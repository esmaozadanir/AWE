"""HabitEvidence <-> dict round-trip (bkz. awe.persistence.serialization)."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.domain.habit import HabitEvidence
from awe.persistence.serialization import dict_to_habit_evidence, habit_evidence_to_dict


def test_habit_evidence_round_trips_through_dict():
    evidence = HabitEvidence(
        organic_occurrences=5,
        distinct_sessions=4,
        distinct_days=3,
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 10, tzinfo=UTC),
    )

    assert dict_to_habit_evidence(habit_evidence_to_dict(evidence)) == evidence
