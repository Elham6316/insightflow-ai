from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import AgentOutput, AnalysisRun, Dataset, Insight
from app.db.session import get_db
from app.agents.report import REPORTS_DIR
from app.orchestrator.graph import run_analysis
from app.orchestrator.state import AnalysisState
from app.services.data_loader import load_and_profile

router = APIRouter()

# Which piece of the final state each agent's row in agent_outputs should
# store. InsightAgent's, KpiAgent's and VisualizationAgent's outputs are
# wrapped since state["insights"]/state["kpis"]/state["visualizations"] are
# bare lists, not dicts, and `output` is a JSONB column.
_AGENT_OUTPUT_FIELDS = {
    "planner": "planner_output",
    "data_quality": "quality_report",
    "eda": "eda_results",
    "forecast": "forecast",
}
_LIST_AGENT_OUTPUT_FIELDS = {
    "cleaning": "cleaning_actions",
    "kpi": "kpis",
    "insight": "insights",
    "visualization": "visualizations",
}


def _agent_status(agent_name: str, errors: list[dict]) -> str:
    if any(err.get("agent") == agent_name for err in errors):
        return "failed"
    return "success"


@router.post("/analysis/{dataset_id}/run")
async def run_dataset_analysis(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        profile = load_and_profile(dataset.file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not load dataset file: {exc}"
        ) from exc

    run = AnalysisRun(dataset_id=dataset.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    initial_state: AnalysisState = {
        "dataset_id": str(dataset.id),
        "file_path": dataset.file_path,
        "profile": profile,
        "run_id": str(run.id),
        "dataset_filename": dataset.filename,
    }
    final_state = await run_analysis(initial_state)

    errors = final_state.get("errors") or []

    for agent_name, state_key in _AGENT_OUTPUT_FIELDS.items():
        db.add(
            AgentOutput(
                run_id=run.id,
                agent_name=agent_name,
                output=final_state.get(state_key) or {},
                status=_agent_status(agent_name, errors),
            )
        )
    for agent_name, state_key in _LIST_AGENT_OUTPUT_FIELDS.items():
        db.add(
            AgentOutput(
                run_id=run.id,
                agent_name=agent_name,
                output={state_key: final_state.get(state_key) or []},
                status=_agent_status(agent_name, errors),
            )
        )

    db.add(
        AgentOutput(
            run_id=run.id,
            agent_name="report",
            output={
                "executive_summary": final_state.get("executive_summary"),
                "report_path": final_state.get("report_path"),
            },
            status=_agent_status("report", errors),
        )
    )

    for insight in final_state.get("insights") or []:
        db.add(
            Insight(
                run_id=run.id,
                title=insight.get("title"),
                description=insight.get("description"),
                severity=insight.get("severity"),
                chart_ref=insight.get("related_metric"),
            )
        )

    run.status = final_state.get("status", "done")
    run.current_agent = final_state.get("current_agent")
    run.finished_at = datetime.now(timezone.utc)
    db.commit()

    response = {"run_id": str(run.id), "final_state": final_state}
    if run.status == "done_with_errors":
        response["note"] = (
            "One or more agents failed during this run; the pipeline still "
            "completed using fallback/partial results. See final_state.errors "
            "for details."
        )
    return response


@router.get("/analysis/{run_id}")
def get_analysis_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    dataset = db.get(Dataset, run.dataset_id)

    agent_outputs = (
        db.query(AgentOutput)
        .filter(AgentOutput.run_id == run.id)
        .order_by(AgentOutput.created_at)
        .all()
    )
    insights = (
        db.query(Insight)
        .filter(Insight.run_id == run.id)
        .order_by(Insight.created_at)
        .all()
    )

    outputs_by_agent = {ao.agent_name: ao.output for ao in agent_outputs}
    planner_output = outputs_by_agent.get("planner") or {}
    quality_report = outputs_by_agent.get("data_quality") or {}
    visualizations = (outputs_by_agent.get("visualization") or {}).get(
        "visualizations", []
    )
    kpis = (outputs_by_agent.get("kpi") or {}).get("kpis", [])
    cleaning_actions = (outputs_by_agent.get("cleaning") or {}).get("cleaning_actions", [])
    forecast = outputs_by_agent.get("forecast") or {}

    response = {
        "run_id": str(run.id),
        "dataset_id": str(run.dataset_id),
        "dataset_filename": dataset.filename if dataset else None,
        "status": run.status,
        "current_agent": run.current_agent,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "data_domain": planner_output.get("data_domain"),
        "quality_report": quality_report,
        "cleaning_actions": cleaning_actions,
        "forecast": forecast,
        "kpis": kpis,
        "visualizations": visualizations,
        "agent_outputs": [
            {
                "id": str(ao.id),
                "agent_name": ao.agent_name,
                "output": ao.output,
                "status": ao.status,
                "duration_ms": ao.duration_ms,
                "created_at": ao.created_at,
            }
            for ao in agent_outputs
        ],
        "insights": [
            {
                "id": str(i.id),
                "title": i.title,
                "description": i.description,
                "severity": i.severity,
                "chart_ref": i.chart_ref,
                "created_at": i.created_at,
            }
            for i in insights
        ],
    }
    if run.status == "done_with_errors":
        response["note"] = (
            "One or more agents failed during this run; the pipeline still "
            "completed using fallback/partial results."
        )
    return response


@router.get("/analysis/{run_id}/report")
def download_analysis_report(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    # ReportAgent always saves to this deterministic path (app/agents/report.py).
    report_path = REPORTS_DIR / f"{run_id}.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="No report has been generated for this run")

    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=f"insightflow-report-{run_id}.pdf",
    )
