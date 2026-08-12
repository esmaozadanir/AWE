"""Habit Evaluator (bölüm 6.7): MVP kapısı `distinct session >= 3 AND distinct day >= 2`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.config.engine_config import HabitConfig
from awe.domain.enums import EpisodeCandidateKind, HabitDecision, ObservationTrigger, ReasonCode
from awe.domain.episode import EpisodeCandidate
from awe.domain.target import TargetVariant
from awe.habit import evaluate_habit
from tests.support.builders import make_series

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_CONFIG = HabitConfig(min_distinct_sessions=3, min_distinct_days=2)


def _candidate(day: int, session_index: int, *, shortcut: bool = False) -> EpisodeCandidate:
    series = make_series(
        f"sess-{day}-{session_index}",
        _NOW + timedelta(days=day, minutes=session_index),
        ["open_cart", "checkout"],
        series_suffix=f"{day}-{session_index}",
        has_shortcut_trigger=shortcut,
    )
    return EpisodeCandidate(
        candidate_id=series.series_id,
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=EpisodeCandidateKind.FULL_CHUNK,
        steps=series.steps,
        step_indices=tuple(range(len(series.steps))),
        observed_at=series.started_at,
        entry_trigger=ObservationTrigger.SHORTCUT if shortcut else series.entry_trigger,
        has_shortcut_trigger=shortcut,
        final_status=series.final_status,
    )


def _variant(occurrence_ids: list[str]) -> TargetVariant:
    from awe.domain.enums import TargetVariantKind

    return TargetVariant(
        variant_id="var1",
        family_id="fam1",
        kind=TargetVariantKind.NO_EXPLICIT_TARGET,
        fingerprint=(None, None),
        occurrence_ids=occurrence_ids,
    )


def test_three_sessions_two_days_meets_the_gate():
    candidates = [
        _candidate(day=0, session_index=0),
        _candidate(day=0, session_index=1),
        _candidate(day=1, session_index=0),
    ]
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.HABIT_DETECTED
    assert assessment.evidence is not None
    assert assessment.evidence.distinct_sessions == 3
    assert assessment.evidence.distinct_days == 2


def test_single_day_burst_with_many_sessions_fails_the_day_dimension():
    candidates = [_candidate(day=0, session_index=i) for i in range(10)]
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.INSUFFICIENT_EVIDENCE
    assert ReasonCode.INSUFFICIENT_DISTINCT_DAYS in assessment.reason_codes


def test_two_sessions_two_days_fails_the_session_dimension():
    candidates = [_candidate(day=0, session_index=0), _candidate(day=1, session_index=0)]
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.INSUFFICIENT_EVIDENCE
    assert ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS in assessment.reason_codes


def test_shortcut_triggered_occurrences_are_excluded_from_organic_evidence():
    """Kısayol kullanımı organik kanıt sayılmaz — yalnızca kısayol tetikli occurrence'lar
    kapıyı karşılamaya yetmemelidir."""
    candidates = [_candidate(day=d, session_index=0, shortcut=True) for d in range(5)]
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.INSUFFICIENT_EVIDENCE
    assert ReasonCode.INSUFFICIENT_OCCURRENCES in assessment.reason_codes


def test_fail_status_occurrences_are_not_excluded_from_the_count():
    """Bölüm 3 kural 4: fail/cancel olan ACTION'lar diziden atılmaz."""
    from awe.domain.enums import ObservationStatus
    from tests.support.builders import StepSpec, make_series_from_steps

    candidates = []
    for day in range(3):
        series = make_series_from_steps(
            f"sess{day}",
            _NOW + timedelta(days=day),
            [StepSpec(action="open_cart"), StepSpec(action="checkout", status=ObservationStatus.FAIL)],
            series_suffix=str(day),
        )
        candidates.append(
            EpisodeCandidate(
                candidate_id=series.series_id,
                project_id=series.project_id,
                subject_id=series.subject_id,
                session_id=series.session_id,
                series_id=series.series_id,
                kind=EpisodeCandidateKind.FULL_CHUNK,
                steps=series.steps,
                step_indices=tuple(range(len(series.steps))),
                observed_at=series.started_at,
                entry_trigger=series.entry_trigger,
                has_shortcut_trigger=False,
                final_status=series.final_status,
            )
        )
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.HABIT_DETECTED
    assert assessment.evidence is not None
    assert assessment.evidence.status_vector.fail == 3
