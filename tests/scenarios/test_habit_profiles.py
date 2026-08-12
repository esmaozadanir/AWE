"""Sentetik profillerin (bkz. `awe.testing.generators`) tam pipeline üzerinden ground-truth
Habit kararını üretip üretmediğini doğrular."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig, HabitConfig
from awe.config.project_config import ProjectConfig
from awe.domain.enums import HabitDecision
from awe.persistence import Base, create_database_engine, create_session_factory
from awe.services import analyze_subject, ingest_event
from awe.testing.generators import PROFILE_NAMES, generate_subject

_MAPPING = AdapterMapping(
    mapping_version="profile-v1",
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
_PROJECT = ProjectConfig(project_id="proj", display_name="Profiles", mapping=_MAPPING, engine=_ENGINE)


@pytest.mark.parametrize("profile", PROFILE_NAMES)
def test_profile_produces_the_expected_ground_truth_habit_decision(profile):
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    now = datetime(2027, 1, 1, tzinfo=UTC)

    subject = generate_subject(
        profile, "proj", f"subj-{profile}", seed=42, base_time=datetime(2026, 1, 1, tzinfo=UTC)
    )
    for raw_event in subject.events:
        outcome = ingest_event(session, _PROJECT, "proj", raw_event, now)
        assert outcome.accepted, outcome.error

    summary = analyze_subject(session, _PROJECT, "proj", subject.subject_id, now)
    session.commit()

    decisions = {v.habit_decision for v in summary.variants}
    if subject.expected_habit_decision == HabitDecision.HABIT_DETECTED:
        assert HabitDecision.HABIT_DETECTED in decisions, f"{profile}: no HABIT_DETECTED variant found"
    else:
        assert HabitDecision.HABIT_DETECTED not in decisions, f"{profile}: unexpectedly found HABIT_DETECTED"
