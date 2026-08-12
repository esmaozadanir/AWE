"""Uçtan uca entegrasyon testleri: ingestion → analiz → suggestion → dismiss.

Bu testler tam pipeline'ı gerçek bir SQLite veritabanına karşı çalıştırır; her katmanın kendi
birim/senaryo testleri ayrıca mevcuttur, burada amaç katmanlar arası kablolamanın (repository,
orkestrasyon, lifecycle) doğru çalıştığını doğrulamaktır.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.domain.enums import HabitDecision, SuggestionState
from awe.persistence import session_scope
from awe.risk import ResolverContract
from awe.services import analyze_subject, ingest_event, list_subject_suggestions

_BASE = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
_STEPS = [
    ("open_settings", "route"),
    ("open_security", "route"),
    ("select_change_password", "select"),
    ("confirm_password_reset", "confirm"),
]


def _event(
    day: int, index: int, action: str, effect: str, subject_id: str = "user_1", session_prefix: str = "sess"
) -> dict:
    ts = (_BASE + timedelta(days=day, minutes=index)).isoformat()
    return {
        "eventId": f"evt-{subject_id}-{day}-{index}",
        "projectId": "shopwave",
        "subjectId": subject_id,
        "sessionId": f"{session_prefix}-{day}",
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


def _ingest_daily_flow(session_factory, project_config, subject_id: str, days: range) -> None:
    with session_scope(session_factory) as session:
        for day in days:
            for index, (action, effect) in enumerate(_STEPS):
                outcome = ingest_event(
                    session, project_config, "shopwave", _event(day, index, action, effect, subject_id), _BASE
                )
                assert outcome.accepted, outcome.error


def test_duplicate_event_does_not_increase_observation_or_family_evidence(session_factory, project_registry):
    project_config = project_registry.get("shopwave")
    _ingest_daily_flow(session_factory, project_config, "user_1", range(6))

    analyze_now = _BASE + timedelta(days=6)
    with session_scope(session_factory) as session:
        analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), analyze_now)

    with session_scope(session_factory) as session:
        before = list_subject_suggestions(session, "shopwave", "user_1")
        before_benefit = before[0].primary_plan.benefit_median_saved_actions

    with session_scope(session_factory) as session:
        outcome = ingest_event(
            session, project_config, "shopwave", _event(0, 0, *_STEPS[0], "user_1"), _BASE
        )
        assert outcome.duplicate is True

    with session_scope(session_factory) as session:
        analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), analyze_now)

    with session_scope(session_factory) as session:
        after = list_subject_suggestions(session, "shopwave", "user_1")
        assert after[0].primary_plan.benefit_median_saved_actions == before_benefit


def test_reanalysis_without_new_events_is_stable(session_factory, project_registry):
    project_config = project_registry.get("shopwave")
    _ingest_daily_flow(session_factory, project_config, "user_1", range(6))
    now = _BASE + timedelta(days=6)

    with session_scope(session_factory) as session:
        first = analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), now)
    with session_scope(session_factory) as session:
        second = analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), now)

    assert second.new_series_count == 0
    assert first.families[0].family_key == second.families[0].family_key


def test_projects_never_share_family_evidence_for_the_same_subject_id(session_factory, project_registry):
    shopwave = project_registry.get("shopwave")
    taskflow = project_registry.get("taskflow")

    _ingest_daily_flow(session_factory, shopwave, "shared_subject", range(6))

    with session_scope(session_factory) as session:
        for day in range(6):
            for index, (action, effect) in enumerate(_STEPS):
                ts = (_BASE + timedelta(days=day, minutes=index)).isoformat()
                raw = {
                    "id": f"tf-evt-{day}-{index}",
                    "workspace": "taskflow",
                    "userRef": "shared_subject",
                    "visit": f"visit-{day}",
                    "ts": ts,
                    "event": "clicked",
                    "interactionKind": effect,
                    "page": "settings",
                    "element": action,
                    "entity": None,
                    "entityKind": None,
                    "outcome": "success",
                    "sessionEnd": False,
                }
                outcome = ingest_event(session, taskflow, "taskflow", raw, _BASE)
                assert outcome.accepted, outcome.error

    now = _BASE + timedelta(days=6)
    with session_scope(session_factory) as session:
        shopwave_summary = analyze_subject(
            session, shopwave, "shopwave", "shared_subject", ResolverContract.permissive(), now
        )
        taskflow_summary = analyze_subject(
            session, taskflow, "taskflow", "shared_subject", ResolverContract.permissive(), now
        )

    assert len(shopwave_summary.families) == 1
    assert len(taskflow_summary.families) == 1
    assert shopwave_summary.families[0].family_key != taskflow_summary.families[0].family_key

    with session_scope(session_factory) as session:
        shopwave_suggestions = list_subject_suggestions(session, "shopwave", "shared_subject")
        taskflow_suggestions = list_subject_suggestions(session, "taskflow", "shared_subject")
    assert len(shopwave_suggestions) == 1
    assert len(taskflow_suggestions) == 1


def test_different_subjects_in_the_same_project_do_not_share_families(session_factory, project_registry):
    project_config = project_registry.get("shopwave")
    _ingest_daily_flow(session_factory, project_config, "user_a", range(6))

    now = _BASE + timedelta(days=6)
    with session_scope(session_factory) as session:
        analyze_subject(session, project_config, "shopwave", "user_a", ResolverContract.permissive(), now)

    with session_scope(session_factory) as session:
        suggestions_b = list_subject_suggestions(session, "shopwave", "user_b")

    assert suggestions_b == []


def test_dismiss_is_respected_until_cooldown_expires_then_revives_with_continued_use(
    session_factory, project_registry
):
    project_config = project_registry.get("shopwave")
    _ingest_daily_flow(session_factory, project_config, "user_1", range(6))
    now = _BASE + timedelta(days=6)

    with session_scope(session_factory) as session:
        analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), now)

    with session_scope(session_factory) as session:
        suggestion_key = list_subject_suggestions(session, "shopwave", "user_1")[0].suggestion_key

    from awe.services import dismiss_suggestion

    with session_scope(session_factory) as session:
        dismiss_suggestion(session, "shopwave", "user_1", suggestion_key, now, project_config.engine.lifecycle)

    soon_after = now + timedelta(days=1)
    with session_scope(session_factory) as session:
        analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), soon_after)
    with session_scope(session_factory) as session:
        still_dismissed = list_subject_suggestions(session, "shopwave", "user_1")
    assert still_dismissed == []

    cooldown_days = project_config.engine.lifecycle.dismiss_cooldown_days
    revival_day = 6 + cooldown_days + 1
    _ingest_daily_flow(session_factory, project_config, "user_1", range(6, revival_day + 1))
    revival_now = _BASE + timedelta(days=revival_day)

    with session_scope(session_factory) as session:
        analyze_subject(session, project_config, "shopwave", "user_1", ResolverContract.permissive(), revival_now)
    with session_scope(session_factory) as session:
        revived = list_subject_suggestions(session, "shopwave", "user_1")

    assert len(revived) == 1
    assert revived[0].state == SuggestionState.ACTIVE.value


def test_habit_pending_before_gate_and_pass_after(session_factory, project_registry):
    project_config = project_registry.get("shopwave")
    _ingest_daily_flow(session_factory, project_config, "user_1", range(2))

    with session_scope(session_factory) as session:
        early = analyze_subject(
            session, project_config, "shopwave", "user_1", ResolverContract.permissive(), _BASE + timedelta(days=2)
        )
    assert early.families[0].habit_decision == HabitDecision.PENDING_EVIDENCE

    _ingest_daily_flow(session_factory, project_config, "user_1", range(2, 6))
    with session_scope(session_factory) as session:
        later = analyze_subject(
            session, project_config, "shopwave", "user_1", ResolverContract.permissive(), _BASE + timedelta(days=6)
        )
    assert later.families[0].habit_decision == HabitDecision.PASS
