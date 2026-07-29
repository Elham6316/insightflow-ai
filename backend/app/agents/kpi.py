from typing import Literal

from pydantic import BaseModel

from app.agents.base import BaseAgent

_SALES_REVENUE_KEYWORDS = ("total", "revenue", "amount", "sales")
_UNIT_PRICE_KEYWORDS = ("unit_price", "price")
_FINANCE_AMOUNT_KEYWORDS = ("amount", "total", "value", "transaction")
_RESOLUTION_KEYWORDS = ("resolution", "duration", "days", "hours", "time")
_CATEGORY_NAME_KEYWORDS = ("category", "type", "issue", "reason")


class Kpi(BaseModel):
    label: str
    value: float | int | str
    unit: str
    format: Literal["currency", "number", "percent"]


def _pick_numeric_column(distributions: dict, keywords: tuple[str, ...]) -> str | None:
    cols = list(distributions.keys())
    for keyword in keywords:
        for col in cols:
            if keyword in col.lower():
                return col
    return None


def _stat(distributions: dict, col: str | None, stat: str, default=0):
    if not col:
        return default
    value = distributions.get(col, {}).get(stat)
    return value if value is not None else default


def _round(value, ndigits=2):
    try:
        return round(value, ndigits)
    except TypeError:
        return value


def _infer_total_rows(state: dict, eda_results: dict) -> int:
    # Prefer the exact row count from the upload profile; eda_results only
    # gives per-column non-null counts, so fall back to the max of those
    # (the least-null column's count is the best available proxy) when the
    # profile isn't present in state.
    profile_rows = (state.get("profile") or {}).get("shape", {}).get("rows")
    if profile_rows is not None:
        return int(profile_rows)

    distributions = eda_results.get("distributions") or {}
    counts = [s.get("count") for s in distributions.values() if s.get("count") is not None]
    return int(max(counts)) if counts else 0


def _quality_score_kpi(quality_report: dict) -> Kpi:
    score = quality_report.get("overall_score")
    return Kpi(
        label="Data Quality Score",
        value=_round(score) if score is not None else 0,
        unit="%",
        format="percent",
    )


def _sales_kpis(state: dict, eda_results: dict, quality_report: dict) -> list[Kpi]:
    distributions = eda_results.get("distributions") or {}
    total_rows = _infer_total_rows(state, eda_results)

    revenue_col = _pick_numeric_column(distributions, _SALES_REVENUE_KEYWORDS)
    if revenue_col:
        mean = _stat(distributions, revenue_col, "mean")
        count = _stat(distributions, revenue_col, "count")
        total_revenue = mean * count if mean and count else 0
        avg_value_kpi = Kpi(
            label="Average Order Value", value=_round(mean), unit="$", format="currency"
        )
    else:
        unit_price_col = _pick_numeric_column(distributions, _UNIT_PRICE_KEYWORDS)
        mean = _stat(distributions, unit_price_col, "mean") if unit_price_col else 0
        total_revenue = 0
        avg_value_kpi = Kpi(
            label="Average Unit Price", value=_round(mean), unit="$", format="currency"
        )

    return [
        Kpi(label="Total Revenue", value=_round(total_revenue), unit="$", format="currency"),
        Kpi(label="Total Orders", value=total_rows, unit="", format="number"),
        avg_value_kpi,
        _quality_score_kpi(quality_report),
    ]


def _finance_kpis(state: dict, eda_results: dict, quality_report: dict) -> list[Kpi]:
    distributions = eda_results.get("distributions") or {}
    total_rows = _infer_total_rows(state, eda_results)

    amount_col = _pick_numeric_column(distributions, _FINANCE_AMOUNT_KEYWORDS)
    mean = _stat(distributions, amount_col, "mean") if amount_col else 0
    count = _stat(distributions, amount_col, "count") if amount_col else 0
    total_amount = mean * count if mean and count else 0

    return [
        Kpi(label="Total Amount", value=_round(total_amount), unit="$", format="currency"),
        Kpi(label="Transaction Count", value=total_rows, unit="", format="number"),
        Kpi(
            label="Average Transaction Value",
            value=_round(mean),
            unit="$",
            format="currency",
        ),
        _quality_score_kpi(quality_report),
    ]


def _complaints_kpis(state: dict, eda_results: dict, quality_report: dict) -> list[Kpi]:
    distributions = eda_results.get("distributions") or {}
    categorical_summary = eda_results.get("categorical_summary") or {}
    total_rows = _infer_total_rows(state, eda_results)

    category_col = None
    for keyword in _CATEGORY_NAME_KEYWORDS:
        for col in categorical_summary:
            if keyword in col.lower():
                category_col = col
                break
        if category_col:
            break
    if category_col is None and categorical_summary:
        category_col = next(iter(categorical_summary))

    most_common_value = next(iter(categorical_summary[category_col])) if category_col else "N/A"

    resolution_col = _pick_numeric_column(distributions, _RESOLUTION_KEYWORDS)
    avg_resolution = _stat(distributions, resolution_col, "mean") if resolution_col else 0

    return [
        Kpi(label="Total Complaints", value=total_rows, unit="", format="number"),
        Kpi(label="Most Common Category", value=most_common_value, unit="", format="number"),
        Kpi(label="Avg Resolution Value", value=_round(avg_resolution), unit="", format="number"),
        _quality_score_kpi(quality_report),
    ]


def _generic_kpis(state: dict, eda_results: dict, quality_report: dict) -> list[Kpi]:
    total_rows = _infer_total_rows(state, eda_results)

    total_columns = (state.get("profile") or {}).get("shape", {}).get("columns")
    if total_columns is None:
        distributions = eda_results.get("distributions") or {}
        categorical_summary = eda_results.get("categorical_summary") or {}
        total_columns = len(distributions) + len(categorical_summary)

    missing_by_column = quality_report.get("missing_by_column") or {}
    most_complete_col = min(missing_by_column, key=missing_by_column.get) if missing_by_column else "N/A"

    return [
        Kpi(label="Total Rows", value=total_rows, unit="", format="number"),
        Kpi(label="Total Columns", value=int(total_columns), unit="", format="number"),
        Kpi(label="Most Complete Column", value=most_complete_col, unit="", format="number"),
        _quality_score_kpi(quality_report),
    ]


_DOMAIN_KPI_BUILDERS = {
    "sales": _sales_kpis,
    "finance": _finance_kpis,
    "complaints": _complaints_kpis,
}


class KpiAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "kpi"

    async def execute(self, state: dict) -> dict:
        data_domain = state.get("data_domain", "generic")
        eda_results = state.get("eda_results", {})
        quality_report = state.get("quality_report", {})

        builder = _DOMAIN_KPI_BUILDERS.get(data_domain, _generic_kpis)
        kpis = builder(state, eda_results, quality_report)

        state["kpis"] = [k.model_dump() for k in kpis]
        return state
