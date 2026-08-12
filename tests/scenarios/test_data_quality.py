"""Bölüm 122'deki veri kalitesi stres testleri."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from awe.adapter import AdapterMapping, AdapterValidationError, FieldRule, TargetRule, build_observation
from awe.domain.enums import ObservationEffect, ObservationRole, ObservationStatus
from awe.persistence import session_scope
from awe.services import ingest_batch, ingest_event

_MAPPING = AdapterMapping(
    mapping_version="dq-test-v1",
    event_id_path="eventId",
    project_id_path="projectId",
    subject_id_path="subjectId",
    session_id_path="sessionId",
    timestamp_path="timestamp",
    action_key_path="actionKey",
    screen_path="screen",
    widget_path="widget",
    trigger=FieldRule(path="trigger", default="unknown"),
    effect=FieldRule(path="effect", default="unknown"),
    role=FieldRule(path="role", default="action"),
    status=FieldRule(path="status", default="unknown"),
    target=TargetRule(ref_path="target.ref"),
)

_MAPPING_NO_TARGET = AdapterMapping(
    mapping_version="dq-test-v1",
    event_id_path="eventId",
    project_id_path="projectId",
    subject_id_path="subjectId",
    session_id_path="sessionId",
    timestamp_path="timestamp",
    action_key_path="actionKey",
)


def _raw(**overrides) -> dict:
    base = {
        "eventId": "evt1",
        "projectId": "proj",
        "subjectId": "subj",
        "sessionId": "sess1",
        "timestamp": "2026-08-05T10:35:22+03:00",
        "actionKey": "open_settings",
        "role": "action",
        "effect": "route",
        "trigger": "button",
        "status": "success",
    }
    base.update(overrides)
    return base


def test_missing_screen_and_widget_are_accepted_as_none():
    observation = build_observation(_raw(), _MAPPING)
    assert observation.screen is None
    assert observation.widget is None
    assert observation.quality.has_screen is False
    assert observation.quality.has_widget is False


def test_explicit_null_target_is_none_not_unknown():
    observation = build_observation(_raw(target=None), _MAPPING)
    assert observation.target == ""


def test_absent_target_mapping_is_unknown_not_none():
    observation = build_observation(_raw(), _MAPPING_NO_TARGET)
    assert observation.target is None


def test_target_present_with_ref_is_captured():
    observation = build_observation(_raw(target={"ref": "opaque_91"}), _MAPPING)
    assert observation.target == "opaque_91"


def test_unknown_raw_role_falls_back_to_default_with_warning():
    observation = build_observation(_raw(role="something_new"), _MAPPING)
    assert observation.role == ObservationRole.ACTION
    assert any("role" in w for w in observation.quality.mapping_warnings)


def test_unknown_raw_effect_falls_back_to_unknown_with_warning():
    observation = build_observation(_raw(effect="teleport"), _MAPPING)
    assert observation.effect == ObservationEffect.UNKNOWN
    assert any("effect" in w for w in observation.quality.mapping_warnings)


def test_unknown_raw_status_falls_back_to_unknown_with_warning():
    observation = build_observation(_raw(status="weird_state"), _MAPPING)
    assert observation.status == ObservationStatus.UNKNOWN
    assert any("status" in w for w in observation.quality.mapping_warnings)


def test_invalid_timestamp_is_rejected_not_crashed():
    with pytest.raises(AdapterValidationError):
        build_observation(_raw(timestamp="not-a-real-timestamp"), _MAPPING)


def test_missing_required_field_is_rejected_not_crashed():
    raw = _raw()
    del raw["actionKey"]
    with pytest.raises(AdapterValidationError):
        build_observation(raw, _MAPPING)


def test_naive_timestamp_is_assumed_project_timezone_and_flagged():
    observation = build_observation(_raw(timestamp="2026-08-05T10:35:22"), _MAPPING)
    assert observation.timestamp.tzinfo is not None
    assert any("naive_timestamp" in w for w in observation.quality.mapping_warnings)


def test_missing_session_id_gets_a_synthetic_per_event_session():
    first = build_observation(_raw(eventId="evt1", sessionId=""), _MAPPING)
    second = build_observation(_raw(eventId="evt2", sessionId=""), _MAPPING)
    assert first.quality.is_synthetic_session is True
    assert first.session_id != second.session_id, "korelasyonsuz eventler asla ayni oturuma birlesmemeli"


def test_mapping_version_is_recorded_per_observation():
    older_mapping = AdapterMapping(
        mapping_version="dq-test-v0",
        event_id_path="eventId",
        project_id_path="projectId",
        subject_id_path="subjectId",
        session_id_path="sessionId",
        timestamp_path="timestamp",
        action_key_path="actionKey",
    )
    old_observation = build_observation(_raw(), older_mapping)
    new_observation = build_observation(_raw(), _MAPPING)
    assert old_observation.mapping_version == "dq-test-v0"
    assert new_observation.mapping_version == "dq-test-v1"


def test_partial_batch_accepts_valid_events_and_rejects_only_invalid_ones(session_factory, project_registry):
    project_config = project_registry.get("shopwave")
    base = datetime(2026, 5, 1, tzinfo=UTC)
    valid_event = {
        "eventId": "evt-valid",
        "projectId": "shopwave",
        "subjectId": "user_1",
        "sessionId": "sess-1",
        "timestamp": base.isoformat(),
        "source": "client",
        "actionKey": "open_settings",
        "role": "action",
        "effect": "route",
        "trigger": "button",
        "status": "success",
        "breaksEpisode": False,
        "metadata": {},
    }
    invalid_event = {"projectId": "shopwave", "subjectId": "user_1"}

    with session_scope(session_factory) as session:
        outcomes = ingest_batch(session, project_config, "shopwave", [valid_event, invalid_event], base)

    assert outcomes[0].accepted is True
    assert outcomes[1].accepted is False


def test_out_of_order_ingestion_still_produces_correctly_ordered_series(session_factory, project_registry):
    project_config = project_registry.get("shopwave")
    base = datetime(2026, 5, 1, 9, tzinfo=UTC)

    def event(event_id: str, action: str, minute: int) -> dict:
        return {
            "eventId": event_id,
            "projectId": "shopwave",
            "subjectId": "user_1",
            "sessionId": "sess-1",
            "timestamp": (base + timedelta(minutes=minute)).isoformat(),
            "source": "client",
            "actionKey": action,
            "role": "action",
            "effect": "route",
            "trigger": "button",
            "status": "success",
            "breaksEpisode": False,
            "metadata": {},
        }

    # C, A, B sirasiyla ingest edilir ama gercek zaman sirasi A(0) < B(1) < C(2)'dir.
    events = [event("evt-c", "C", 2), event("evt-a", "A", 0), event("evt-b", "B", 1)]

    with session_scope(session_factory) as session:
        for raw in events:
            outcome = ingest_event(session, project_config, "shopwave", raw, base)
            assert outcome.accepted

    from awe.ordering import order_session
    from awe.persistence.repository import fetch_unprocessed_observations

    with session_scope(session_factory) as session:
        observations, _ = fetch_unprocessed_observations(session, "shopwave", "user_1")
        ordered, _confidence = order_session(observations)

    assert [o.action for o in ordered] == ["A", "B", "C"]
