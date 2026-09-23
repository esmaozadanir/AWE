"""awe.services.ingest_sync.pull_and_analyze -- PULL->TRANSFORM->INGEST->ANALYZE akışı (bkz.
modül docstring'i). PUSH bilerek burada YOK -- bağımsız bir yetenek, bkz.
tests/unit/test_suggestion_delivery.py.

Gerçek bir dış sunucu olmadığı için `httpx.MockTransport` kullanılır (bkz. tests/unit/
test_pull_client.py) -- kendi kodumuz mock'lanmaz, yalnızca ağ katmanı sahte."""

from __future__ import annotations

import sys
import types
from datetime import UTC, datetime

import httpx

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig, HabitConfig
from awe.config.project_config import ProjectConfig, PullConfig
from awe.persistence import Base, create_database_engine, create_session_factory
from awe.services import pull_and_analyze

_MAPPING = AdapterMapping(
    mapping_version="sync-test-v1",
    event_id_path="eventId",
    project_id_path="projectId",
    subject_id_path="subjectId",
    session_id_path="sessionId",
    timestamp_path="timestamp",
    action_key_path="actionKey",
    screen_path="screen",
    source=FieldRule(path="source", default="unknown"),
    effect=FieldRule(path="effect", default="unknown"),
    trigger=FieldRule(path="trigger", default="unknown"),
    status=FieldRule(path="status", default="unknown"),
    target=TargetRule(ref_path="target"),
)
_ENGINE = EngineConfig(habit=HabitConfig(min_distinct_sessions=3, min_distinct_days=2))
_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _session():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)()


def _register_fake_transform(monkeypatch, project_id: str, transform) -> None:
    module = types.ModuleType(f"awe.transforms.{project_id}")
    module.transform = transform
    monkeypatch.setitem(sys.modules, f"awe.transforms.{project_id}", module)


def test_pull_and_analyze_fails_fast_when_pull_disabled():
    project_config = ProjectConfig(
        project_id="proj", display_name="Test", mapping=_MAPPING, engine=_ENGINE, pull=PullConfig(enabled=False)
    )
    result = pull_and_analyze(_session(), project_config, "proj", "subj", _NOW)

    assert result.success is False
    assert "pull.enabled" in result.error


def test_pull_and_analyze_fails_when_no_transform_registered(monkeypatch):
    monkeypatch.delitem(sys.modules, "awe.transforms.no_such_project_xyz", raising=False)
    project_config = ProjectConfig(
        project_id="no_such_project_xyz",
        display_name="Test",
        mapping=_MAPPING,
        engine=_ENGINE,
        pull=PullConfig(enabled=True, pull_url="https://fake.example.com/export", auth_type="none"),
    )
    result = pull_and_analyze(_session(), project_config, "no_such_project_xyz", "subj", _NOW)

    assert result.success is False
    assert "no_such_project_xyz" in result.error


def test_pull_and_analyze_pulls_transforms_ingests_and_analyzes(monkeypatch):
    """Sahte sunucu, kendi keyfi şeklinde (`hits`) tek bir event döner; kayıtlı TRANSFORM
    fonksiyonu bunu AWE'nin beklediği canonical event şekline çevirir."""

    def fake_pull_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/export"
        return httpx.Response(
            200,
            json={
                "hits": [{"who": "subj", "did": "open_cart", "sess": "sess-0", "at": "2026-01-01T09:00:00+00:00"}]
            },
        )

    def fake_transform(raw_data: object) -> list[dict]:
        assert isinstance(raw_data, dict)
        return [
            {
                "eventId": "evt-1",
                "projectId": "proj",
                "subjectId": hit["who"],
                "sessionId": hit["sess"],
                "timestamp": hit["at"],
                "actionKey": hit["did"],
                "effect": "route",
                "trigger": "button",
                "source": "client",
                "screen": "cart",
                "status": "success",
            }
            for hit in raw_data["hits"]
        ]

    _register_fake_transform(monkeypatch, "proj", fake_transform)

    project_config = ProjectConfig(
        project_id="proj",
        display_name="Test",
        mapping=_MAPPING,
        engine=_ENGINE,
        pull=PullConfig(enabled=True, pull_url="https://fake.example.com/export", auth_type="none"),
    )
    client = httpx.Client(transport=httpx.MockTransport(fake_pull_handler))

    result = pull_and_analyze(_session(), project_config, "proj", "subj", _NOW, client=client)

    assert result.success is True
    assert result.ingested_count == 1
    assert result.rejected_count == 0
    assert result.series_count == 1


def test_pull_and_analyze_reports_pull_failure_without_crashing(monkeypatch):
    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    _register_fake_transform(monkeypatch, "proj", lambda raw: [])
    project_config = ProjectConfig(
        project_id="proj",
        display_name="Test",
        mapping=_MAPPING,
        engine=_ENGINE,
        pull=PullConfig(enabled=True, pull_url="https://fake.example.com/export", auth_type="none"),
    )
    client = httpx.Client(transport=httpx.MockTransport(failing_handler))

    result = pull_and_analyze(_session(), project_config, "proj", "subj", _NOW, client=client)

    assert result.success is False
    assert "PULL" in result.error
