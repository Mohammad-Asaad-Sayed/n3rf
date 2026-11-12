from typing import Any

from fastapi import APIRouter

from app.registry import load_all

router = APIRouter(tags=["nodes"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
def version() -> dict[str, str]:
    return {"version": "0.1.0", "license": "AGPL-3.0-only"}


@router.get("/nodes")
def catalog() -> list[dict[str, Any]]:
    return [spec.public() for spec in load_all().values()]
