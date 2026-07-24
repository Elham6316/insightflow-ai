import calendar
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.agents.base import BaseAgent

_DATE_NAME_RE = re.compile(r"date|time|_dt$|timestamp|created|updated", re.IGNORECASE)
_MIN_ROWS_FOR_TRENDS = 2
_MIN_DATE_PARSE_RATE = 0.8
_TOP_N_CATEGORIES = 5
_INCOMPLETE_PERIOD_DAY_THRESHOLD = 3  # days before month-end; simple heuristic, not exact


class EDAResults(BaseModel):
    distributions: dict[str, dict[str, float | None]] = {}
    distributions_note: str | None = None
    correlations: dict[str, dict[str, float | None]] = {}
    correlations_note: str | None = None
    trends: dict = {}
    trends_note: str | None = None
    categorical_summary: dict[str, dict[str, int]] = {}
    categorical_summary_note: str | None = None


def _load_dataframe(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file format '{ext}'")


def _clean(value) -> float | None:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return float(value)


def _describe_numeric(df: pd.DataFrame) -> tuple[dict, str | None]:
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return {}, "No numeric columns found in this dataset."
    try:
        desc = numeric_df.describe()
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, don't crash the pipeline
        return {}, f"Could not compute distributions: {exc}"

    result = {
        col: {stat: _clean(val) for stat, val in desc[col].items()} for col in desc.columns
    }
    return result, None


def _correlations(df: pd.DataFrame) -> tuple[dict, str | None]:
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return {}, "Need at least 2 numeric columns to compute correlations."
    try:
        corr = numeric_df.corr()
    except Exception as exc:  # noqa: BLE001
        return {}, f"Could not compute correlations: {exc}"

    result = {
        col: {other: _clean(v) for other, v in corr[col].items()} for col in corr.columns
    }
    return result, None


def _find_date_series(df: pd.DataFrame) -> tuple[str | None, pd.Series | None]:
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col, df[col]

    for col in df.columns:
        if _DATE_NAME_RE.search(str(col)):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if len(df) and parsed.notna().mean() >= _MIN_DATE_PARSE_RATE:
                return col, parsed

    return None, None


def _trends(df: pd.DataFrame) -> tuple[dict, str | None]:
    date_col, parsed = _find_date_series(df)
    if date_col is None:
        return {}, "No date/time column detected."
    if len(df) < _MIN_ROWS_FOR_TRENDS:
        return {}, "Not enough rows to compute a time-based trend."

    try:
        periods = parsed.dt.to_period("M")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        grouped = df.assign(_period=periods).groupby("_period", dropna=True)

        data = []
        for period, group in grouped:
            row = {
                "period": str(period),
                "count": int(len(group)),
                "incomplete_period": False,
                "note": None,
            }
            for col in numeric_cols:
                row[f"sum_{col}"] = _clean(group[col].sum())
            data.append(row)
        data.sort(key=lambda r: r["period"])

        max_date = parsed.max()
        if pd.notna(max_date):
            last_period = str(max_date.to_period("M"))
            days_in_month = calendar.monthrange(max_date.year, max_date.month)[1]
            if (days_in_month - max_date.day) > _INCOMPLETE_PERIOD_DAY_THRESHOLD:
                for row in data:
                    if row["period"] == last_period:
                        row["incomplete_period"] = True
                        row["note"] = (
                            f"This period only contains data through "
                            f"{max_date.strftime('%b %d')} and may not be "
                            f"representative of a full month."
                        )
                        break
    except Exception as exc:  # noqa: BLE001
        return {}, f"Could not compute trends: {exc}"

    return {"date_column": date_col, "granularity": "month", "data": data}, None


def _categorical_summary(df: pd.DataFrame, exclude_cols: set) -> tuple[dict, str | None]:
    result = {}
    for col in df.select_dtypes(include=["object", "string"]).columns:
        if col in exclude_cols:
            continue
        counts = df[col].dropna().value_counts().head(_TOP_N_CATEGORIES)
        if counts.empty:
            continue
        result[col] = {str(k): int(v) for k, v in counts.items()}

    if not result:
        return {}, "No categorical/text columns found in this dataset."
    return result, None


class EDAAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "eda"

    async def execute(self, state: dict) -> dict:
        file_path = state["file_path"]
        df = _load_dataframe(file_path)

        distributions, distributions_note = _describe_numeric(df)
        correlations, correlations_note = _correlations(df)
        date_col, _ = _find_date_series(df)
        trends, trends_note = _trends(df)
        categorical_summary, categorical_summary_note = _categorical_summary(
            df, exclude_cols={date_col} if date_col else set()
        )

        results = EDAResults(
            distributions=distributions,
            distributions_note=distributions_note,
            correlations=correlations,
            correlations_note=correlations_note,
            trends=trends,
            trends_note=trends_note,
            categorical_summary=categorical_summary,
            categorical_summary_note=categorical_summary_note,
        )
        state["eda_results"] = results.model_dump()
        return state
