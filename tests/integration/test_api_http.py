"""FastAPI HTTP yüzeyinin uçtan uca doğrulaması: event ingest -> analyze -> suggestions ->
dismiss, gerçek `config_examples/shopwave.yaml` mapping'i üzerinden."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from awe.api.main import app
from awe.config import ProjectRegistry, Settings
from awe.persistence import Base, create_database_engine

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config_examples"


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / f"{uuid.uuid4().hex}.db"
    database_url = f"sqlite:///{db_path}"
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)

    # `app.state` burada değil, TestClient girişinden (lifespan çalıştıktan) SONRA set edilir —
    # aksi halde `_lifespan`in kendi `get_settings()` çağrısı bu override'ı ezer.
    with TestClient(app) as test_client:
        app.state.settings = Settings(database_url=database_url, project_config_dir=str(_CONFIG_DIR))
        app.state.project_registry = ProjectRegistry(_CONFIG_DIR)
        yield test_client


def _raw_event(event_id: str, session_id: str, day: int, action: str, effect: str, screen: str) -> dict:
    base = datetime(2026, 1, 1, 9, tzinfo=UTC) + timedelta(days=day)
    return {
        "eventId": event_id,
        "projectId": "shopwave",
        "subjectId": "sub_1",
        "sessionId": session_id,
        "timestamp": base.isoformat(),
        "actionKey": action,
        "effect": effect,
        "trigger": "button",
        "source": "client",
        "screen": screen,
        "target": {"ref": None},
        "status": "success",
    }


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_project_returns_404(client):
    response = client.post("/projects/does-not-exist/events", json={})
    assert response.status_code == 404


def test_event_ingest_analyze_and_suggestion_flow(client):
    for day in range(3):
        response = client.post(
            "/projects/shopwave/events",
            json=_raw_event(f"evt-{day}", f"sess-{day}", day, "open_cart", "route", "cart"),
        )
        assert response.status_code == 200
        assert response.json()["accepted"] is True

    analyze_response = client.post("/projects/shopwave/subjects/sub_1/analyze")
    assert analyze_response.status_code == 200
    body = analyze_response.json()
    assert body["series_count"] == 3
    assert "variants" in body

    suggestions_response = client.get("/projects/shopwave/subjects/sub_1/suggestions")
    assert suggestions_response.status_code == 200
    assert isinstance(suggestions_response.json(), list)


def test_batch_ingest_reports_accepted_and_duplicate_counts(client):
    events = [_raw_event("evt-batch-1", "sess-batch", 0, "open_cart", "route", "cart")]
    first = client.post("/projects/shopwave/events/batch", json=events)
    assert first.status_code == 200
    assert first.json()["accepted_count"] == 1

    second = client.post("/projects/shopwave/events/batch", json=events)
    assert second.json()["duplicate_count"] == 1


def test_dismiss_unknown_suggestion_returns_404(client):
    response = client.post("/projects/shopwave/subjects/sub_1/suggestions/does-not-exist/dismiss")
    assert response.status_code == 404
