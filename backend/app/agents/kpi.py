import re
from typing import Literal

from pydantic import BaseModel

from app.agents.base import BaseAgent

_SALES_REVENUE_KEYWORDS = ("total", "revenue", "amount", "sales")
_UNIT_PRICE_KEYWORDS = ("unit_price", "price")
# "spent"/"spend"/"actual" are checked before "budget"/"allocated" so that,
# when a dataset has both (e.g. budget_allocated + actual_spent), the KPI
# lands on the real transacted amount rather than the planned/budgeted one.
_FINANCE_AMOUNT_KEYWORDS = (
    "amount",
    "total",
    "value",
    "transaction",
    "spent",
    "spend",
    "actual",
    "expense",
    "budget",
    "allocated",
)
_RESOLUTION_KEYWORDS = ("resolution", "duration", "days", "hours", "time")
_CATEGORY_NAME_KEYWORDS = ("category", "type", "issue", "reason")

_ID_COLUMN_NAME_RE = re.compile(r"(^|_)id$", re.IGNORECASE)


class Kpi(BaseModel):
    label: str
    value: float | int | str
    unit: str
    format: Literal["currency", "number", "percent"]


def _pick_numeric_column(distributions: dict, keywords: tuple[str, ...]) -> str | None:
    # id-like columns are skipped even on a keyword hit — e.g. "transaction"
    # matching "transaction_id" would otherwise win over a real amount
    # column just because a keyword happens to be a substring of an id
    # column's name. This is the same check the durable magnitude-based
    # fallback below uses, applied here too rather than only there.
    for keyword in keywords:
        for col, stats in distributions.items():
            if keyword in col.lower() and not _looks_like_id_column(col, stats):
                return col
    return None


def _looks_like_id_column(col: str, stats: dict) -> bool:
    """True for columns that are almost certainly an identifier, not a
    meaningful amount — by name (*_id) or by shape (a dense run of unique
    sequential integers, e.g. 1..15 with no gaps, which is exactly what an
    autoincrementing id column looks like from `describe()` stats alone)."""
    if _ID_COLUMN_NAME_RE.search(col):
        return True

    count, min_v, max_v = stats.get("count"), stats.get("min"), stats.get("max")
    if count is None or min_v is None or max_v is None:
        return False
    if float(min_v).is_integer() and float(max_v).is_integer():
        if (max_v - min_v + 1) == count:
            return True
    return False


def _highest_magnitude_numeric_column(distributions: dict) -> str | None:
    """Durable fallback for keyword-based amount detection: when no column
    name matches any known keyword, pick whichever numeric column has the
    largest total magnitude (mean * count), skipping id-like columns. This
    is what keeps a newly-seen dataset's KPIs from silently showing $0.00
    just because its columns weren't a keyword this list happened to know
    about yet."""
    best_col, best_total = None, None
    for col, stats in distributions.items():
        if _looks_like_id_column(col, stats):
            continue
        mean, count = stats.get("mean"), stats.get("count")
        if mean is None or count is None:
            continue
        total = abs(mean * count)
        if best_total is None or total > best_total:
            best_col, best_total = col, total
    return best_col


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
    unit_price_col = _pick_numeric_column(distributions, _UNIT_PRICE_KEYWORDS)

    if revenue_col:
        mean = _stat(distributions, revenue_col, "mean")
        count = _stat(distributions, revenue_col, "count")
        total_revenue = mean * count if mean and count else 0
        avg_value_kpi = Kpi(
            label="Average Order Value", value=_round(mean), unit="$", format="currency"
        )
    elif unit_price_col:
        mean = _stat(distributions, unit_price_col, "mean")
        total_revenue = 0
        avg_value_kpi = Kpi(
            label="Average Unit Price", value=_round(mean), unit="$", format="currency"
        )
    else:
        # Durable fallback: no revenue/unit-price keyword matched at all, so
        # rather than silently showing $0.00, use whichever numeric column
        # actually carries the largest amounts (excluding id-like columns).
        fallback_col = _highest_magnitude_numeric_column(distributions)
        mean = _stat(distributions, fallback_col, "mean") if fallback_col else 0
        count = _stat(distributions, fallback_col, "count") if fallback_col else 0
        total_revenue = mean * count if mean and count else 0
        avg_value_kpi = Kpi(
            label="Average Transaction Value", value=_round(mean), unit="$", format="currency"
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

    amount_col = _pick_numeric_column(
        distributions, _FINANCE_AMOUNT_KEYWORDS
    ) or _highest_magnitude_numeric_column(distributions)
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
