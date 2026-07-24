import asyncio
import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, ValidationError

from app.agents.base import BaseAgent
from app.services.llm_client import MODEL_NAME, client

logger = logging.getLogger(__name__)

_NUMERIC_STRING_RE = re.compile(r"^-?\d+(\.\d+)?$")
NUMERIC_LOOKING_THRESHOLD = 0.8  # % of non-null values that must look numeric to flag


class DataQualityReport(BaseModel):
    missing_by_column: dict[str, float]
    duplicates: int
    type_issues: list[dict]
    outliers: dict[str, int]
    overall_score: float
    summary: str


FALLBACK_SUMMARY_TEXT = "Fallback summary: the LLM was unavailable, so this summary was template-generated from the computed stats."


def _load_dataframe(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file format '{ext}'")


def _missing_by_column(df: pd.DataFrame) -> dict[str, float]:
    if len(df) == 0:
        return {col: 0.0 for col in df.columns}
    return (df.isnull().mean() * 100).round(2).to_dict()


def _duplicate_count(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def _numeric_like_fraction(series: pd.Series) -> float:
    non_null = series.dropna().astype(str).str.strip()
    if non_null.empty:
        return 0.0
    cleaned = non_null.str.replace(",", "", regex=False)
    matches = cleaned.apply(lambda v: bool(_NUMERIC_STRING_RE.match(v)))
    return float(matches.mean())


def _type_issues(df: pd.DataFrame) -> list[dict]:
    issues = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        fraction = _numeric_like_fraction(df[col])
        if fraction >= NUMERIC_LOOKING_THRESHOLD:
            issues.append(
                {
                    "column": col,
                    "issue": "numeric_values_stored_as_text",
                    "detail": f"{fraction * 100:.0f}% of non-null values look numeric "
                    f"but the column dtype is {df[col].dtype}",
                }
            )
    return issues


def _outliers_by_column(df: pd.DataFrame) -> tuple[dict[str, int], int, int]:
    outliers: dict[str, int] = {}
    total_outliers = 0
    total_numeric_cells = 0

    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        total_numeric_cells += len(series)
        if len(series) < 4:
            outliers[col] = 0
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            outliers[col] = 0
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        outliers[col] = count
        total_outliers += count

    return outliers, total_outliers, total_numeric_cells


def _overall_score(
    df: pd.DataFrame,
    missing_by_column: dict[str, float],
    duplicates: int,
    total_outliers: int,
    total_numeric_cells: int,
) -> float:
    # Overall score (0-100, higher = better), a simple weighted penalty formula:
    #   missing_pct   = average % missing across all columns
    #   duplicate_pct = fully duplicate rows / total rows * 100
    #   outlier_pct   = total outlier values / total numeric cells * 100
    #   score = 100 - (0.4 * missing_pct + 0.3 * duplicate_pct + 0.3 * outlier_pct)
    # Missing values are weighted highest (0.4) since they most directly block
    # downstream analysis; duplicates and outliers are weighted equally (0.3
    # each) since both distort results without fully blocking them.
    rows = len(df)
    missing_pct = (
        sum(missing_by_column.values()) / len(missing_by_column)
        if missing_by_column
        else 0.0
    )
    duplicate_pct = (duplicates / rows * 100) if rows else 0.0
    outlier_pct = (
        total_outliers / total_numeric_cells * 100 if total_numeric_cells else 0.0
    )

    score = 100 - (0.4 * missing_pct + 0.3 * duplicate_pct + 0.3 * outlier_pct)
    return round(max(0.0, min(100.0, score)), 2)


def _build_summary_prompt(stats: dict) -> str:
    return f"""You are a data quality reviewer. Given these computed data quality \
stats (not raw data), write a 2-3 sentence human-readable summary for a
non-technical reader. Mention the overall score, the most notable issue (if
any), and whether the data looks usable as-is.

Stats:
{json.dumps(stats, indent=2)}

Return ONLY the summary text, no markdown, no preamble."""


def _template_summary(stats: dict) -> str:
    score = stats["overall_score"]
    n_type_issues = len(stats["type_issues"])
    n_outlier_cols = sum(1 for v in stats["outliers"].values() if v > 0)
    return (
        f"Data quality score: {score}/100. Found {stats['duplicates']} duplicate "
        f"row(s), {n_type_issues} column(s) with possible type issues, and "
        f"{n_outlier_cols} numeric column(s) containing outliers."
    )


class DataQualityAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "data_quality"

    async def execute(self, state: dict) -> dict:
        file_path = state["file_path"]
        df = _load_dataframe(file_path)

        missing_by_column = _missing_by_column(df)
        duplicates = _duplicate_count(df)
        type_issues = _type_issues(df)
        outliers, total_outliers, total_numeric_cells = _outliers_by_column(df)
        overall_score = _overall_score(
            df, missing_by_column, duplicates, total_outliers, total_numeric_cells
        )

        stats = {
            "missing_by_column": missing_by_column,
            "duplicates": duplicates,
            "type_issues": type_issues,
            "outliers": outliers,
            "overall_score": overall_score,
        }

        summary = await self._get_summary(stats)

        report = DataQualityReport(**stats, summary=summary)
        state["quality_report"] = report.model_dump()
        return state

    async def _get_summary(self, stats: dict) -> str:
        prompt = _build_summary_prompt(stats)
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                raw = await asyncio.to_thread(self._call_llm, prompt)
                summary = raw.strip()
                if summary:
                    return summary
                raise ValueError("empty response from LLM")
            except Exception as exc:  # noqa: BLE001 - any LLM/parse failure triggers retry
                logger.warning(
                    "data_quality: LLM summary failed on attempt %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )

        logger.warning(
            "data_quality: falling back to template summary after %d attempts", attempts
        )
        return _template_summary(stats)

    def _call_llm(self, prompt: str) -> str:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text
