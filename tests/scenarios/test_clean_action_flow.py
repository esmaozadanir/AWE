"""Ham event → canonical Observation → ACTION/CONTEXT/IGNORE → temiz action akışı zincirinin
uçtan uca doğrulaması (Adapter → Classifier → Ordering → O-Series Builder, henüz Family'ye
girmeden).

Tek bir gerçekçi session: kullanıcı kursları açar (ACTION), kurs listesini görür (CONTEXT),
listeyi kaydırır (IGNORE — passive), bir kursu açar (ACTION), arka planda bir senkronizasyon
event'i gelir (IGNORE — effect=none), dersi başlatır (ACTION). Temiz akış yalnızca üç ACTION
adımını içermelidir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.adapter import build_observation
from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.ordering import group_by_session, order_session
from awe.series import extract_series

_MAPPING = AdapterMapping(
    mapping_version="course-app-v1",
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

_BASE = datetime(2026, 8, 11, 13, 20, tzinfo=UTC)


def _event(event_id, minute, action, effect, trigger, screen, *, source="client"):
    return {
        "eventId": event_id,
        "projectId": "learnloop",
        "subjectId": "sub_42",
        "sessionId": "sess_9",
        "timestamp": (_BASE + timedelta(minutes=minute)).isoformat(),
        "actionKey": action,
        "effect": effect,
        "trigger": trigger,
        "source": source,
        "screen": screen,
        "target": None,
        "status": "success",
        "duration": None,
    }


_RAW_SESSION = [
    _event("evt1", 0, "open_courses", "route", "button", "home"),
    _event("evt2", 1, "course_list_shown", "view", "automatic", "courses"),
    _event("evt3", 2, "scroll_list", "query", "scroll", "courses"),
    _event("evt4", 3, "open_course", "route", "button", "courses"),
    _event("evt5", 4, "background_sync", "none", "automatic", None, source="system"),
    _event("evt6", 5, "start_lesson", "route", "button", "course_42"),
]


def test_seven_event_session_produces_a_three_action_clean_flow():
    observations = [build_observation(raw, _MAPPING) for raw in _RAW_SESSION]
    grouped = group_by_session(observations)
    assert set(grouped) == {"sess_9"}

    ordered, confidence = order_session(grouped["sess_9"])
    series = extract_series(ordered, confidence)

    assert len(series) == 1
    assert [step.token.action for step in series[0].steps] == ["open_courses", "open_course", "start_lesson"]
    # CONTEXT/IGNORE olaylar temiz akıştan düşer ama raw kanıt olarak korunur.
    assert len(series[0].raw_observations) == len(_RAW_SESSION)


def test_scroll_is_passive_and_never_enters_the_action_flow():
    observations = [build_observation(raw, _MAPPING) for raw in _RAW_SESSION]
    ordered, confidence = order_session(observations)
    series = extract_series(ordered, confidence)

    actions = [step.token.action for step in series[0].steps]
    assert "scroll_list" not in actions


def test_system_sourced_sync_event_is_ignored_not_treated_as_a_user_action():
    observations = [build_observation(raw, _MAPPING) for raw in _RAW_SESSION]
    ordered, confidence = order_session(observations)
    series = extract_series(ordered, confidence)

    actions = [step.token.action for step in series[0].steps]
    assert "background_sync" not in actions
