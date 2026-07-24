from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import AgentOutput, AnalysisRun, Dataset, Insight
from app.db.session import get_db
from app.orchestrator.graph import run_analysis
from app.orchestrator.state import AnalysisState
from app.services.data_loader import load_and_profile

router = APIRouter()

# Which piece of the final state each agent's row in agent_outputs should
# store. InsightAgent's output is wrapped since state["insights"] is a bare
# list, not a dict, and `output` is a JSONB column.
_AGENT_OUTPUT_FIELDS = {
    "planner": "planner_output",
    "data_quality": "quality_report",
    "eda": "eda_results",
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
    db.add(
        AgentOutput(
            run_id=run.id,
            agent_name="insight",
            output={"insights": final_state.get("insights") or []},
            status=_agent_status("insight", errors),
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

    response = {
        "run_id": str(run.id),
        "dataset_id": str(run.dataset_id),
        "status": run.status,
        "current_agent": run.current_agent,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
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
