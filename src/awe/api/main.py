"""FastAPI uygulama giriş noktası.

Çalıştırma: `uvicorn awe.api.main:app --reload` (önce `alembic upgrade head` gerekir).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from awe.api.routes_events import router as events_router
from awe.api.routes_suggestions import router as suggestions_router
from awe.config import ProjectRegistry, configure_logging, get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.project_registry = ProjectRegistry(settings.project_config_dir)
    yield


app = FastAPI(
    title="Adaptive Workflow Engine",
    description="Event log tabanlı habit-to-shortcut öneri motoru.",
    version="0.1.0",
    lifespan=_lifespan,
)
app.include_router(events_router)
app.include_router(suggestions_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
