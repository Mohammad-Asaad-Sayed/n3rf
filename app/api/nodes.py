from typing import Any

from fastapi import APIRouter

from app.registry import load_all

router = APIRouter(tags=["nodes"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/nodes")
def catalog() -> list[dict[str, Any]]:
    return [spec.public() for spec in load_all().values()]
