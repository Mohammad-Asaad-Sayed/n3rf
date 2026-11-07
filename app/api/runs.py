from typing import Any

from fastapi import APIRouter, HTTPException

from app import store
from app.errors import NodeError
from app.schemas.workflow import RunRequest
from app.services.execution import run as execute_workflow

router = APIRouter(tags=["runs"])


@router.post("/run")
async def run_unsaved(request: RunRequest) -> dict[str, Any]:
    try:
        return await execute_workflow(
            request.nodes,
            request.edges,
            request.input_override,
            target_node_id=request.target_node_id,
        )
    except NodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/run")
async def run_saved(workflow_id: str) -> dict[str, Any]:
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    try:
        return await execute_workflow(workflow["nodes"], workflow["edges"], None, workflow_id)
    except NodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    result = store.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return result
