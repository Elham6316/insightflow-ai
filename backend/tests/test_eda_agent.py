from pathlib import Path

import pytest

from app.agents.eda import EDAAgent

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


@pytest.mark.asyncio
async def test_eda_agent_populates_all_sections():
    state = {"file_path": FIXTURE_PATH}
    state = await EDAAgent().run(state)

    assert state.get("errors") is None

    results = state["eda_results"]

    # distributions: numeric columns (quantity, unit_price, total) should be present
    assert results["distributions"]
    for col in ("quantity", "unit_price", "total"):
        assert col in results["distributions"]
        assert "mean" in results["distributions"][col]

    # correlations: at least 2 numeric columns -> non-empty matrix
    assert results["correlations"]
    assert "unit_price" in results["correlations"]
    assert "total" in results["correlations"]["unit_price"]

    # trends: 'date' column should be detected and produce monthly buckets
    assert results["trends"]
    assert results["trends"]["date_column"] == "date"
    assert results["trends"]["granularity"] == "month"
    assert len(results["trends"]["data"]) >= 1
    assert results["trends"]["data"][0]["count"] > 0

    # categorical_summary: product/category/region/customer_name should show up
    assert results["categorical_summary"]
    for col in ("product", "category", "region"):
        assert col in results["categorical_summary"]
        assert len(results["categorical_summary"][col]) > 0
