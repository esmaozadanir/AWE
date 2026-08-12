"""Ham event → canonical Observation → ACTION/CONTEXT/IGNORE → temiz action akışı zincirinin
uçtan uca doğrulaması.

Tek bir gerçekçi session örneği: bir kullanıcı uygulamayı açar (lifecycle context), kursları
açar, kurs listesini görür (context), listeyi kaydırır (ignore), bir kursu açar, arka planda
ilerleme senkronize edilir (ignore), dersi başlatır. Beklenen temiz action akışı yalnızca
gerçek kullanıcı eylemlerinden oluşur: `open_courses → open_course → start_lesson`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.adapter import AdapterMapping, FieldRule, build_observation
from awe.config import default_engine_config
from awe.ordering import order_session
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
    trigger=FieldRule(path="trigger", default="unknown"),
    effect=FieldRule(path="effect", default="unknown"),
    status=FieldRule(path="status", default="unknown"),
)

_BASE = datetime(2026, 2, 1, 9, tzinfo=UTC)


def _raw(action_key: str, trigger: str, effect: str, index: int) -> dict:
    return {
        "eventId": f"evt{index}",
        "projectId": "course-app",
        "subjectId": "learner_1",
        "sessionId": "sess1",
        "timestamp": (_BASE + timedelta(seconds=index)).isoformat(),
        "actionKey": action_key,
        "trigger": trigger,
        "effect": effect,
        "status": "success",
        "screen": "courses",
    }


def test_course_app_session_produces_the_expected_clean_action_flow():
    raw_events = [
        _raw("app_started", "lifecycle", "view", 0),
        _raw("open_courses", "button", "route", 1),
        _raw("courses_viewed", "automatic", "view", 2),
        _raw("scroll_courses", "scroll", "view", 3),
        _raw("open_course", "button", "route", 4),
        _raw("sync_progress", "automatic", "update", 5),
        _raw("start_lesson", "button", "route", 6),
    ]

    observations = [build_observation(raw, _MAPPING) for raw in raw_events]
    ordered, confidence = order_session(observations)
    series = extract_series(ordered, confidence, default_engine_config().family)

    assert len(series) == 1
    assert [step.token.action for step in series[0].normalized_steps] == [
        "open_courses",
        "open_course",
        "start_lesson",
    ]
    # CONTEXT/IGNORE olarak sınıflanan adımlar action akışına girmez, ama audit için
    # raw_observations'ta -- session'ın tam ham event sayısıyla -- korunmaya devam eder.
    assert len(series[0].raw_observations) == len(raw_events)
