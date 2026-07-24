from app.agents.base import BaseAgent

# Must match app/agents/eda.py's _TOP_N_CATEGORIES. eda.py's categorical_summary
# always caps each column's value_counts at this many entries, so a column
# returning fewer than this many entries proves that's its *true* total
# category count (not just the top of a longer tail) — that's the signal we
# use below to decide pie vs. bar.
_TOP_N_CATEGORIES = 5
_PIE_CHART_MAX_CATEGORIES = 6

_REVENUE_LIKE_KEYWORDS = ("revenue", "total", "amount", "sales", "price", "sum")


def _title_case(col: str) -> str:
    return col.replace("_", " ").replace("-", " ").title()


def _pick_primary_numeric_column(numeric_cols: list[str]) -> str | None:
    if not numeric_cols:
        return None
    for keyword in _REVENUE_LIKE_KEYWORDS:
        for col in numeric_cols:
            if keyword in col.lower():
                return col
    return numeric_cols[0]


def _line_chart_from_trends(trends: dict) -> dict | None:
    data = trends.get("data") or []
    if not data:
        return None

    numeric_cols = sorted(
        {key[len("sum_") :] for row in data for key in row if key.startswith("sum_")}
    )
    primary_col = _pick_primary_numeric_column(numeric_cols)
    if primary_col is None:
        return None

    periods = [row["period"] for row in data]
    values = [row.get(f"sum_{primary_col}") for row in data]
    incomplete_notes = [
        row["note"] for row in data if row.get("incomplete_period") and row.get("note")
    ]

    title = f"{_title_case(primary_col)} Trend by Month"
    option = {
        "title": {
            "text": title,
            **({"subtext": " ".join(incomplete_notes)} if incomplete_notes else {}),
        },
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": periods},
        "yAxis": {"type": "value"},
        "series": [{"name": _title_case(primary_col), "type": "line", "data": values}],
    }

    return {
        "chart_type": "line",
        "title": title,
        "echarts_option": option,
        "related_metric": f"trends.sum_{primary_col}",
    }


def _heatmap_from_correlations(correlations: dict) -> dict | None:
    if not correlations:
        return None

    cols = list(correlations.keys())
    data = []
    for row_idx, row_col in enumerate(cols):
        for col_idx, col_col in enumerate(cols):
            value = correlations[row_col].get(col_col)
            data.append([col_idx, row_idx, value if value is not None else "-"])

    title = "Correlation Heatmap"
    option = {
        "title": {"text": title},
        "tooltip": {"position": "top"},
        "xAxis": {"type": "category", "data": cols},
        "yAxis": {"type": "category", "data": cols},
        "visualMap": {
            "min": -1,
            "max": 1,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
        },
        "series": [{"name": "Correlation", "type": "heatmap", "data": data, "label": {"show": True}}],
    }

    return {
        "chart_type": "heatmap",
        "title": title,
        "echarts_option": option,
        "related_metric": "correlations",
    }


def _bar_chart_from_categorical(col: str, counts: dict) -> dict:
    title = f"Top {_title_case(col)} Values"
    option = {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": list(counts.keys())},
        "yAxis": {"type": "value"},
        "series": [{"name": _title_case(col), "type": "bar", "data": list(counts.values())}],
    }

    return {
        "chart_type": "bar",
        "title": title,
        "echarts_option": option,
        "related_metric": f"categorical_summary.{col}",
    }


def _pie_chart_from_categorical(col: str, counts: dict) -> dict:
    title = f"{_title_case(col)} Breakdown"
    option = {
        "title": {"text": title},
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "name": _title_case(col),
                "type": "pie",
                "radius": "60%",
                "data": [{"name": k, "value": v} for k, v in counts.items()],
            }
        ],
    }

    return {
        "chart_type": "pie",
        "title": title,
        "echarts_option": option,
        "related_metric": f"categorical_summary.{col}",
    }


def _charts_from_categorical_summary(categorical_summary: dict) -> list[dict]:
    charts = []
    for col, counts in categorical_summary.items():
        if len(counts) < _TOP_N_CATEGORIES and len(counts) <= _PIE_CHART_MAX_CATEGORIES:
            charts.append(_pie_chart_from_categorical(col, counts))
        else:
            charts.append(_bar_chart_from_categorical(col, counts))
    return charts


def _find_matching_insight_title(related_metric: str, insights: list[dict]) -> str | None:
    for insight in insights:
        if insight.get("related_metric") == related_metric:
            return insight.get("title")

    # Fall back to a dotted-prefix match (e.g. chart "trends.sum_total" vs.
    # insight "trends", or chart "correlations" vs. insight
    # "correlations.total") — NOT a bare top-level-segment match, since that
    # would collapse e.g. "categorical_summary.region" and
    # "categorical_summary.product" together and misattribute titles across
    # unrelated columns.
    for insight in insights:
        insight_metric = insight.get("related_metric") or ""
        if not insight_metric:
            continue
        if related_metric.startswith(insight_metric + ".") or insight_metric.startswith(
            related_metric + "."
        ):
            return insight.get("title")

    return None


def _apply_insight_titles(charts: list[dict], insights: list[dict]) -> None:
    for chart in charts:
        matched_title = _find_matching_insight_title(chart["related_metric"], insights)
        if matched_title:
            chart["title"] = matched_title
            chart["echarts_option"]["title"]["text"] = matched_title


class VisualizationAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "visualization"

    async def execute(self, state: dict) -> dict:
        eda_results = state.get("eda_results", {})
        insights = state.get("insights", [])

        charts = []

        trend_chart = _line_chart_from_trends(eda_results.get("trends") or {})
        if trend_chart:
            charts.append(trend_chart)

        heatmap = _heatmap_from_correlations(eda_results.get("correlations") or {})
        if heatmap:
            charts.append(heatmap)

        charts.extend(
            _charts_from_categorical_summary(eda_results.get("categorical_summary") or {})
        )

        # Prefer an existing insight's title when it references the same
        # metric, since InsightAgent's titles are grounded, causal, and
        # business-oriented rather than mechanically generated.
        _apply_insight_titles(charts, insights)

        state["visualizations"] = charts
        return state
