from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    models_router,
    nodes_router,
    pricing_router,
    runs_router,
    upload_router,
    workflows_router,
)

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
STATIC_DIR = APP_DIR / "static"
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"


def create_app() -> FastAPI:
    application = FastAPI(
        title="n3rf",
        version="0.1.0",
        description="Local-first AI workflow builder for structured row pipelines.",
    )
    application.include_router(nodes_router)
    application.include_router(models_router)
    application.include_router(pricing_router)
    application.include_router(runs_router)
    application.include_router(workflows_router)
    application.include_router(upload_router)

    # Micro-SaaS split hosting: static frontend may call this API cross-origin.
    # Secrets never travel in URLs; model keys live only in this process env.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    if FRONTEND_ASSETS.is_dir():
        application.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_ASSETS),
            name="frontend-assets",
        )
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def _index_response() -> FileResponse:
        index = FRONTEND_DIST / "index.html"
        if not index.is_file():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Frontend build is missing. Run "
                    "'cd frontend && pnpm install && pnpm run build'."
                ),
            )
        return FileResponse(index)

    @application.get("/", include_in_schema=False)
    def editor() -> FileResponse:
        return _index_response()

    @application.get("/app", include_in_schema=False)
    def app_home() -> FileResponse:
        return _index_response()

    @application.get("/app/{rest:path}", include_in_schema=False)
    def app_subpath(rest: str) -> FileResponse:
        return _index_response()

    @application.get("/alternatives/claygent", include_in_schema=False)
    def claygent_alternative() -> FileResponse:
        return _index_response()

    @application.get("/legal", include_in_schema=False)
    def legal_page() -> FileResponse:
        return _index_response()

    @application.get("/eva01-tokens.css", include_in_schema=False)
    def editor_tokens() -> FileResponse:
        return FileResponse(STATIC_DIR / "eva01-tokens.css", media_type="text/css")

    return application


app = create_app()
