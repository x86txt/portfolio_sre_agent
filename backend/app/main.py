import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router


def create_app() -> FastAPI:
    # Load .env files if present (dev convenience; files are gitignored).
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:  # pragma: no cover
        load_dotenv = None

    if load_dotenv:
        here = Path(__file__).resolve()
        backend_dir = here.parents[1]  # backend/
        repo_root = here.parents[2]  # repo root
        load_dotenv(repo_root / ".env", override=False)
        load_dotenv(backend_dir / ".env", override=False)

    app = FastAPI(
        title="aiTriage API",
        version="0.1.0",
        description="Ingest alerts, correlate signals, and generate situation reports + runbook steps.",
        openapi_version="3.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    cors_origins = os.getenv(
        "AITRIAGE_CORS_ORIGINS",
        "http://localhost:4321,http://127.0.0.1:4321,http://localhost:3000",
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    # Serve frontend static files (for production/fly.io deployment)
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()


