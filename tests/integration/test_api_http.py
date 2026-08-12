"""FastAPI HTTP katmanının uçtan uca doğrulaması (gerçek istek/yanıt döngüsü)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from awe.api.main import app
from awe.persistence import Base, create_database_engine

_BASE = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
_STEPS = [
    ("open_settings", "route"),
    ("open_security", "route"),
    ("select_change_password", "select"),
    ("confirm_password_reset", "confirm"),
]


def _event(day: int, index: int, action: str, effect: str) -> dict:
    ts = (_BASE + timedelta(days=day, minutes=index)).isoformat()
    return {
        "eventId": f"evt-{day}-{index}",
        "projectId": "shopwave",
        "subjectId": "user_1",
        "sessionId": f"sess-{day}",
        "timestamp": ts,
        "source": "client",
        "actionKey": action,
        "role": "action",
        "effect": effect,
        "trigger": "button",
        "screen": "settings",
        "widget": "password_row",
        "target": None,
        "status": "success",
        "breaksEpisode": False,
        "metadata": {},
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "api_test.db"
    monkeypatch.setenv("AWE_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("AWE_PROJECT_CONFIG_DIR", "config_examples")

    engine = create_database_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    from awe.api import dependencies

    dependencies._session_factory_for.cache_clear()

    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_reports_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_full_http_round_trip_ingest_analyze_list_dismiss(client: TestClient):
    for day in range(6):
        for index, (action, effect) in enumerate(_STEPS):
            response = client.post("/projects/shopwave/events", json=_event(day, index, action, effect))
            assert response.status_code == 200
            assert response.json()["accepted"] is True

    duplicate = client.post("/projects/shopwave/events", json=_event(0, 0, *_STEPS[0]))
    assert duplicate.json()["duplicate"] is True

    analyze = client.post("/projects/shopwave/subjects/user_1/analyze")
    assert analyze.status_code == 200
    assert analyze.json()["families"][0]["habit_decision"] == "pass"

    suggestions = client.get("/projects/shopwave/subjects/user_1/suggestions")
    assert suggestions.status_code == 200
    body = suggestions.json()
    assert len(body) == 1
    assert body[0]["primary_plan"]["plan_type"] == "prefill"

    suggestion_key = body[0]["suggestion_key"]
    dismissed = client.post(f"/projects/shopwave/subjects/user_1/suggestions/{suggestion_key}/dismiss")
    assert dismissed.status_code == 200
    assert dismissed.json()["state"] == "dismissed"

    after_dismiss = client.get("/projects/shopwave/subjects/user_1/suggestions")
    assert after_dismiss.json() == []


def test_unknown_project_returns_404(client: TestClient):
    response = client.post("/projects/unknown/events", json={})
    assert response.status_code == 404


def test_malformed_event_is_rejected_not_crashed(client: TestClient):
    response = client.post("/projects/shopwave/events", json={"missing": "required fields"})
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["error"] is not None
