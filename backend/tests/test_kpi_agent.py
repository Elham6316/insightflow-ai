from pathlib import Path

import pytest

from app.agents.eda import EDAAgent
from app.agents.kpi import KpiAgent
from app.services.data_loader import load_and_profile

FINANCE_FIXTURE = str(Path(__file__).parent / "fixtures" / "sample_finance.csv")


async def _kpis_for_finance_fixture() -> dict[str, object]:
    profile = load_and_profile(FINANCE_FIXTURE)
    state = {"file_path": FINANCE_FIXTURE, "data_domain": "finance", "profile": profile}
    state = await EDAAgent().run(state)
    state = await KpiAgent().run(state)
    assert not state.get("errors"), state.get("errors")
    return {kpi["label"]: kpi for kpi in state["kpis"]}


@pytest.mark.asyncio
async def test_finance_kpis_use_actual_spent_not_zero():
    """Regression test: budget_allocated/actual_spent/variance column names
    matched none of the original finance keywords ("amount", "total",
    "value", "transaction"), so Total Amount and Average Transaction Value
    silently rendered as $0.00 despite 15 real transactions. Both should now
    reflect the real `actual_spent` figures.
    """
    kpis = await _kpis_for_finance_fixture()

    total_amount = kpis["Total Amount"]
    avg_value = kpis["Average Transaction Value"]

    assert total_amount["value"] > 0
    assert avg_value["value"] > 0

    # actual_spent sums to 204,478.65 across the 15 fixture rows (mean
    # 13,631.91); pin to that so a future keyword-order change that quietly
    # picks budget_allocated instead (sum 204,600.00 — deliberately close,
    # so this test only passes if the *right* column was picked, not just
    # *a* plausible-looking one) would fail loudly.
    assert total_amount["value"] == pytest.approx(204478.65, abs=1)
    assert avg_value["value"] == pytest.approx(13631.91, abs=1)


@pytest.mark.asyncio
async def test_finance_kpis_exclude_id_column_from_fallback():
    """The durable highest-magnitude fallback must never pick an id-like
    column (transaction_id here is a dense 1..15 sequential run) even
    though its sum could otherwise look large."""
    kpis = await _kpis_for_finance_fixture()

    # transaction_id sums to 120 with a mean of 8 — nowhere near
    # actual_spent's totals, so this also indirectly confirms the fallback
    # (if it were ever exercised) wouldn't land on it.
    assert kpis["Average Transaction Value"]["value"] != pytest.approx(8, abs=0.5)
