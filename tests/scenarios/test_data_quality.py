"""Adapter'ın veri kalitesi kanıtı: target null/missing/present ayrımı, geçersiz duration,
bilinmeyen canonical değerler (bölüm 6.1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from awe.adapter import AdapterValidationError, build_observation
from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule

_MAPPING = AdapterMapping(
    mapping_version="dq-v1",
    event_id_path="eventId",
    project_id_path="projectId",
    subject_id_path="subjectId",
    session_id_path="sessionId",
    timestamp_path="timestamp",
    action_key_path="actionKey",
    screen_path="screen",
    duration_path="duration",
    source=FieldRule(path="source", default="unknown"),
    effect=FieldRule(path="effect", default="unknown"),
    trigger=FieldRule(path="trigger", default="unknown"),
    status=FieldRule(path="status", default="unknown"),
    target=TargetRule(ref_path="target"),
)

_TS = datetime(2026, 1, 1, tzinfo=UTC).isoformat()


def _base_event(**overrides) -> dict:
    event = {
        "eventId": "evt1",
        "projectId": "proj",
        "subjectId": "subj",
        "sessionId": "sess",
        "timestamp": _TS,
        "actionKey": "open_item",
        "effect": "route",
        "trigger": "button",
        "source": "client",
        "screen": "home",
        "target": "item_1",
        "status": "success",
        "duration": None,
    }
    event.update(overrides)
    return event


def test_target_present_with_ref_is_captured():
    observation = build_observation(_base_event(target="item_1"), _MAPPING)
    assert observation.target == "item_1"
    assert observation.quality.missing_target_field is False


def test_target_explicit_null_means_no_target():
    observation = build_observation(_base_event(target=None), _MAPPING)
    assert observation.target is None
    assert observation.quality.missing_target_field is False


def test_target_key_entirely_absent_means_unknown():
    event = _base_event()
    del event["target"]
    observation = build_observation(event, _MAPPING)
    assert observation.target is None
    assert observation.quality.missing_target_field is True


def test_negative_duration_is_nulled_and_flagged():
    observation = build_observation(_base_event(duration=-50), _MAPPING)
    assert observation.duration_ms is None
    assert observation.quality.invalid_duration is True


def test_non_numeric_duration_is_nulled_and_flagged():
    observation = build_observation(_base_event(duration="not-a-number"), _MAPPING)
    assert observation.duration_ms is None
    assert observation.quality.invalid_duration is True


def test_valid_duration_is_captured_without_a_flag():
    observation = build_observation(_base_event(duration=250), _MAPPING)
    assert observation.duration_ms == 250
    assert observation.quality.invalid_duration is False


def test_unknown_effect_value_falls_back_to_unknown_with_a_warning():
    observation = build_observation(_base_event(effect="teleport"), _MAPPING)
    assert observation.effect.value == "unknown"
    assert any("effect" in warning for warning in observation.quality.warnings)


def test_missing_required_field_is_rejected():
    event = _base_event()
    del event["actionKey"]
    with pytest.raises(AdapterValidationError):
        build_observation(event, _MAPPING)


def test_naive_timestamp_is_rejected():
    event = _base_event(timestamp="2026-01-01T09:00:00")
    with pytest.raises(AdapterValidationError):
        build_observation(event, _MAPPING)
