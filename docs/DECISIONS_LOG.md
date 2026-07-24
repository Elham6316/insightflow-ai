# Decisions Log

## Tech Stack Changes

- **LLM provider: Claude/Anthropic → Google Gemini.** The project originally
  planned to use Anthropic's Claude API for the LLM layer (`app/config.py`
  originally read `ANTHROPIC_API_KEY`, and `requirements.txt` originally
  included `anthropic`). This was switched to Google's Gemini API because
  Gemini offers a usable free tier suitable for a personal/learning project,
  while the Claude API requires paid usage beyond a small initial credit.
  `app/config.py` now reads `GEMINI_API_KEY` (see `.env.example`),
  `requirements.txt` lists `google-genai` instead of `anthropic`, and the
  client lives in `app/services/llm_client.py`. The model currently
  configured there is `models/gemini-3.1-flash-lite` (see "gemini-1.5-flash
  retired" below for why).
- **Impact on future work:** anywhere the original plan refers to "Claude" or
  "the Anthropic API" — in agent prompts, docs, or design notes written
  before this switch — it now means Gemini via `app/services/llm_client.py`.
  `app/agents/planner.py` is the first agent built against this client and
  should be used as the reference pattern for future agents.

## Environment Setup Issues & Fixes

- **Windows TLS/SSL certificate failure calling the Gemini API.** Both the
  gRPC-based `google-generativeai` SDK and, after switching SDKs, the
  HTTP-based `google-genai` SDK failed identically with
  `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` when
  calling `generativelanguage.googleapis.com`. `curl` to the same host from
  the same machine succeeded, which ruled out network blocking and pointed
  to a Python-specific trust store gap: the local Windows certificate store
  has a root CA that Python's bundled `certifi`/gRPC trust roots don't
  recognize. Fixed by adding the `truststore` package (see
  `requirements.txt`) and calling `truststore.inject_into_ssl()` at the top
  of `app/services/llm_client.py`, which patches Python's `ssl` module to
  validate against the OS-native certificate store instead of the bundled
  one.
- **`gemini-1.5-flash` retired.** The original plan specified
  `gemini-1.5-flash` (chosen for its free tier) as the model, but by the
  time the client was tested against the live API it returned `404
  NOT_FOUND` — the model had been retired and was no longer in the
  account's available model list (confirmed via `client.models.list()`).
  Switched to the model currently configured in
  `app/services/llm_client.py`: `models/gemini-3.1-flash-lite`.
- **Supabase password authentication failure on first migration.** The
  first `alembic upgrade head` attempt against the Supabase database
  (`db.adtyaupjooveifqwwbfy.supabase.co`) failed with `FATAL: password
  authentication failed for user "postgres"` — the password in
  `backend/.env`'s `DATABASE_URL` was stale/incorrect. Resolved by
  re-copying the correct connection string from the Supabase dashboard
  (Project Settings → Database → Connection string) into `backend/.env`;
  the retry succeeded and created all four tables plus Alembic's own
  `alembic_version` table.

## Database

Schema as defined in `backend/app/db/models.py` and created by
`backend/alembic/versions/a4970af3b658_create_initial_tables.py`:

- **`datasets`**: `id` (UUID, PK, default `gen_random_uuid()`), `filename`
  (Text, not null), `file_path` (Text, not null), `domain` (Text, nullable),
  `row_count` (Integer, nullable), `col_count` (Integer, nullable), `status`
  (Text, default `"uploaded"`), `uploaded_at` (Timestamp, default `now()`).
- **`analysis_runs`**: `id` (UUID, PK), `dataset_id` (UUID, FK →
  `datasets.id`, `ON DELETE CASCADE`), `status` (Text, default `"pending"`),
  `current_agent` (Text, nullable), `started_at` (Timestamp, default
  `now()`), `finished_at` (Timestamp, nullable).
- **`agent_outputs`**: `id` (UUID, PK), `run_id` (UUID, FK →
  `analysis_runs.id`, `ON DELETE CASCADE`), `agent_name` (Text, not null),
  `output` (JSONB, nullable), `status` (Text, nullable), `duration_ms`
  (Integer, nullable), `created_at` (Timestamp, default `now()`).
- **`insights`**: `id` (UUID, PK), `run_id` (UUID, FK → `analysis_runs.id`,
  `ON DELETE CASCADE`), `title` (Text, nullable), `description` (Text,
  nullable), `severity` (Text, nullable), `chart_ref` (Text, nullable),
  `created_at` (Timestamp, default `now()`).

The migration also runs `CREATE EXTENSION IF NOT EXISTS pgcrypto` so
`gen_random_uuid()` is available for the UUID primary key defaults.

- **RLS is currently disabled on all four tables** (flagged by Supabase's
  dashboard). This is acceptable for now because the backend connects
  directly via `DATABASE_URL` using the `postgres` role
  (`app/db/session.py`), not through Supabase's public API / anon key —
  there is no client-side path that bypasses the backend today. RLS
  policies must be added before any production deployment, and before the
  frontend (`frontend/`) ever talks to Supabase directly instead of going
  through the FastAPI backend.
- **`datasets.domain` is currently always NULL after upload.** The
  `POST /upload` endpoint (`app/api/routes_upload.py`) only sets
  `filename`, `file_path`, `row_count`, `col_count`, and `status` on
  insert. `PlannerAgent` (`app/agents/planner.py`) does classify the domain
  (`state["data_domain"]`), but that result currently lives only in the
  in-memory `state` dict passed between agents — nothing writes it back to
  the `datasets` row. This will be wired up once the orchestrator/graph is
  built in Phase 2.

## Completed Phases

**Phase 0** — project scaffolding:
- Monorepo structure (`frontend/`, `backend/`, `automation/n8n_workflows/`,
  `docs/`) with root `.env.example` and `.gitignore`, git initialized.
- Next.js 14 frontend (App Router, TypeScript, Tailwind, shadcn/ui) with a
  shared header layout and a placeholder homepage.
- FastAPI backend (`app/main.py`) with the package layout
  (`app/api/`, `app/db/`, `app/agents/`, `app/orchestrator/`,
  `app/services/`, `app/utils/`), a working `GET /health` endpoint, and
  `app/config.py` reading settings from `.env` via pydantic-settings.
- Supabase Postgres database with `datasets`, `analysis_runs`,
  `agent_outputs`, `insights` created via the first Alembic migration.
- Gemini client (`app/services/llm_client.py`) working end-to-end against
  the live API.

**Phase 1** — first agent pipeline pieces:
- `BaseAgent` (`app/agents/base.py`): abstract base using `abc.ABC` /
  `abstractmethod`, with a concrete `run(state)` that wraps the
  subclass-defined `execute(state)` in start/end logging and a try/except
  that appends failures to `state["errors"]` instead of crashing the
  pipeline.
- `data_loader.load_and_profile()` (`app/services/data_loader.py`): reads
  CSV (`.csv`) or Excel (`.xlsx`/`.xls`) via pandas, returns shape,
  column/dtype info, a JSON-serializable 5-row sample, and per-column null
  counts; raises `ValueError` for unsupported extensions.
- `POST /upload` (`app/api/routes_upload.py`): validates extension
  (`.csv`/`.xlsx`), saves the file under `uploads/` with a UUID filename,
  profiles it via `load_and_profile`, inserts a `datasets` row, returns
  `dataset_id` and the profile.
- `PlannerAgent` (`app/agents/planner.py`): calls Gemini with the dataset
  profile, parses/validates the response with a Pydantic model
  (`PlannerOutput`), retries once on malformed JSON, and falls back to a
  safe default (`domain="generic"`,
  `agents_to_run=["data_quality","eda","insight"]`) if the retry also
  fails; handles LLM responses wrapped in markdown code fences.
- All of the above verified with real API calls (live Gemini classification
  of a sample dataset, live upload against the Supabase `datasets` table)
  and mocked edge cases (malformed JSON fallback, fenced JSON extraction,
  unsupported file extensions).

## Known Gaps / TODO for Phase 2

- Planner output (`data_domain`, `has_time_series`, `reasoning`,
  `agents_to_run`) is not yet persisted back to the `datasets` table.
- RLS is not yet configured on any table.
- No orchestrator/graph exists yet to wire agents together into a full run
  (`app/orchestrator/` is currently an empty package).
