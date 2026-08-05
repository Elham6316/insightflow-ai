import logging

from langgraph.graph import END, START, StateGraph

from app.agents.base import BaseAgent
from app.agents.cleaning import CleaningAgent
from app.agents.data_quality import DataQualityAgent
from app.agents.eda import EDAAgent
from app.agents.forecast import ForecastAgent
from app.agents.insight import InsightAgent
from app.agents.kpi import KpiAgent
from app.agents.planner import PlannerAgent
from app.agents.report import ReportAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.visualization import VisualizationAgent
from app.orchestrator.state import AnalysisState

logger = logging.getLogger(__name__)


def _make_node(agent: BaseAgent):
    """Wrap an agent into a LangGraph node.

    BaseAgent.run() already catches agent exceptions internally and records
    them in state["errors"] rather than raising, so the graph continues to
    the next node on its own. This wrapper adds the explicit
    warn-and-continue behavior at the orchestrator level, and defends
    against anything unexpected (e.g. a bug outside the agent's own guard)
    so a single node can never halt the whole graph.
    """

    async def node(state: AnalysisState) -> AnalysisState:
        state["current_agent"] = agent.name
        errors_before = len(state.get("errors") or [])

        try:
            state = await agent.run(state)
        except Exception as exc:  # noqa: BLE001 - last-resort guard, node must not halt the graph
            logger.warning(
                "orchestrator: node %s raised unexpectedly, continuing: %s",
                agent.name,
                exc,
            )
            state.setdefault("errors", []).append(
                {"agent": agent.name, "error": str(exc)}
            )

        errors_after = state.get("errors") or []
        if len(errors_after) > errors_before:
            logger.warning(
                "orchestrator: node %s recorded error(s), continuing to next node: %s",
                agent.name,
                errors_after[errors_before:],
            )

        return state

    return node


def _route_after_review(state: AnalysisState) -> str:
    # ReviewerAgent already enforces the rerun cap (review_rerun_count) and
    # only sets needs_rerun when it actually incremented the counter, so
    # this just reads the decision rather than re-deriving it — the only
    # way this could loop forever is if ReviewerAgent's own cap logic broke.
    if state.get("needs_rerun") and state.get("rerun_agent"):
        return state["rerun_agent"]
    return END


def build_graph():
    graph = StateGraph(AnalysisState)

    graph.add_node("planner", _make_node(PlannerAgent()))
    graph.add_node("data_quality", _make_node(DataQualityAgent()))
    graph.add_node("cleaning", _make_node(CleaningAgent()))
    graph.add_node("eda", _make_node(EDAAgent()))
    graph.add_node("forecast", _make_node(ForecastAgent()))
    graph.add_node("kpi", _make_node(KpiAgent()))
    graph.add_node("insight", _make_node(InsightAgent()))
    graph.add_node("visualization", _make_node(VisualizationAgent()))
    graph.add_node("report", _make_node(ReportAgent()))
    graph.add_node("reviewer", _make_node(ReviewerAgent()))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "data_quality")
    graph.add_edge("data_quality", "cleaning")
    graph.add_edge("cleaning", "eda")
    graph.add_edge("eda", "forecast")
    graph.add_edge("forecast", "kpi")
    graph.add_edge("kpi", "insight")
    graph.add_edge("insight", "visualization")
    graph.add_edge("visualization", "report")
    graph.add_edge("report", "reviewer")
    graph.add_conditional_edges("reviewer", _route_after_review, {"kpi": "kpi", END: END})

    return graph.compile()


async def run_analysis(initial_state: AnalysisState) -> AnalysisState:
    app = build_graph()
    initial_state.setdefault("status", "running")
    final_state = await app.ainvoke(initial_state)
    final_state["status"] = "done" if not final_state.get("errors") else "done_with_errors"
    return final_state
