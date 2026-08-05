"""Manual test: run DataQuality -> Cleaning on sample_sales_fixed.csv (which
has known missing values in quantity/total/customer_name) and confirm the
cleaned file has those gaps filled, with no other row loss.

Not a pytest test (no assertions) — run directly:

    python -m tests.manual_test_cleaning
"""

import asyncio
import json
from pathlib import Path

import pandas as pd

from app.agents.cleaning import CleaningAgent
from app.agents.data_quality import DataQualityAgent

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")


async def main() -> None:
    original = pd.read_csv(FIXTURE_PATH)
    print(f"original: {len(original)} rows, missing values:")
    print(original.isna().sum()[original.isna().sum() > 0])
    print()

    state = {"file_path": FIXTURE_PATH}
    state = await DataQualityAgent().run(state)
    state = await CleaningAgent().run(state)

    if state.get("errors"):
        print("ERRORS:", json.dumps(state["errors"], indent=2))
        return

    print("cleaning_actions:")
    print(json.dumps(state["cleaning_actions"], indent=2))
    print()

    cleaned_path = state["cleaned_file_path"]
    print(f"cleaned file: {cleaned_path}")
    cleaned = pd.read_csv(cleaned_path)

    print(f"cleaned: {len(cleaned)} rows, missing values:")
    missing = cleaned.isna().sum()
    print(missing[missing > 0] if missing.any() else "(none)")

    duplicates_removed = state["quality_report"]["duplicates"]
    expected_rows = len(original) - duplicates_removed
    assert len(cleaned) == expected_rows, (
        f"row count changed by more than duplicate removal: "
        f"{len(original)} -> {len(cleaned)}, expected {expected_rows}"
    )
    print(f"\nrow count check OK: {len(original)} -> {len(cleaned)} "
          f"({duplicates_removed} duplicate(s) removed, no other row loss)")


if __name__ == "__main__":
    asyncio.run(main())
