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

## Phase 2: Core Analysis Pipeline

### Agents Built

- **`DataQualityAgent`** (`app/agents/data_quality.py`): pure pandas/numpy
  computation, no LLM involved in the calculations themselves. Computes
  `missing_by_column` (`% missing per column, df.isnull().mean() * 100`),
  `duplicates` (`df.duplicated().sum()`), `type_issues` (object/string
  columns where ≥80% of non-null values match a numeric-looking regex —
  `NUMERIC_LOOKING_THRESHOLD = 0.8`), and `outliers` (per numeric column,
  values outside `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`). `overall_score` is a
  weighted penalty formula (see `_overall_score()`):
  `100 - (0.4 * missing_pct + 0.3 * duplicate_pct + 0.3 * outlier_pct)`,
  clipped to `[0, 100]` — missing values weighted highest (0.4) since they
  most directly block analysis, duplicates and outliers weighted equally
  (0.3 each). The LLM (`_get_summary()`) is used *only* to turn the already
  computed `stats` dict into a 2-3 sentence human-readable summary — it
  never receives raw data and never influences the numbers.
- **`EDAAgent`** (`app/agents/eda.py`): pure pandas, no LLM, no duckdb (not
  needed — pandas covered every requested computation). Computes
  `distributions` (`describe()` per numeric column), `correlations`
  (`.corr()` on numeric columns as a nested dict), `trends` (monthly
  sum/count aggregation when a date/time column is found — see "Known
  Limitation" below), and `categorical_summary` (top 5 value counts per
  object/string column). Every section degrades to `{}` plus a
  `<section>_note` explaining why (e.g. "No numeric columns found in this
  dataset.") instead of raising, when the relevant data is missing or
  insufficient.
- **`InsightAgent`** (`app/agents/insight.py`): the prompt (`_PROMPT_TEMPLATE`)
  embeds two few-shot examples — a BAD example ("Revenue was $50,000 in the
  top region.") and a GOOD example ("Riyadh generated 45% of total revenue
  despite having only 30% of transactions...") — to steer the LLM toward
  causal, explanatory insights instead of restated numbers. Output is
  validated with `InsightList`, whose `insights` field uses
  `Field(min_length=3, max_length=6)` — this Pydantic constraint itself is
  what rejects a too-short response as a `ValidationError`, feeding the same
  retry-once-then-fallback loop used by `PlannerAgent`. The fallback
  (`_fallback_insights()`) builds exactly 3 insights directly from
  `eda_results`/`quality_report` (a quality-score overview, a numeric-range
  highlight, and a categorical/trend highlight), never inventing numbers.

### Design Pattern: Retry + Fallback for LLM Calls

All three LLM-calling agents — `PlannerAgent`, `DataQualityAgent`'s summary
step, and `InsightAgent` — follow the same pattern: call the LLM, validate
the response with a Pydantic model, retry once on failure (malformed JSON,
schema validation failure, or empty response), then fall back to a safe
template-based default rather than crashing the pipeline. This was a
deliberate consistency decision so every agent behaves predictably under LLM
failure, rather than each agent inventing its own error-handling approach.

### Known Limitation Found & Fixed: Misleading Trend Comparisons

**Issue:** `InsightAgent`, run against `sample_sales_fixed.csv` (data through
Feb 10 only), initially generated an insight along the lines of "Significant
Decline in Monthly Transaction Volume," directly comparing January's 11
orders to February's 4 — treating a complete month against a partial one as
if the drop were a real trend. The LLM had no way to know February only had
10 days of data, because that information wasn't in what it was given.

**Fix:** `EDAAgent._trends()` (`app/agents/eda.py`) now finds the dataset's
max date, computes days-in-month via `calendar.monthrange()`, and flags the
period containing that max date as `"incomplete_period": true` (with a
human-readable `"note"`) whenever the max date falls more than
`_INCOMPLETE_PERIOD_DAY_THRESHOLD = 3` days short of month-end — a simple,
intentionally inexact heuristic. `InsightAgent`'s prompt was updated with an
explicit "INCOMPLETE TIME PERIODS" instruction telling the LLM not to treat
a comparison involving a flagged period as a definitive trend, and to either
avoid it or explicitly caveat it as partial. Re-running against the same
fixture, the misleading insight was replaced by one titled "Incomplete Data
for February 2025" / "Incomplete reporting for February," which explicitly
states the Jan-vs-Feb comparison "would be mathematically unsound without
normalizing for the shortened timeframe."

**Broader lesson:** LLM-generated causal insights can be numerically
accurate but contextually misleading when the underlying data has gaps the
LLM isn't explicitly told about. This was only checked and fixed for the
time-series/`trends` case so far — the same class of problem (grounded but
misleading due to an un-flagged data gap) should be checked for other agents
and domains as they're added later, not assumed solved everywhere.

### Orchestration

`app/orchestrator/graph.py` builds a LangGraph `StateGraph` over
`AnalysisState` (`app/orchestrator/state.py`) with a linear pipeline:
`planner -> data_quality -> eda -> insight -> END`. There are no conditional
edges yet — every run executes all four agents in the same fixed order; a
Reviewer node with conditional routing is planned for a later phase, not
this one.

Error-continuation behavior: `BaseAgent.run()` (`app/agents/base.py`)
already catches agent exceptions internally and writes them to
`state["errors"]` rather than raising, so the graph naturally continues to
the next node even if one agent fails. `_make_node()` additionally
diffs `state["errors"]` before/after each node and logs a warning when a
node adds new errors, plus wraps `agent.run()` in a last-resort
`try/except` as defense against failures outside the agent's own guard.
`run_analysis()` sets the final `state["status"]` to `"done_with_errors"`
instead of `"done"` when `state["errors"]` is non-empty. This was explicitly
tested by mocking `DataQualityAgent.execute` to raise: the graph logged a
warning, continued to `eda`, and the final status was correctly
`"done_with_errors"`.

### API Endpoints Added

Both in `app/api/routes_analysis.py`, wired into `app/main.py`:

- **`POST /analysis/{dataset_id}/run`**: looks up the `datasets` row (404 if
  missing), profiles the file via `load_and_profile`, inserts an
  `analysis_runs` row (`status="running"`), runs the full graph, then writes
  one `agent_outputs` row per agent (`planner` → `planner_output`,
  `data_quality` → `quality_report`, `eda` → `eda_results`, `insight` →
  `{"insights": [...]}`), with each row's `status` set to `"failed"` if that
  agent name appears in `state["errors"]`, else `"success"`. Each generated
  insight is written to the `insights` table, with `related_metric` stored
  in the `chart_ref` column (repurposing it for its stated future use —
  "for later chart linking" — since no dedicated chart-reference data exists
  yet). Updates the `analysis_runs` row's `status`, `current_agent`, and
  `finished_at`, and returns `{"run_id": ..., "final_state": ...}`, plus a
  `"note"` field when `status == "done_with_errors"`.
- **`GET /analysis/{run_id}`**: 404 if the run doesn't exist, otherwise
  returns the `analysis_runs` row plus its related `agent_outputs` and
  `insights` rows (queried directly, not via lazy relationship access), with
  the same `"note"` field when applicable. Note: `agent_outputs.duration_ms`
  is currently always `null` — `BaseAgent.run()` times each agent
  internally but doesn't thread that duration back into `state`, so nothing
  populates this column yet.

### Testing Approach

- **`tests/test_eda_agent.py`** and **`tests/test_orchestrator_graph.py`**:
  pytest tests (using `pytest-asyncio`) against `sample_sales_fixed.csv`,
  covering `EDAAgent` in isolation and the full
  `planner -> data_quality -> eda -> insight` graph end-to-end.
- **`tests/manual_test_insight.py`**: a manual (non-pytest, no assertions)
  script that runs `DataQualityAgent -> EDAAgent -> InsightAgent` against
  `sample_sales_fixed.csv` and pretty-prints the generated insights, for
  fast by-eye iteration on prompt/insight quality. Note: there is currently
  no equivalent `manual_test_data_quality.py` — only `manual_test_insight.py`
  exists; `DataQualityAgent` was iterated on with ad-hoc inline scripts
  during development rather than a saved manual test script.
- The full pipeline was also verified live against the real Supabase
  database via `POST /analysis/{dataset_id}/run` and
  `GET /analysis/{run_id}` (through a locally running `uvicorn` instance),
  confirming real rows landed correctly in `analysis_runs`, `agent_outputs`,
  and `insights`. That test data was cleaned up afterward by deleting the
  `datasets` row, which cascades (`ON DELETE CASCADE`) through
  `analysis_runs` to `agent_outputs` and `insights`.

## Known Issues

### RESOLVED: Blue pill/capsule artifact on the correlation heatmap

**Symptom:** a solid blue pill/capsule-shaped region rendered near the top
of the correlation heatmap chart in the dashboard (`app/agents/
visualization.py`'s `_heatmap_from_correlations()`, rendered client-side via
`frontend/components/echart.tsx`), overlapping the chart title. It persisted
across page refreshes, hard refreshes, and backend restarts, and survived
two earlier fix attempts, so it took three separate rounds of DOM/canvas
inspection to isolate correctly.

**Root cause:** the shape was the ECharts `visualMap` component — the
color-scale legend bar for the heatmap — rendering as a solid filled shape
rather than the thin gradient strip it was meant to be. It was confirmed via
live DOM inspection (`document.elementsFromPoint()` at the shape's screen
location returned only the chart's own `<canvas>` layers, no separate HTML/
CSS element) and canvas pixel analysis (a concentrated, single-dominant-
color blob, present immediately on page load before any mouse interaction
had ever occurred, non-blinking, and unaffected by hovering over the chart
or moving the mouse away).

**Initial attempts that were wrong, and why they seemed plausible:**
1. `visualMap.calculable = False` (commit `f1ca559`) — `calculable=True`
   makes ECharts draw draggable range-filter "handle" thumbs (pill-shaped)
   on the legend bar; this was a real, verified bug (confirmed via before/
   after pixel comparison) and a legitimate fix, but it wasn't the shape
   still being reported afterward.
2. `axisPointer: {"show": False}` at the option, `xAxis`, and `yAxis`
   levels (bundled into commit `41faf96`) — ruled out on architectural
   grounds: `axisPointer` is a hover-triggered overlay ECharts only ever
   draws in response to a `mousemove` event, but the shape was present
   before any mouse event had ever fired on the page, which is impossible
   for an `axisPointer`.

**Actual fix (commit `41faf96`):** `visualMap.show` set to `False`. `min`/
`max` (the color-mapping range) are kept, so cell background colors and
tooltips are unaffected — only the visible legend bar itself is hidden.
Verified via a fresh end-to-end run: heatmap cells still render correct
colors/values (confirmed via per-canvas-layer pixel counts), the legend's
render layer is empty (`0` colored pixels) before/during/after simulated
hover, and the rest of the dashboard (KPIs, insights, other charts) is
unaffected.

**Lesson:** this took three rounds because three different ECharts
components — the `visualMap` legend's interactive drag-handles, the
`axisPointer` hover crosshair/shadow, and the `visualMap` legend bar itself
— can all render as visually similar small blue shapes near a chart's edge,
despite being entirely separate components with separate config keys and
separate root causes. What actually worked was not reasoning from
appearance, but isolating the exact component by disabling one candidate at
a time and re-verifying with fresh DOM/pixel inspection after each change —
in particular, checking whether the shape existed *before any interaction*
was the single fact that ruled out `axisPointer` conclusively.

## Visual Identity Vision

**Insight Stream as the product's signature motion system.** The motion
language defined in `frontend/lib/motion.ts` (the `Organize` / `Merge` /
`Flow` / `Connect` / `Reveal` primitives, and the node-and-edge "Insight
Stream" visual it powers) is intended to become InsightFlow's consistent
visual identity, not a one-off homepage decoration. The target is to reuse
the same motion primitives and visual vocabulary (thin full-saturation
lines, small solid nodes, orderly connection) across: the homepage hero, the
upload experience, loading states, empty states, success states, dashboard
transitions, and AI-processing indicators (e.g. while an agent is running).

This is the target for the follow-up phase once the homepage foundation
(design tokens + the Insight Stream hero component) is built and confirmed
— it is not yet implemented beyond the homepage scope.

## Known Gaps / TODO for Phase 3

- `datasets.domain` is still always `NULL` after upload — neither
  `POST /upload` nor `POST /analysis/{dataset_id}/run` writes
  `state["data_domain"]` back to the `datasets` row; it only ever lives in
  `state`/`agent_outputs`/the API response.
- RLS is not yet configured on any table.
- The orchestrator graph is linear with no conditional edges — a Reviewer
  node (and any branching logic) is not built yet.
- `agent_outputs.duration_ms` is never populated (see API Endpoints Added
  above).
- The "incomplete period" fix only covers the EDA `trends` section; whether
  other agents can produce numerically-accurate-but-misleading output due to
  un-flagged data gaps hasn't been audited.
