"""Manual test: run DataQuality -> EDA -> Kpi on sample_sales_fixed.csv (and a
few synthetic domain variants) and pretty-print the computed KPIs, to confirm
real computed numbers rather than placeholders.

Not a pytest test (no assertions) — run directly:

    python -m tests.manual_test_kpi
"""

import asyncio
import json
from pathlib import Path

from app.agents.data_quality import DataQualityAgent
from app.agents.eda import EDAAgent
from app.agents.kpi import KpiAgent
from app.services.data_loader import load_and_profile

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


async def run_for_domain(file_path: str, data_domain: str) -> None:
    # Mirrors the real pipeline (routes_analysis.py always seeds state with
    # the upload profile) so KpiAgent's exact-row/column-count path is
    # exercised the same way it is in production, not just its fallback.
    profile = load_and_profile(file_path)
    state = {"file_path": file_path, "data_domain": data_domain, "profile": profile}
    state = await DataQualityAgent().run(state)
    state = await EDAAgent().run(state)
    state = await KpiAgent().run(state)

    print(f"=== domain={data_domain} file={file_path} ===")
    if state.get("errors"):
        print("ERRORS:", json.dumps(state["errors"], indent=2))
    print(json.dumps(state["kpis"], indent=2))
    print()


async def main() -> None:
    await run_for_domain(FIXTURE_PATH, "sales")
    await run_for_domain(FIXTURE_PATH, "generic")


if __name__ == "__main__":
    asyncio.run(main())
