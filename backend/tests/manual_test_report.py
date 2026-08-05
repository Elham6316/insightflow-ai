"""Manual test: run the full pipeline (through ReportAgent) on
sample_sales_fixed.csv and confirm a real, non-empty PDF is produced.

Not a pytest test (no assertions beyond a couple of sanity checks) — run
directly:

    python -m tests.manual_test_report
"""

import asyncio
import uuid
from pathlib import Path

from app.agents.cleaning import CleaningAgent
from app.agents.data_quality import DataQualityAgent
from app.agents.eda import EDAAgent
from app.agents.forecast import ForecastAgent
from app.agents.insight import InsightAgent
from app.agents.kpi import KpiAgent
from app.agents.planner import PlannerAgent
from app.agents.report import REPORTS_DIR, ReportAgent
from app.agents.visualization import VisualizationAgent

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "sample_sales_fixed.csv")
MIN_PDF_SIZE_BYTES = 1024

_PDF_MAGIC = b"%PDF-"


async def main() -> None:
    run_id = f"manual-test-{uuid.uuid4()}"
    state = {
        "file_path": FIXTURE_PATH,
        "run_id": run_id,
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
    ]:
        state = await agent.run(state)

    if state.get("errors"):
        print("ERRORS during pipeline run:")
        for err in state["errors"]:
            print(" ", err)

    print("executive_summary:")
    print(" ", state.get("executive_summary"))
    print()
    print("report_path:", state.get("report_path"))

    report_path = Path(state["report_path"])
    assert report_path.exists(), f"report file does not exist: {report_path}"

    size = report_path.stat().st_size
    print("report file size:", size, "bytes")
    assert size > MIN_PDF_SIZE_BYTES, f"report file suspiciously small: {size} bytes"

    header = report_path.read_bytes()[: len(_PDF_MAGIC)]
    assert header == _PDF_MAGIC, f"file does not look like a PDF (header: {header!r})"

    print(f"\nPDF check OK: {report_path} exists, {size} bytes, valid PDF header.")

    report_path.unlink()
    cleaned_fixture = Path(FIXTURE_PATH).with_name("sample_sales_fixed_cleaned.csv")
    cleaned_fixture.unlink(missing_ok=True)
    if not any(REPORTS_DIR.iterdir()):
        REPORTS_DIR.rmdir()


if __name__ == "__main__":
    asyncio.run(main())
