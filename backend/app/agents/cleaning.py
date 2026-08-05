from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.agents.base import BaseAgent

# Missing % above this is "too much to safely guess" — leave the column as
# is rather than impute a large fraction of it.
_MAX_IMPUTABLE_MISSING_PCT = 40.0


class CleaningAction(BaseModel):
    column: str | None
    action: str
    detail: str
    affected: int


def _load_dataframe(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file format '{ext}'")


def _save_dataframe(df: pd.DataFrame, file_path: str) -> str:
    path = Path(file_path)
    cleaned_path = path.with_name(f"{path.stem}_cleaned{path.suffix}")
    ext = path.suffix.lower()
    if ext == ".csv":
        df.to_csv(cleaned_path, index=False)
    else:
        df.to_excel(cleaned_path, index=False)
    return str(cleaned_path)


def _drop_duplicates(df: pd.DataFrame, quality_report: dict) -> tuple[pd.DataFrame, list[CleaningAction]]:
    duplicates = quality_report.get("duplicates", 0)
    if not duplicates:
        return df, []
    before = len(df)
    df = df.drop_duplicates(keep="first")
    return df, [
        CleaningAction(
            column=None,
            action="drop_duplicates",
            detail="Removed fully duplicate rows, keeping the first occurrence.",
            affected=before - len(df),
        )
    ]


def _impute_missing(df: pd.DataFrame, quality_report: dict) -> list[CleaningAction]:
    actions: list[CleaningAction] = []
    for col, pct in (quality_report.get("missing_by_column") or {}).items():
        if col not in df.columns or not pct:
            continue

        missing_count = int(df[col].isna().sum())
        if missing_count == 0:
            continue

        if pct >= _MAX_IMPUTABLE_MISSING_PCT:
            actions.append(
                CleaningAction(
                    column=col,
                    action="skip_missing_too_high",
                    detail=f"{pct:.1f}% missing exceeds the {_MAX_IMPUTABLE_MISSING_PCT:.0f}% "
                    "threshold for safe imputation — left as-is.",
                    affected=missing_count,
                )
            )
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            fill_value = df[col].median()
            method = "median"
        else:
            mode = df[col].mode(dropna=True)
            if mode.empty:
                continue
            fill_value = mode.iloc[0]
            method = "mode"

        df[col] = df[col].fillna(fill_value)
        if hasattr(fill_value, "item"):
            fill_value = fill_value.item()
        actions.append(
            CleaningAction(
                column=col,
                action=f"impute_missing_{method}",
                detail=f"Filled {missing_count} missing value(s) with the column {method} "
                f"({fill_value!r}).",
                affected=missing_count,
            )
        )
    return actions


def _convert_type_issues(df: pd.DataFrame, quality_report: dict) -> list[CleaningAction]:
    actions: list[CleaningAction] = []
    for issue in quality_report.get("type_issues") or []:
        col = issue.get("column")
        if col not in df.columns:
            continue

        original_non_null = int(df[col].notna().sum())
        cleaned = df[col].astype(str).str.strip().str.replace(",", "", regex=False)
        converted = pd.to_numeric(cleaned, errors="coerce")
        converted_non_null = int(converted.notna().sum())

        # Only apply if this doesn't destroy data that was previously
        # present — i.e. the conversion doesn't turn more values null than
        # were already null.
        if converted_non_null < original_non_null:
            actions.append(
                CleaningAction(
                    column=col,
                    action="skip_type_conversion_unsafe",
                    detail="Some non-null values didn't parse as numbers — left as text "
                    "rather than risk losing data.",
                    affected=original_non_null - converted_non_null,
                )
            )
            continue

        df[col] = converted
        actions.append(
            CleaningAction(
                column=col,
                action="convert_type",
                detail=f"Converted '{col}' from text to numeric.",
                affected=converted_non_null,
            )
        )
    return actions


def _flag_outliers(quality_report: dict) -> list[CleaningAction]:
    # Outlier rows are never dropped automatically — a genuinely large
    # transaction is legitimate data, not noise. This just surfaces what
    # DataQualityAgent already found, for visibility.
    actions = []
    for col, count in (quality_report.get("outliers") or {}).items():
        if count:
            actions.append(
                CleaningAction(
                    column=col,
                    action="flag_outliers",
                    detail=f"{count} IQR-based outlier value(s) found and left in place "
                    "(not removed automatically).",
                    affected=count,
                )
            )
    return actions


class CleaningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "cleaning"

    async def execute(self, state: dict) -> dict:
        file_path = state["file_path"]
        quality_report = state.get("quality_report", {})
        df = _load_dataframe(file_path)

        df, dedup_actions = _drop_duplicates(df, quality_report)
        actions = [
            *dedup_actions,
            *_impute_missing(df, quality_report),
            *_convert_type_issues(df, quality_report),
            *_flag_outliers(quality_report),
        ]

        cleaned_file_path = _save_dataframe(df, file_path)

        state["cleaning_actions"] = [a.model_dump() for a in actions]
        state["cleaned_file_path"] = cleaned_file_path
        return state
