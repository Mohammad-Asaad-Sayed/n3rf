import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from app import store
from app.errors import NodeError
from app.schemas.workflow import WorkflowRequest
from app.services.execution import validate_graph

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
def list_workflows() -> list[dict[str, Any]]:
    return store.list_workflows()


@router.post("", status_code=201)
def create_workflow(request: WorkflowRequest) -> dict[str, Any]:
    workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
    try:
        validate_graph(request.nodes, request.edges)
    except NodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save_workflow(workflow_id, request.name, request.model_dump())


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str) -> dict[str, Any]:
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return workflow


@router.put("/{workflow_id}")
def update_workflow(workflow_id: str, request: WorkflowRequest) -> dict[str, Any]:
    if store.get_workflow(workflow_id) is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    try:
        validate_graph(request.nodes, request.edges)
    except NodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save_workflow(workflow_id, request.name, request.model_dump())


@router.delete("/{workflow_id}", status_code=204)
def remove_workflow(workflow_id: str) -> Response:
    if not store.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return Response(status_code=204)
