import base64
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(tags=["uploads"])


@router.post("/upload")
async def upload(file: Annotated[UploadFile, File()]) -> dict[str, str]:
    content = await file.read(10_000_001)
    if len(content) > 10_000_000:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
    return {
        "filename": file.filename or "upload",
        "content": base64.b64encode(content).decode("ascii"),
    }
