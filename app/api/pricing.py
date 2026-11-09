from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.pricing import MODEL_PRICES, PRICING_LAST_UPDATED, estimate_cost
from app.services.parse_xlsx import parse_xlsx_bytes

router = APIRouter(tags=["pricing"])


class EstimateRequest(BaseModel):
    rows: int = Field(ge=0, le=1_000_000)
    model: str = Field(min_length=1, max_length=160)
    input_tokens_per_row: int = Field(default=0, ge=0, le=1_000_000)
    output_tokens_per_row: int = Field(default=0, ge=0, le=1_000_000)


@router.get("/pricing")
def get_pricing() -> dict[str, Any]:
    return {
        "updated": PRICING_LAST_UPDATED,
        "models": MODEL_PRICES,
        "note": "Published list prices per 1M tokens, USD. n3rf adds $0.",
    }


@router.post("/pricing/estimate")
def post_estimate(request: EstimateRequest) -> dict[str, Any]:
    return estimate_cost(
        request.rows,
        request.input_tokens_per_row,
        request.output_tokens_per_row,
        request.model,
    )


@router.post("/parse-file")
async def parse_file(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """Parse an .xlsx upload in Python (stdlib only) -> rows + CSV text."""
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=422,
            detail="Only .xlsx spreadsheets are parsed here. CSV uses the CSV import flow.",
        )
    if filename.endswith(".xls"):
        raise HTTPException(
            status_code=422,
            detail="Legacy .xls is not supported. Resave as .xlsx or CSV and try again.",
        )
    content = await file.read(10_000_001)
    if len(content) > 10_000_000:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
    try:
        return parse_xlsx_bytes(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
