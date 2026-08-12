"""Yeni mimariye özgü adversarial durumlar: aynı timestamp'te çoklu ACTION, çakışan event
gövdesi, yüksek tekrarlı retry'ların çökmemesi."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig
from awe.config.project_config import ProjectConfig
from awe.episodes import build_episode_candidates
from awe.families import group_into_families
from awe.ordering import order_session
from awe.persistence import Base, create_database_engine, create_session_factory
from awe.persistence.models import EventConflictRecord
from awe.series import extract_series
from awe.services import ingest_event
from tests.support.builders import make_observation

_MAPPING = AdapterMapping(
    mapping_version="adv-v1",
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
_PROJECT = ProjectConfig(project_id="proj", display_name="Adv", mapping=_MAPPING, engine=EngineConfig())
_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _event(event_id, minute, action, **overrides):
    event = {
        "eventId": event_id,
        "projectId": "proj",
        "subjectId": "subj",
        "sessionId": "sess",
        "timestamp": (_NOW + timedelta(minutes=minute)).isoformat(),
        "actionKey": action,
        "effect": "route",
        "trigger": "button",
        "source": "client",
        "screen": "home",
        "target": None,
        "status": "success",
        "duration": None,
    }
    event.update(overrides)
    return event


def test_conflicting_event_body_is_quarantined_not_silently_accepted():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()

    first = ingest_event(session, _PROJECT, "proj", _event("evt1", 0, "open_cart"), _NOW)
    assert first.accepted and not first.duplicate

    second = ingest_event(session, _PROJECT, "proj", _event("evt1", 0, "different_action"), _NOW)
    assert second.accepted is False
    assert second.duplicate is True
    assert second.conflict is True

    session.flush()
    conflicts = session.query(EventConflictRecord).all()
    assert len(conflicts) == 1
    assert conflicts[0].event_id == "evt1"


def test_identical_duplicate_event_is_silently_accepted_as_duplicate():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()

    raw = _event("evt1", 0, "open_cart")
    first = ingest_event(session, _PROJECT, "proj", raw, _NOW)
    second = ingest_event(session, _PROJECT, "proj", dict(raw), _NOW)

    assert first.accepted and not first.duplicate
    assert second.duplicate is True
    assert second.conflict is False


def test_many_simultaneous_actions_do_not_crash_ordering_or_extraction():
    observations = [
        make_observation(f"action_{i}", event_id=f"evt{i}", session_id="sess", timestamp=_NOW) for i in range(50)
    ]
    ordered, confidence = order_session(observations)
    series = extract_series(ordered, confidence)

    # 50 event aynı timestamp'i paylaşıyor -> tek büyük ambiguity grubu, hiçbiri step olmaz.
    assert sum(len(s.steps) for s in series) == 0
    assert all(s.cut_by_ambiguity for s in series[:-1])


def test_deeply_repeated_identical_steps_do_not_crash_episode_candidate_mining():
    from tests.support.builders import make_series

    long_repeat = ["ping"] * 40
    series_a = make_series("sess1", _NOW, long_repeat, series_suffix="a")
    series_b = make_series("sess2", _NOW, long_repeat, series_suffix="b")

    from awe.config.engine_config import EpisodeConfig

    candidates = build_episode_candidates([series_a, series_b], EpisodeConfig(min_symbols=2, max_symbols=8))
    families = group_into_families(candidates)
    assert len(families) >= 1


def test_empty_session_produces_no_series_and_no_crash():
    ordered, confidence = order_session([])
    assert extract_series(ordered, confidence) == []
