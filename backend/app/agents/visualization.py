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
        # No internal ECharts title — the dashboard card header renders the
        # title in HTML. One source of truth, so it never shows twice.
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
        # Rendered by the frontend as a caption below the chart, not inside
        # the ECharts option — putting it in title.subtext overlapped the
        # chart title itself.
        "note": " ".join(incomplete_notes) if incomplete_notes else None,
    }


def _heatmap_from_correlations(correlations: dict) -> dict | None:
    if not correlations:
        return None

    cols = list(correlations.keys())
    # Round to 2 decimals so cell labels ("0.81" vs "0.8123961052053926")
    # stay short enough not to collide with each other or the axis labels.
    data = []
    for row_idx, row_col in enumerate(cols):
        for col_idx, col_col in enumerate(cols):
            value = correlations[row_col].get(col_col)
            rounded = round(value, 2) if value is not None else None
            data.append([col_idx, row_idx, rounded if rounded is not None else "-"])

    # Rotate sooner than before (>=3 cols, not >4) — a 3-col dashboard grid
    # gives each heatmap card less width, so labels crowd at a lower count.
    rotate_labels = 30 if len(cols) >= 3 else 0

    title = "Correlation Heatmap"
    option = {
        # No internal ECharts title here — the dashboard already shows the
        # chart's title via the surrounding Card's own title.
        "tooltip": {"position": "top"},
        "axisPointer": {"show": False},
        # Tighter than a 2-col layout would need — these charts render in a
        # 3-col grid on desktop, so labels/margins are sized for a narrower
        # card.
        "grid": {"top": 30, "bottom": 44, "left": 70, "right": 16, "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": cols,
            "splitArea": {"show": True},
            "axisLabel": {"fontSize": 9, "interval": 0, "rotate": rotate_labels},
            "axisPointer": {"show": False},
        },
        "yAxis": {
            "type": "category",
            "data": cols,
            "splitArea": {"show": True},
            "axisLabel": {"fontSize": 9},
            "axisPointer": {"show": False},
        },
        "visualMap": {
            # min/max keep driving the color mapping for the heatmap cells;
            # show=False hides the visible legend component entirely (the
            # bar/handles/whatever else it renders) without affecting how
            # cell colors are computed.
            "min": -1,
            "max": 1,
            "show": False,
            # Brand-colored diverging scale: sunlight-yellow (negative) ->
            # soft-sand (near zero) -> coastal-blue (positive), instead of
            # ECharts' default blue gradient.
            "inRange": {"color": ["#FFD369", "#F7F9FC", "#3490DC"]},
        },
        "series": [
            {
                "name": "Correlation",
                "type": "heatmap",
                "data": data,
                "label": {"show": True, "fontSize": 9},
            }
        ],
    }

    return {
        "chart_type": "heatmap",
        "title": title,
        "echarts_option": option,
        "related_metric": "correlations",
        "note": None,
    }


def _bar_chart_from_categorical(col: str, counts: dict) -> dict:
    title = f"Top {_title_case(col)} Values"
    option = {
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
        "note": None,
    }


def _pie_chart_from_categorical(col: str, counts: dict) -> dict:
    title = f"{_title_case(col)} Breakdown"
    option = {
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
        "note": None,
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
    # An insight can fuzzy-match more than one chart (e.g. a bare
    # "categorical_summary" related_metric matches every categorical chart).
    # Only the first chart that matches a given insight title gets it, so we
    # never render the same title on two different charts; later charts keep
    # their generated default title instead.
    used_titles: set[str] = set()
    for chart in charts:
        matched_title = _find_matching_insight_title(chart["related_metric"], insights)
        if matched_title and matched_title not in used_titles:
            # No chart carries an internal ECharts title (the dashboard
            # card header is the only place a title renders), so only the
            # dict used by the HTML header needs updating here.
            chart["title"] = matched_title
            used_titles.add(matched_title)


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
