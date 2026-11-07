from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import ModelProfileRecord, RunRecord, WorkflowRecord


def _workflow_payload(record: WorkflowRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        **json.loads(record.data),
        "updated_at": record.updated_at.isoformat(sep=" "),
    }


def list_workflows() -> list[dict[str, Any]]:
    with Session(get_engine()) as db:
        records = db.scalars(select(WorkflowRecord).order_by(WorkflowRecord.updated_at.desc()))
        return [_workflow_payload(record) for record in records]


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    with Session(get_engine()) as db:
        record = db.get(WorkflowRecord, workflow_id)
        return _workflow_payload(record) if record else None


def save_workflow(workflow_id: str, name: str, data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "nodes": [
            {key: node[key] for key in ("id", "type", "node", "params", "position") if key in node}
            for node in data.get("nodes", [])
        ],
        "edges": [
            {
                key: edge[key]
                for key in ("source", "target", "from", "to", "target_input", "input")
                if key in edge
            }
            for edge in data.get("edges", [])
        ],
    }
    with Session(get_engine()) as db, db.begin():
        record = db.get(WorkflowRecord, workflow_id)
        if record is None:
            record = WorkflowRecord(id=workflow_id, name=name, data=json.dumps(payload))
            db.add(record)
        else:
            record.name = name
            record.data = json.dumps(payload)
            from sqlalchemy import func

            record.updated_at = func.current_timestamp()
    return get_workflow(workflow_id) or {}


def save_run(run: dict[str, Any], workflow_id: str | None = None) -> None:
    with Session(get_engine()) as db, db.begin():
        record = db.get(RunRecord, run["run_id"])
        if record is None:
            db.add(RunRecord(id=run["run_id"], workflow_id=workflow_id, data=json.dumps(run)))
        else:
            record.workflow_id = workflow_id
            record.data = json.dumps(run)


def get_run(run_id: str) -> dict[str, Any] | None:
    with Session(get_engine()) as db:
        record = db.get(RunRecord, run_id)
        return json.loads(record.data) if record else None


def delete_workflow(workflow_id: str) -> bool:
    with Session(get_engine()) as db, db.begin():
        record = db.get(WorkflowRecord, workflow_id)
        if record is None:
            return False
        db.delete(record)
        return True


def list_model_profiles() -> list[dict[str, Any]]:
    with Session(get_engine()) as db:
        records = db.scalars(select(ModelProfileRecord).order_by(ModelProfileRecord.name))
        return [_model_profile_payload(record) for record in records]


def _model_profile_payload(record: ModelProfileRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "base_url": record.base_url,
        "model": record.model,
        "api_key_env": record.api_key_env,
        "updated_at": record.updated_at.isoformat(sep=" "),
    }


def save_model_profile(profile: dict[str, str]) -> dict[str, Any]:
    with Session(get_engine()) as db, db.begin():
        record = db.get(ModelProfileRecord, profile["id"])
        if record is None:
            record = ModelProfileRecord(**profile)
            db.add(record)
        else:
            for key in ("name", "base_url", "model", "api_key_env"):
                setattr(record, key, profile[key])
    with Session(get_engine()) as db:
        saved = db.get(ModelProfileRecord, profile["id"])
        if saved is None:
            raise RuntimeError("Saved model profile was not found after commit.")
        return _model_profile_payload(saved)


def delete_model_profile(profile_id: str) -> bool:
    with Session(get_engine()) as db, db.begin():
        record = db.get(ModelProfileRecord, profile_id)
        if record is None:
            return False
        db.delete(record)
        return True
