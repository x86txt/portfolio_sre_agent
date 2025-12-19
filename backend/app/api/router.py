from fastapi import APIRouter

from app.api.routes import admin, chat, incidents, ingest, llm, report, resolution, scenarios, stream

api_router = APIRouter()

api_router.include_router(ingest.router, tags=["ingest"])
api_router.include_router(incidents.router, tags=["incidents"])
api_router.include_router(report.router, tags=["report"])
api_router.include_router(llm.router, tags=["llm"])
api_router.include_router(resolution.router, tags=["resolution"])
api_router.include_router(scenarios.router, tags=["scenarios"])
api_router.include_router(stream.router, tags=["stream"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(admin.router, tags=["admin"])


