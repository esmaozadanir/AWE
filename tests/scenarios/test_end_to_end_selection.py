"""Uçtan uca senaryo: bölüm 7'nin worked example'ı.

K1(route: home->menu) -> K2(route: menu->reports) -> K3(open: reports->daily_report). Üç
farklı günde/session'da tekrar eden bu akış, tamamı route/open olduğu için WEAK bir Anchor'a
(K3'ün stabil post-view kanıtıyla RESOLVED), ALLOW Risk'e ve CLEAR Benefit'e (observed=3,
planned=1, saved=2) ulaşmalı; Weak-anchor istisnası koşullarını karşıladığı için Selector
SELECTED döndürmelidir — bu, ingestion'dan Selector'a kadar tüm zincirin gerçek servis
katmanından (adapter/registry mock'lanmadan) doğrulandığı tek testtir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig, HabitConfig
from awe.config.project_config import ProjectConfig
from awe.domain.enums import SuggestionState
from awe.persistence import Base, create_database_engine, create_session_factory
from awe.persistence.repository import fetch_all_observations
from awe.services import analyze_subject, explain_suggestion, ingest_event, list_subject_suggestions

_MAPPING = AdapterMapping(
    mapping_version="scenario-v1",
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
_PROJECT = ProjectConfig(project_id="proj", display_name="Scenario", mapping=_MAPPING, engine=_ENGINE)
_BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _raw_event(
    event_id: str, session_id: str, day: int, minute: int, action: str, effect: str, screen: str
) -> dict:
    return {
        "eventId": event_id,
        "projectId": "proj",
        "subjectId": "subj",
        "sessionId": session_id,
        "timestamp": (_BASE + timedelta(days=day, minutes=minute)).isoformat(),
        "actionKey": action,
        "effect": effect,
        "trigger": "button",
        "source": "client",
        "screen": screen,
        "target": None,
        "status": "success",
        "duration": None,
    }


def _view_event(event_id: str, session_id: str, day: int, minute: int, screen: str) -> dict:
    event = _raw_event(event_id, session_id, day, minute, f"view_{screen}", "view", screen)
    event["trigger"] = "automatic"
    return event


def _session_events(day: int) -> list[dict]:
    session_id = f"sess-{day}"
    return [
        _raw_event(f"e{day}-1", session_id, day, 0, "k1_open_menu", "route", "home"),
        _view_event(f"e{day}-2", session_id, day, 1, "menu"),
        _raw_event(f"e{day}-3", session_id, day, 2, "k2_open_reports", "route", "menu"),
        _view_event(f"e{day}-4", session_id, day, 3, "reports"),
        _raw_event(f"e{day}-5", session_id, day, 4, "k3_open_daily_report", "open", "reports"),
        _view_event(f"e{day}-6", session_id, day, 5, "daily_report"),
    ]


def test_repeated_route_open_flow_produces_a_selected_weak_navigate_suggestion():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    now = datetime(2026, 2, 1, tzinfo=UTC)

    for day in range(3):
        for raw_event in _session_events(day):
            outcome = ingest_event(session, _PROJECT, "proj", raw_event, now)
            assert outcome.accepted, outcome.error

    observations = fetch_all_observations(session, "proj", "subj")
    assert len(observations) == 18

    summary = analyze_subject(session, _PROJECT, "proj", "subj", now)
    session.commit()

    assert summary.series_count == 3
    assert any(v.suggestion_state == SuggestionState.ACTIVE for v in summary.variants)

    suggestions = list_subject_suggestions(session, "proj", "subj")
    assert len(suggestions) == 1

    intent = suggestions[0].intent
    assert intent.mode == "navigate"
    assert intent.destination_screen == "daily_report"
    assert intent.target is None
    assert intent.requires_user_confirmation is False
    assert intent.risk_decision == "allow"
    assert intent.benefit_saved_actions == 2
    assert intent.benefit_level == "clear"

    explanation = explain_suggestion(session, "proj", "subj", suggestions[0].suggestion_key)
    assert explanation is not None
    assert explanation.steps == ["k1_open_menu", "k2_open_reports", "k3_open_daily_report"]
    assert explanation.anchor == "k3_open_daily_report"
    assert explanation.repeat_count == 3
    assert explanation.saved_steps == 2
    assert explanation.target is None


def test_two_unrelated_sessions_never_merge_into_one_flow():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    now = datetime(2026, 2, 1, tzinfo=UTC)

    for raw_event in _session_events(day=0):
        ingest_event(session, _PROJECT, "proj", raw_event, now)

    other_session_event = _raw_event("e-other-1", "sess-other", 1, 0, "unrelated_action", "route", "elsewhere")
    ingest_event(session, _PROJECT, "proj", other_session_event, now)

    summary = analyze_subject(session, _PROJECT, "proj", "subj", now)
    session.commit()

    assert summary.series_count == 2
