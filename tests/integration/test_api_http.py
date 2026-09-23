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


def _raw_event(
    event_id: str, session_id: str, day: int, action: str, effect: str, screen: str, minute: int = 0
) -> dict:
    base = datetime(2026, 1, 1, 9, tzinfo=UTC) + timedelta(days=day, minutes=minute)
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


def _view_event(event_id: str, session_id: str, day: int, minute: int, screen: str) -> dict:
    event = _raw_event(event_id, session_id, day, f"view_{screen}", "view", screen, minute=minute)
    event["trigger"] = "automatic"
    return event


def _explanation_flow_events(day: int) -> list[dict]:
    session_id = f"sess-explain-{day}"
    return [
        _raw_event(f"ee{day}-1", session_id, day, "k1_open_menu", "route", "home"),
        _view_event(f"ee{day}-2", session_id, day, 1, "menu"),
        _raw_event(f"ee{day}-3", session_id, day, "k2_open_reports", "route", "menu", minute=2),
        _view_event(f"ee{day}-4", session_id, day, 3, "reports"),
        _raw_event(f"ee{day}-5", session_id, day, "k3_open_daily_report", "open", "reports", minute=4),
        _view_event(f"ee{day}-6", session_id, day, 5, "daily_report"),
    ]


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


_SHOPWAVE = {"project_id": "shopwave", "subject_id": "sub_1"}


def test_unknown_project_returns_404(client):
    response = client.post("/events", params={"project_id": "does-not-exist"}, json={})
    assert response.status_code == 404


def test_missing_project_id_returns_422_not_a_crash(client):
    """project_id/subject_id query parametresi -- eksikse FastAPI handler'ı hiç çalıştırmadan
    alan-bazlı, okunabilir bir 422 döner (bkz. docs/engine-decisions.md ilgili karar notu)."""
    response = client.post("/analyze")
    assert response.status_code == 422
    locations = [tuple(err["loc"]) for err in response.json()["detail"]]
    assert ("query", "project_id") in locations
    assert ("query", "subject_id") in locations


def test_event_ingest_analyze_and_suggestion_flow(client):
    for day in range(3):
        response = client.post(
            "/events",
            params={"project_id": "shopwave"},
            json=_raw_event(f"evt-{day}", f"sess-{day}", day, "open_cart", "route", "cart"),
        )
        assert response.status_code == 200
        assert response.json()["accepted"] is True

    analyze_response = client.post("/analyze", params=_SHOPWAVE)
    assert analyze_response.status_code == 200
    body = analyze_response.json()
    assert body["series_count"] == 3
    assert "variants" in body

    suggestions_response = client.get("/suggestions", params=_SHOPWAVE)
    assert suggestions_response.status_code == 200
    assert isinstance(suggestions_response.json(), list)


def test_pull_endpoint_reports_pull_disabled_for_projects_without_it_configured(client):
    """shopwave (ve şu an tüm örnek projeler) `pull.enabled=False` ile geliyor -- endpoint bu
    durumda 5xx değil 200 + `success=False` döner (bkz. awe.services.ingest_sync.
    pull_and_analyze). PULL ve PUSH bağımsız endpoint'ler -- ayrı ayrı test edilir."""
    response = client.post("/pull", params=_SHOPWAVE)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "pull.enabled" in body["error"]


def test_push_endpoint_reports_delivery_disabled_for_projects_without_it_configured(client):
    """shopwave (ve şu an tüm örnek projeler) `delivery.enabled=False` ile geliyor -- bkz.
    awe.services.suggestions.push_pending."""
    response = client.post("/push", params=_SHOPWAVE)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "delivery.enabled" in body["error"]


def test_batch_ingest_reports_accepted_and_duplicate_counts(client):
    events = [_raw_event("evt-batch-1", "sess-batch", 0, "open_cart", "route", "cart")]
    first = client.post("/events/batch", params={"project_id": "shopwave"}, json=events)
    assert first.status_code == 200
    assert first.json()["accepted_count"] == 1

    second = client.post("/events/batch", params={"project_id": "shopwave"}, json=events)
    assert second.json()["duplicate_count"] == 1


def test_dismiss_unknown_suggestion_returns_404(client):
    response = client.post("/dismiss", params={**_SHOPWAVE, "suggestion_key": "does-not-exist"})
    assert response.status_code == 404


def test_suggestion_explanation_returns_step_sequence_and_stats(client):
    for day in range(3):
        for raw_event in _explanation_flow_events(day):
            response = client.post("/events", params={"project_id": "shopwave"}, json=raw_event)
            assert response.status_code == 200
            assert response.json()["accepted"] is True

    analyze_response = client.post("/analyze", params=_SHOPWAVE)
    assert analyze_response.status_code == 200

    suggestions_response = client.get("/suggestions", params=_SHOPWAVE)
    suggestions = suggestions_response.json()
    assert len(suggestions) == 1
    suggestion_key = suggestions[0]["suggestion_key"]

    explanation_response = client.get("/explanation", params={**_SHOPWAVE, "suggestion_key": suggestion_key})
    assert explanation_response.status_code == 200
    body = explanation_response.json()
    assert body["suggestion_key"] == suggestion_key
    assert body["steps"] == ["k1_open_menu", "k2_open_reports", "k3_open_daily_report"]
    assert body["anchor"] == body["steps"][-1]
    assert body["repeat_count"] == 3
    assert body["saved_steps"] >= 1
    assert body["target"] is None


def test_suggestion_explanation_unknown_key_returns_404(client):
    response = client.get("/explanation", params={**_SHOPWAVE, "suggestion_key": "does-not-exist"})
    assert response.status_code == 404
