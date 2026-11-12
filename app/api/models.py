import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import store
from app.errors import NodeError
from app.llm import test_connection
from app.schemas.workflow import ModelProfileRequest

router = APIRouter(prefix="/models", tags=["models"])

# Conventional env-var names for the provider presets baked into the node
# catalog. Only the name is looked up — values are never read into responses.
KNOWN_PROVIDER_ENVS = (
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "MISTRAL_API_KEY",
    "HUGGINGFACE_API_KEY",
    "CLOUDFLARE_API_TOKEN",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
)


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


@router.get("/status")
def model_status() -> dict[str, Any]:
    """Tell the UI whether any provider can actually be reached right now.

    A profile counts as ready when its api_key_env is set (or blank, for
    keyless local providers). Failing that, any conventional provider env
    var being set also counts. Only booleans leave this function — never
    key material.
    """
    profiles = store.list_model_profiles()

    def resolvable(profile: dict[str, Any]) -> bool:
        env = (profile.get("api_key_env") or "").strip()
        return not env or bool(os.environ.get(env))

    ready = any(resolvable(profile) for profile in profiles) or any(
        os.environ.get(name) for name in KNOWN_PROVIDER_ENVS
    )
    return {"ready": ready, "profiles": len(profiles)}


@router.delete("/{profile_id}", status_code=204)
def delete_model(profile_id: str) -> None:
    if not store.delete_model_profile(profile_id):
        raise HTTPException(status_code=404, detail="Model profile not found.")
