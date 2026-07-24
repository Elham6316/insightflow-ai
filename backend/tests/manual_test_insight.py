"""Manual test: run DataQuality -> EDA -> Insight on sample_sales_fixed.csv and
pretty-print the generated insights for eyeball review.

Not a pytest test (no assertions) — it hits the real Gemini API and is meant
to be run directly:

    python tests/manual_test_insight.py
"""

import asyncio
import json
from pathlib import Path

from app.agents.data_quality import DataQualityAgent
from app.agents.eda import EDAAgent
from app.agents.insight import InsightAgent

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


async def main() -> None:
    state = {"file_path": FIXTURE_PATH, "data_domain": "sales"}

    state = await DataQualityAgent().run(state)
    state = await EDAAgent().run(state)
    state = await InsightAgent().run(state)

    if state.get("errors"):
        print("=== ERRORS ===")
        print(json.dumps(state["errors"], indent=2))
        print()

    print(f"=== INSIGHTS ({len(state.get('insights', []))}) ===\n")
    for i, insight in enumerate(state.get("insights", []), start=1):
        print(f"[{i}] {insight['title']}  ({insight['severity']})")
        print(f"    metric: {insight['related_metric']}")
        print(f"    {insight['description']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
