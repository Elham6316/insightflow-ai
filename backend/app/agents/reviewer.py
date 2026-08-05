import re
from typing import Literal

from pydantic import BaseModel

from app.agents.base import BaseAgent

# Only impossible_kpi_values ever uses "critical" — it's the only check
# pointing at a single, cleanly re-runnable agent (kpi), so it's the only
# one allowed to trigger a rerun. Every other check flags a real problem
# but re-running kpi wouldn't fix it, so they stay "warning"/"info".
_MIN_INSIGHTS = 3
_MAX_REVIEW_RERUNS = 1
_NON_NEGATIVE_KPI_FORMATS = {"currency", "number"}
_NUMBER_RE = re.compile(r"-?\d+\.\d+|-?\d+")


class ReviewNote(BaseModel):
    check_name: str
    severity: Literal["critical", "warning", "info"]
    message: str
    affected_agent: str


def _check_impossible_kpis(kpis: list[dict]) -> list[ReviewNote]:
    notes = []
    for kpi in kpis:
        value = kpi.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        label, fmt, unit = kpi.get("label", "KPI"), kpi.get("format"), kpi.get("unit", "")

        if fmt in _NON_NEGATIVE_KPI_FORMATS and value < 0:
            notes.append(
                ReviewNote(
                    check_name="impossible_kpi_values",
                    severity="critical",
                    message=f"'{label}' is {value}{unit}, but this KPI should never be negative.",
                    affected_agent="kpi",
                )
            )
        elif fmt == "percent" and not (0 <= value <= 100):
            notes.append(
                ReviewNote(
                    check_name="impossible_kpi_values",
                    severity="critical",
                    message=f"'{label}' is {value}%, outside the valid 0-100% range.",
                    affected_agent="kpi",
                )
            )
    return notes


def _collect_reference_numbers(eda_results: dict, kpis: list[dict], quality_report: dict) -> set[float]:
    """Flattens every numeric leaf across the three sources into one set, so
    an insight's cited number can be spot-checked against "does this appear
    anywhere in the underlying data" without caring which field it came
    from."""
    numbers: set[float] = set()

    def _walk(value) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            numbers.add(round(float(value), 2))
        elif isinstance(value, dict):
            for v in value.values():
                _walk(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                _walk(v)

    _walk(eda_results)
    _walk(quality_report)
    for kpi in kpis:
        _walk(kpi.get("value"))
    return numbers


def _plausibly_present(n: float, reference: set[float]) -> bool:
    # 1% relative tolerance (floor 0.05) absorbs rounding differences
    # between how a number is stored (e.g. correlations rounded to 2dp in
    # the chart) and how the LLM phrased it in prose.
    return any(abs(n - r) <= max(0.05, abs(r) * 0.01) for r in reference)


def _check_insight_mismatches(insights: list[dict], reference_numbers: set[float]) -> list[ReviewNote]:
    notes = []
    for insight in insights:
        description = insight.get("description", "")
        cited = [round(float(m), 2) for m in _NUMBER_RE.findall(description)]
        if not cited:
            continue
        if not any(_plausibly_present(n, reference_numbers) for n in cited):
            notes.append(
                ReviewNote(
                    check_name="insight_data_mismatch",
                    severity="warning",
                    message=(
                        f"Insight '{insight.get('title', '')}' cites number(s) {cited} "
                        "that couldn't be found anywhere in the underlying data — "
                        "may be unverified."
                    ),
                    affected_agent="insight",
                )
            )
    return notes


def _check_insight_count(insights: list[dict]) -> list[ReviewNote]:
    if len(insights) >= _MIN_INSIGHTS:
        return []
    return [
        ReviewNote(
            check_name="insufficient_insight_count",
            severity="warning",
            message=f"Only {len(insights)} insight(s) were generated; expected at least {_MIN_INSIGHTS}.",
            affected_agent="insight",
        )
    ]


def _check_quality_score_sanity(quality_report: dict) -> list[ReviewNote]:
    score = quality_report.get("overall_score")
    duplicates = quality_report.get("duplicates") or 0
    has_missing = any((quality_report.get("missing_by_column") or {}).values())

    if score is None or score < 100 or not (duplicates > 0 or has_missing):
        return []
    return [
        ReviewNote(
            check_name="quality_score_sanity",
            severity="warning",
            message=(
                f"overall_score is {score} despite {duplicates} duplicate(s) and "
                f"{'missing values' if has_missing else 'no missing values'} present "
                "in quality_report — possible scoring formula bug."
            ),
            affected_agent="data_quality",
        )
    ]


class ReviewerAgent(BaseAgent):
    """Deterministic quality-control pass over the pipeline's own output.

    Pure Python checks, no LLM: an LLM re-checking another LLM's work could
    itself be wrong, while these checks are cheap, fast, and either true or
    false with no ambiguity.
    """

    @property
    def name(self) -> str:
        return "reviewer"

    async def execute(self, state: dict) -> dict:
        kpis = state.get("kpis") or []
        insights = state.get("insights") or []
        quality_report = state.get("quality_report") or {}
        eda_results = state.get("eda_results") or {}

        reference_numbers = _collect_reference_numbers(eda_results, kpis, quality_report)

        notes = [
            *_check_impossible_kpis(kpis),
            *_check_insight_mismatches(insights, reference_numbers),
            *_check_insight_count(insights),
            *_check_quality_score_sanity(quality_report),
        ]

        review_rerun_count = state.get("review_rerun_count", 0)
        critical_found = any(n.severity == "critical" for n in notes)

        needs_rerun = False
        if critical_found:
            if review_rerun_count < _MAX_REVIEW_RERUNS:
                needs_rerun = True
                state["rerun_agent"] = "kpi"
                state["review_rerun_count"] = review_rerun_count + 1
            else:
                notes.append(
                    ReviewNote(
                        check_name="rerun_cap_reached",
                        severity="info",
                        message=(
                            f"Critical issue(s) found but the rerun cap "
                            f"({_MAX_REVIEW_RERUNS}) was already used for this run — "
                            "not re-running again."
                        ),
                        affected_agent="reviewer",
                    )
                )

        state["needs_rerun"] = needs_rerun
        state["review_notes"] = [n.model_dump() for n in notes]
        return state
