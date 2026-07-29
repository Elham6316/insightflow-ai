from typing import Any, TypedDict


class AnalysisState(TypedDict, total=False):
    dataset_id: str
    file_path: str
    profile: dict[str, Any]

    # written by PlannerAgent (app/agents/planner.py)
    data_domain: str
    has_time_series: bool
    reasoning: str
    agents_to_run: list[str]
    planner_output: dict[str, Any]

    # written by DataQualityAgent (app/agents/data_quality.py)
    quality_report: dict[str, Any]

    # written by EDAAgent (app/agents/eda.py)
    eda_results: dict[str, Any]

    # written by KpiAgent (app/agents/kpi.py)
    kpis: list[dict[str, Any]]

    # written by InsightAgent (app/agents/insight.py)
    insights: list[dict[str, Any]]

    # written by VisualizationAgent (app/agents/visualization.py)
    visualizations: list[dict[str, Any]]

    # written by BaseAgent.run() on any agent failure (app/agents/base.py)
    errors: list[dict[str, Any]]

    # orchestrator-managed run bookkeeping
    status: str
    current_agent: str
