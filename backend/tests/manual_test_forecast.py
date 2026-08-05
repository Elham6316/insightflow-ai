"""Manual test: ForecastAgent's skip path and its actual forecasting path.

Not a pytest test (no assertions) — run directly:

    python -m tests.manual_test_forecast

Case 1: sample_sales_fixed.csv only has 2 monthly periods and the second is
incomplete, so only 1 complete period is available — below the minimum of 4,
so ForecastAgent should skip with a clear reason.

Case 2: a synthetic dataset with 6 full months of data, to confirm the
linear-trend forecasting path produces 3 future periods with sensible
predicted values and confidence bounds.
"""

import asyncio
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.agents.cleaning import CleaningAgent
from app.agents.data_quality import DataQualityAgent
from app.agents.eda import EDAAgent
from app.agents.forecast import ForecastAgent

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SALES_FIXTURE = str(FIXTURES_DIR / "sample_sales_fixed.csv")
SYNTHETIC_FIXTURE = FIXTURES_DIR / "sample_forecast_synthetic.csv"


def _make_synthetic_fixture() -> None:
    rng = np.random.default_rng(42)
    dates, revenue = [], []
    for month in range(1, 7):  # Jan..Jun 2025, 6 full months
        days = [3, 10, 17, 24, 28] if month < 6 else [3, 10, 17, 24, 28, 30]
        for day in days:
            dates.append(f"2025-{month:02d}-{day:02d}")
            trend = 1000 + month * 150  # clear upward trend, easy to sanity-check
            revenue.append(round(float(trend + rng.normal(0, 40)), 2))
    pd.DataFrame({"date": dates, "revenue": revenue}).to_csv(SYNTHETIC_FIXTURE, index=False)


async def _run_through_forecast(file_path: str, has_time_series: bool) -> dict:
    state = {"file_path": file_path}
    state = await DataQualityAgent().run(state)
    state = await CleaningAgent().run(state)
    state = await EDAAgent().run(state)
    # PlannerAgent normally sets this via an LLM call; set it directly here
    # to keep this test isolated from the LLM.
    state["has_time_series"] = has_time_series
    state = await ForecastAgent().run(state)

    if state.get("errors"):
        print("ERRORS:", json.dumps(state["errors"], indent=2))
    return state


async def main() -> None:
    print("=== Case 1: sample_sales_fixed.csv (expect SKIP) ===")
    state = await _run_through_forecast(SALES_FIXTURE, has_time_series=True)
    print(json.dumps(state["forecast"], indent=2))
    assert state["forecast"]["skipped"] is True

    print("\n=== Case 2: synthetic 6-month dataset (expect real forecast) ===")
    _make_synthetic_fixture()
    try:
        state = await _run_through_forecast(str(SYNTHETIC_FIXTURE), has_time_series=True)
        print(json.dumps(state["forecast"], indent=2))
        assert state["forecast"]["skipped"] is False
        assert len(state["forecast"]["forecast_points"]) == 3
        for point in state["forecast"]["forecast_points"]:
            assert point["lower_bound"] <= point["predicted_value"] <= point["upper_bound"]
        print("\nforecast shape check OK: 3 future periods, each within its own bounds")
    finally:
        SYNTHETIC_FIXTURE.unlink(missing_ok=True)
        cleaned = SYNTHETIC_FIXTURE.with_name(f"{SYNTHETIC_FIXTURE.stem}_cleaned.csv")
        cleaned.unlink(missing_ok=True)

    sales_cleaned = Path(SALES_FIXTURE).with_name("sample_sales_fixed_cleaned.csv")
    sales_cleaned.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
