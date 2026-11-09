import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import store
from app.errors import NodeError
from app.llm import test_connection
from app.schemas.workflow import ModelProfileRequest

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models() -> list[dict[str, Any]]:
    return store.list_model_profiles()


@router.post("", status_code=201)
def save_model(request: ModelProfileRequest) -> dict[str, Any]:
    profile = request.model_dump(exclude={"api_key"})
    profile["id"] = request.id or f"model_{uuid.uuid4().hex[:12]}"
    return store.save_model_profile(profile)


@router.post("/test")
async def test_model(request: ModelProfileRequest) -> dict[str, Any]:
    try:
        return await test_connection(
            request.base_url, request.api_key_env, request.model, request.api_key
        )
    except NodeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{profile_id}", status_code=204)
def delete_model(profile_id: str) -> None:
    if not store.delete_model_profile(profile_id):
        raise HTTPException(status_code=404, detail="Model profile not found.")
