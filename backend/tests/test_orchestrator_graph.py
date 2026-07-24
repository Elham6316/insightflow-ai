import json
import uuid
from pathlib import Path

import pytest

from app.orchestrator.graph import run_analysis
from app.services.data_loader import load_and_profile

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


@pytest.mark.asyncio
async def test_full_graph_upload_through_visualization():
    # Mirrors what POST /upload does (app/api/routes_upload.py): profile the
    # file first, then hand the result into the pipeline as the initial state.
    profile = load_and_profile(FIXTURE_PATH)

    initial_state = {
        "dataset_id": str(uuid.uuid4()),
        "file_path": FIXTURE_PATH,
        "profile": profile,
    }

    final_state = await run_analysis(initial_state)

    print("\n---FINAL STATE---")
    print(json.dumps(final_state, indent=2, default=str))

    assert final_state.get("errors") is None
    assert final_state["status"] == "done"
    assert final_state["current_agent"] == "visualization"

    assert final_state.get("data_domain")
    assert isinstance(final_state.get("agents_to_run"), list)

    assert final_state.get("quality_report")
    assert "overall_score" in final_state["quality_report"]

    assert final_state.get("eda_results")
    assert final_state["eda_results"]["distributions"]
    assert final_state["eda_results"]["trends"]

    assert final_state.get("insights")
    assert 3 <= len(final_state["insights"]) <= 6

    assert final_state.get("visualizations")
    for chart in final_state["visualizations"]:
        assert chart["chart_type"] in {"line", "bar", "pie", "heatmap"}
        assert chart["title"]
        assert "series" in chart["echarts_option"] or "visualMap" in chart["echarts_option"]
