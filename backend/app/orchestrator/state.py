from typing import Any, TypedDict


class AnalysisState(TypedDict, total=False):
    dataset_id: str
    file_path: str
    profile: dict[str, Any]

    # set by routes_analysis.py before invoking the graph, so ReportAgent
    # (the final node) has the run's id for its output filename and the
    # original filename for the report header — both only exist in the DB,
    # not anywhere else in state.
    run_id: str
    dataset_filename: str

    # written by PlannerAgent (app/agents/planner.py)
    data_domain: str
    has_time_series: bool
    reasoning: str
    agents_to_run: list[str]
    planner_output: dict[str, Any]

    # written by DataQualityAgent (app/agents/data_quality.py)
    quality_report: dict[str, Any]

    # written by CleaningAgent (app/agents/cleaning.py). EDAAgent reads
    # cleaned_file_path in preference to file_path when present.
    cleaning_actions: list[dict[str, Any]]
    cleaned_file_path: str

    # written by EDAAgent (app/agents/eda.py)
    eda_results: dict[str, Any]

    # written by ForecastAgent (app/agents/forecast.py)
    forecast: dict[str, Any]

    # written by KpiAgent (app/agents/kpi.py)
    kpis: list[dict[str, Any]]

    # written by InsightAgent (app/agents/insight.py)
    insights: list[dict[str, Any]]

    # written by VisualizationAgent (app/agents/visualization.py)
    visualizations: list[dict[str, Any]]

    # written by ReportAgent (app/agents/report.py)
    executive_summary: str
    report_path: str

    # written by BaseAgent.run() on any agent failure (app/agents/base.py)
    errors: list[dict[str, Any]]

    # orchestrator-managed run bookkeeping
    status: str
    current_agent: str
