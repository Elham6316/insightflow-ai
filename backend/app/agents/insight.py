import asyncio
import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.agents.base import BaseAgent
from app.services.llm_client import MODEL_NAME, client

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
MIN_INSIGHTS = 3
MAX_INSIGHTS = 6


class Insight(BaseModel):
    title: str
    description: str
    severity: Literal["info", "warning", "critical"]
    related_metric: str


class InsightList(BaseModel):
    insights: list[Insight] = Field(min_length=MIN_INSIGHTS, max_length=MAX_INSIGHTS)


_PROMPT_TEMPLATE = """You are a senior data analyst writing insights for a business \
stakeholder. You are given a data quality report and an exploratory data \
analysis (EDA) summary for a "{data_domain}" dataset. Write {min_n}-{max_n} \
business insights.

CRITICAL STYLE REQUIREMENT: every insight must be CAUSAL and EXPLANATORY, not \
a restated number. Explain what a pattern likely MEANS or WHY it might be \
happening, and what it's worth investigating or doing next. Do not just \
report a statistic.

BAD (reject this style — just restates a number with no reasoning):
"Revenue was $50,000 in the top region."

GOOD (target this style — explains a pattern and suggests a reason/action):
"Riyadh generated 45% of total revenue despite having only 30% of \
transactions, suggesting higher average order value there — likely worth \
investigating what's driving larger purchases in that region."

Every insight's description MUST reference actual numbers from the data \
below — never invent numbers that aren't present in the data given to you.

IMPORTANT — INCOMPLETE TIME PERIODS: in the EDA summary's "trends" data, any \
period with "incomplete_period": true does NOT contain a full period's worth \
of data — see its "note" field for exactly how much of the period it covers. \
Do NOT frame a comparison involving an incomplete period as a definitive \
trend (e.g. do not say a metric "declined" or "grew" relative to it as if \
comparing like-for-like). Either avoid comparing to that period entirely, or \
if you do mention it, explicitly caveat that the period is partial/incomplete \
and that the comparison isn't apples-to-apples.

Data quality report:
{quality_report}

EDA summary:
{eda_results}

Return ONLY valid JSON, with no markdown fences and no commentary, matching \
exactly this shape:
{{
  "insights": [
    {{
      "title": "short, specific title",
      "description": "2-3 sentences of causal reasoning grounded in the real numbers above",
      "severity": "info | warning | critical",
      "related_metric": "which EDA/quality field this references, e.g. 'distributions.unit_price' or 'overall_score'"
    }}
  ]
}}
Use "warning" or "critical" severity for data quality problems that affect \
reliability, or concerning business trends. Use "info" for neutral \
observations."""


def _build_prompt(data_domain: str, eda_results: dict, quality_report: dict) -> str:
    return _PROMPT_TEMPLATE.format(
        data_domain=data_domain or "generic",
        min_n=MIN_INSIGHTS,
        max_n=MAX_INSIGHTS,
        quality_report=json.dumps(quality_report, indent=2),
        eda_results=json.dumps(eda_results, indent=2),
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = _JSON_BLOCK_RE.search(text)
    if match:
        text = match.group(0)
    return json.loads(text)


def _fallback_insights(eda_results: dict, quality_report: dict) -> InsightList:
    insights = []

    score = quality_report.get("overall_score")
    duplicates = quality_report.get("duplicates", 0)
    missing_by_column = quality_report.get("missing_by_column", {})
    n_missing_cols = sum(1 for pct in missing_by_column.values() if pct > 0)

    insights.append(
        Insight(
            title="Data quality overview",
            description=(
                f"This dataset has an overall data quality score of {score}/100, "
                f"with {n_missing_cols} column(s) containing missing values and "
                f"{duplicates} duplicate row(s)."
            ),
            severity="warning" if (score is not None and score < 80) else "info",
            related_metric="overall_score",
        )
    )

    distributions = eda_results.get("distributions") or {}
    if distributions:
        col, stats = next(iter(distributions.items()))
        insights.append(
            Insight(
                title=f"{col} range",
                description=(
                    f"{col} ranges from {stats.get('min')} to {stats.get('max')}, "
                    f"with a mean of {stats.get('mean')}."
                ),
                severity="info",
                related_metric=f"distributions.{col}",
            )
        )
    else:
        insights.append(
            Insight(
                title="No numeric columns",
                description=(
                    "This dataset has no numeric columns, so distribution and "
                    "correlation analysis could not be computed."
                ),
                severity="info",
                related_metric="distributions",
            )
        )

    categorical_summary = eda_results.get("categorical_summary") or {}
    trends = eda_results.get("trends") or {}
    if categorical_summary:
        col, counts = next(iter(categorical_summary.items()))
        top_value, top_count = next(iter(counts.items()))
        insights.append(
            Insight(
                title=f"Most common {col}",
                description=(
                    f"'{top_value}' is the most frequent value in '{col}', "
                    f"appearing {top_count} time(s)."
                ),
                severity="info",
                related_metric=f"categorical_summary.{col}",
            )
        )
    elif trends.get("data"):
        first, last = trends["data"][0], trends["data"][-1]
        insights.append(
            Insight(
                title="Time trend",
                description=(
                    f"Row count went from {first['count']} in {first['period']} "
                    f"to {last['count']} in {last['period']}."
                ),
                severity="info",
                related_metric="trends",
            )
        )
    else:
        insights.append(
            Insight(
                title="Limited breakdowns available",
                description=(
                    "No categorical columns or time trends were available for "
                    "further breakdown in this dataset."
                ),
                severity="info",
                related_metric="eda_results",
            )
        )

    return InsightList(insights=insights)


class InsightAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "insight"

    async def execute(self, state: dict) -> dict:
        eda_results = state.get("eda_results", {})
        quality_report = state.get("quality_report", {})
        data_domain = state.get("data_domain", "generic")

        prompt = _build_prompt(data_domain, eda_results, quality_report)
        result = await self._get_insights(prompt, eda_results, quality_report)

        state["insights"] = [i.model_dump() for i in result.insights]
        return state

    async def _get_insights(
        self, prompt: str, eda_results: dict, quality_report: dict
    ) -> InsightList:
        attempts = 2
        for attempt in range(1, attempts + 1):
            raw = await asyncio.to_thread(self._call_llm, prompt)
            try:
                data = _extract_json(raw)
                return InsightList.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "insight: malformed/insufficient LLM output on attempt %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )

        logger.warning(
            "insight: falling back to template insights after %d attempts", attempts
        )
        return _fallback_insights(eda_results, quality_report)

    def _call_llm(self, prompt: str) -> str:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text
