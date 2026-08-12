"""FastAPI bağımlılık enjeksiyonu: veritabanı session'ı ve proje konfigürasyonu."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from awe.config import ProjectConfig, ProjectNotFoundError, ProjectRegistry, Settings, get_settings
from awe.persistence import create_database_engine, create_session_factory


@lru_cache
def _session_factory_for(database_url: str) -> sessionmaker[Session]:
    engine = create_database_engine(database_url)
    return create_session_factory(engine)


def get_db_session(request: Request) -> Iterator[Session]:
    settings: Settings = request.app.state.settings
    factory = _session_factory_for(settings.database_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_project_registry(request: Request) -> ProjectRegistry:
    return request.app.state.project_registry


def get_project_config(
    project_id: str, registry: ProjectRegistry = Depends(get_project_registry)
) -> ProjectConfig:
    try:
        return registry.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"unknown project_id '{project_id}'") from exc


__all__ = ["get_db_session", "get_project_registry", "get_project_config", "get_settings"]
