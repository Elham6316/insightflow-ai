"""Manual test: run the full pipeline (planner -> data_quality -> eda ->
insight -> visualization) on sample_sales_fixed.csv and pretty-print the
generated chart specs, to sanity-check the ECharts option structure by eye.

Not a pytest test (no assertions) — it hits the real Gemini API and is meant
to be run directly:

    python -m tests.manual_test_visualization
"""

import asyncio
import json
import uuid
from pathlib import Path

from app.orchestrator.graph import run_analysis
from app.services.data_loader import load_and_profile

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


async def main() -> None:
    profile = load_and_profile(FIXTURE_PATH)
    initial_state = {
        "dataset_id": str(uuid.uuid4()),
        "file_path": FIXTURE_PATH,
        "profile": profile,
    }

    final_state = await run_analysis(initial_state)

    if final_state.get("errors"):
        print("=== ERRORS ===")
        print(json.dumps(final_state["errors"], indent=2))
        print()

    charts = final_state.get("visualizations", [])
    print(f"=== CHARTS ({len(charts)}) ===\n")
    for i, chart in enumerate(charts, start=1):
        print(f"[{i}] {chart['title']}  ({chart['chart_type']})")
        print(f"    related_metric: {chart['related_metric']}")
        print("    echarts_option:")
        print(
            "\n".join(
                f"      {line}"
                for line in json.dumps(chart["echarts_option"], indent=2).splitlines()
            )
        )
        print()


if __name__ == "__main__":
    asyncio.run(main())
