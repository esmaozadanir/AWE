"""HabitEvidence <-> dict round-trip (bkz. awe.persistence.serialization)."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.domain.enums import HabitCadence
from awe.domain.habit import HabitEvidence, StatusVector
from awe.persistence.serialization import dict_to_habit_evidence, habit_evidence_to_dict


def test_habit_evidence_round_trips_through_dict():
    evidence = HabitEvidence(
        organic_occurrences=5,
        distinct_sessions=4,
        distinct_days=3,
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 10, tzinfo=UTC),
        status_vector=StatusVector(success=3, fail=1, cancel=0, unknown=1),
        active_days_total=6,
        support_ratio=0.5,
        mean_gap_days=4.5,
        gap_regularity=0.82,
        cadence=HabitCadence.WEEKLY,
    )

    assert dict_to_habit_evidence(habit_evidence_to_dict(evidence)) == evidence
