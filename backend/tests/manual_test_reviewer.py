"""Manual test: ReviewerAgent's checks and the graph's rerun-loop wiring.

Not a pytest test (no assertions beyond plain asserts) — run directly:

    python -m tests.manual_test_reviewer

Case 1: a normal full pipeline run on sample_sales_fixed.csv — confirms
review_notes has no "critical" entries and needs_rerun is False.

Case 2: a mocked state with an impossible KPI value (negative revenue) —
confirms ReviewerAgent flags it "critical" and sets needs_rerun=True, then
confirms the SAME impossible value on a second pass (simulating a rerun
that didn't fix anything) is capped rather than triggering forever. Then,
using a mocked KpiAgent inside a small isolated graph (kpi -> reviewer,
looping back to kpi on demand), confirms the real graph wiring loops back
exactly once and terminates rather than hanging.
"""

import asyncio
import functools
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agents.cleaning import CleaningAgent
from app.agents.data_quality import DataQualityAgent
from app.agents.eda import EDAAgent
from app.agents.forecast import ForecastAgent
from app.agents.insight import InsightAgent
from app.agents.kpi import KpiAgent
from app.agents.planner import PlannerAgent
from app.agents.report import REPORTS_DIR, ReportAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.visualization import VisualizationAgent
from app.orchestrator.state import AnalysisState

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


async def case_1_normal_run() -> None:
    print("=== Case 1: normal full pipeline run (expect no critical notes) ===")
    state = {
        "file_path": FIXTURE_PATH,
        "run_id": "manual-test-reviewer-case1",
        "dataset_filename": "sample_sales_fixed.csv",
    }
    for agent in [
        PlannerAgent(),
        DataQualityAgent(),
        CleaningAgent(),
        EDAAgent(),
        ForecastAgent(),
        KpiAgent(),
        InsightAgent(),
        VisualizationAgent(),
        ReportAgent(),
        ReviewerAgent(),
    ]:
        state = await agent.run(state)

    if state.get("errors"):
        print("ERRORS during pipeline run:", state["errors"])

    review_notes = state.get("review_notes", [])
    print("review_notes:", review_notes)
    print("needs_rerun:", state.get("needs_rerun"))

    critical_notes = [n for n in review_notes if n["severity"] == "critical"]
    assert not critical_notes, f"expected no critical notes on a normal run, got {critical_notes}"
    assert state.get("needs_rerun") is False, "expected needs_rerun False on a normal run"
    print("Case 1 OK: no critical notes, needs_rerun is False.\n")

    Path(state["report_path"]).unlink(missing_ok=True)
    Path(FIXTURE_PATH).with_name("sample_sales_fixed_cleaned.csv").unlink(missing_ok=True)
    if REPORTS_DIR.exists() and not any(REPORTS_DIR.iterdir()):
        REPORTS_DIR.rmdir()


async def case_2a_direct_flagging() -> None:
    print("=== Case 2a: ReviewerAgent directly on a mocked impossible KPI ===")
    state = {
        "kpis": [
            {"label": "Total Revenue", "value": -500.0, "unit": "$", "format": "currency"},
            {"label": "Total Orders", "value": 10, "unit": "", "format": "number"},
            {"label": "Data Quality Score", "value": 95.0, "unit": "%", "format": "percent"},
        ],
        "insights": [
            {"title": "A", "description": "nothing numeric here", "severity": "info", "related_metric": "x"},
            {"title": "B", "description": "nothing numeric here either", "severity": "info", "related_metric": "y"},
            {"title": "C", "description": "still nothing numeric", "severity": "info", "related_metric": "z"},
        ],
        "quality_report": {"overall_score": 90.0, "duplicates": 0, "missing_by_column": {}},
        "eda_results": {},
    }

    state = await ReviewerAgent().run(state)
    critical_notes = [n for n in state["review_notes"] if n["severity"] == "critical"]
    print("review_notes:", state["review_notes"])
    assert critical_notes, "expected a critical note for the negative revenue KPI"
    assert state["needs_rerun"] is True
    assert state["rerun_agent"] == "kpi"
    assert state["review_rerun_count"] == 1
    print("first pass OK: critical flagged, needs_rerun=True, review_rerun_count=1")

    # Second pass, same unfixed impossible value — the cap must stop it here.
    state = await ReviewerAgent().run(state)
    assert state["needs_rerun"] is False, "rerun cap should prevent a second trigger"
    assert state["review_rerun_count"] == 1, "counter must not increment past the cap"
    assert any(n["check_name"] == "rerun_cap_reached" for n in state["review_notes"])
    print("second pass OK: cap enforced, needs_rerun=False, counter stayed at 1.\n")


async def _mock_kpi_node(state: dict, call_count: list[int]) -> dict:
    call_count[0] += 1
    state["current_agent"] = "kpi"
    # Always returns the same impossible value — a stand-in for a kpi
    # re-run that didn't actually fix anything, so the cap is what has to
    # stop the loop, not the data happening to become valid.
    state["kpis"] = [
        {"label": "Total Revenue", "value": -500.0, "unit": "$", "format": "currency"},
        {"label": "Data Quality Score", "value": 95.0, "unit": "%", "format": "percent"},
    ]
    state.setdefault(
        "insights",
        [
            {"title": "A", "description": "no numbers", "severity": "info", "related_metric": "x"},
            {"title": "B", "description": "no numbers", "severity": "info", "related_metric": "y"},
            {"title": "C", "description": "no numbers", "severity": "info", "related_metric": "z"},
        ],
    )
    state.setdefault("quality_report", {"overall_score": 90.0, "duplicates": 0, "missing_by_column": {}})
    state.setdefault("eda_results", {})
    return state


def _route_after_review(state: AnalysisState) -> str:
    if state.get("needs_rerun") and state.get("rerun_agent"):
        return state["rerun_agent"]
    return END


async def case_2b_graph_loops_once_then_stops() -> None:
    print("=== Case 2b: isolated kpi<->reviewer graph with a mocked KpiAgent ===")
    call_count = [0]

    graph = StateGraph(AnalysisState)
    graph.add_node("kpi", functools.partial(_mock_kpi_node, call_count=call_count))
    graph.add_node("reviewer", ReviewerAgent().run)
    graph.add_edge(START, "kpi")
    graph.add_edge("kpi", "reviewer")
    graph.add_conditional_edges("reviewer", _route_after_review, {"kpi": "kpi", END: END})
    compiled = graph.compile()

    final_state = await compiled.ainvoke({})

    print("kpi node call count:", call_count[0])
    print("final review_rerun_count:", final_state.get("review_rerun_count"))
    print("final needs_rerun:", final_state.get("needs_rerun"))
    print("final review_notes:", final_state.get("review_notes"))

    assert call_count[0] == 2, f"expected kpi to run exactly twice (initial + 1 rerun), got {call_count[0]}"
    assert final_state.get("review_rerun_count") == 1
    assert final_state.get("needs_rerun") is False
    assert any(n["check_name"] == "rerun_cap_reached" for n in final_state["review_notes"])
    print("Case 2b OK: graph looped back exactly once, then terminated at END.\n")


async def main() -> None:
    await case_1_normal_run()
    await case_2a_direct_flagging()
    await case_2b_graph_loops_once_then_stops()
    print("All ReviewerAgent checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
