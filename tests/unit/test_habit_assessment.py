"""Habit Evaluator (bölüm 6.7): MVP kapısı `distinct session >= 3 AND distinct day >= 2`,
artı kullanıcı talebiyle eklenen deterministik regularity/support katmanı (bkz.
docs/engine-decisions.md #7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.config.engine_config import HabitConfig
from awe.domain.enums import EpisodeCandidateKind, HabitCadence, HabitDecision, ObservationTrigger, ReasonCode
from awe.domain.episode import EpisodeCandidate
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.habit import evaluate_habit
from tests.support.builders import make_series

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_CONFIG = HabitConfig(min_distinct_sessions=3, min_distinct_days=2)


def _occurrence(day: int, session_index: int, *, shortcut: bool = False) -> tuple[EpisodeCandidate, OSeries]:
    series = make_series(
        f"sess-{day}-{session_index}",
        _NOW + timedelta(days=day, minutes=session_index),
        ["open_cart", "checkout"],
        series_suffix=f"{day}-{session_index}",
        has_shortcut_trigger=shortcut,
    )
    candidate = EpisodeCandidate(
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
    return candidate, series


def _split(pairs: list[tuple[EpisodeCandidate, OSeries]]) -> tuple[list[EpisodeCandidate], list[OSeries]]:
    return [c for c, _s in pairs], [s for _c, s in pairs]


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
    candidates, all_series = _split(
        [
            _occurrence(day=0, session_index=0),
            _occurrence(day=0, session_index=1),
            _occurrence(day=1, session_index=0),
        ]
    )
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.HABIT_DETECTED
    assert assessment.evidence is not None
    assert assessment.evidence.distinct_sessions == 3
    assert assessment.evidence.distinct_days == 2
    assert assessment.evidence.support_ratio == 1.0


def test_single_day_burst_with_many_sessions_fails_the_day_dimension():
    candidates, all_series = _split([_occurrence(day=0, session_index=i) for i in range(10)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.INSUFFICIENT_EVIDENCE
    assert ReasonCode.INSUFFICIENT_DISTINCT_DAYS in assessment.reason_codes


def test_two_sessions_two_days_fails_the_session_dimension():
    candidates, all_series = _split([_occurrence(day=0, session_index=0), _occurrence(day=1, session_index=0)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.INSUFFICIENT_EVIDENCE
    assert ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS in assessment.reason_codes


def test_shortcut_triggered_occurrences_are_excluded_from_organic_evidence():
    """Kısayol kullanımı organik kanıt sayılmaz — yalnızca kısayol tetikli occurrence'lar
    kapıyı karşılamaya yetmemelidir."""
    candidates, all_series = _split([_occurrence(day=d, session_index=0, shortcut=True) for d in range(5)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.INSUFFICIENT_EVIDENCE
    assert ReasonCode.INSUFFICIENT_OCCURRENCES in assessment.reason_codes


def test_fail_status_occurrences_are_not_excluded_from_the_count():
    """Bölüm 3 kural 4: fail/cancel olan ACTION'lar diziden atılmaz."""
    from awe.domain.enums import ObservationStatus
    from tests.support.builders import StepSpec, make_series_from_steps

    candidates = []
    all_series = []
    for day in range(3):
        series = make_series_from_steps(
            f"sess{day}",
            _NOW + timedelta(days=day),
            [StepSpec(action="open_cart"), StepSpec(action="checkout", status=ObservationStatus.FAIL)],
            series_suffix=str(day),
        )
        all_series.append(series)
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

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.decision == HabitDecision.HABIT_DETECTED
    assert assessment.evidence is not None
    assert assessment.evidence.status_vector.fail == 3
    assert assessment.evidence.support_ratio == 1.0


def test_two_distinct_days_gap_regularity_is_treated_as_maximal():
    """Yalnızca iki distinct gün (tek bir gap) varken popülasyon stdev'i matematiksel olarak
    0'dır (n=1 için "tanımsız" değil) -- gap_regularity=1.0 ve DAILY doğal sonuçtur. Kanıt
    ince olsa da (distinct_days tam kapı eşiğinde), bu bir gate DEĞİLDİR."""
    candidates, all_series = _split(
        [
            _occurrence(day=0, session_index=0),
            _occurrence(day=0, session_index=1),
            _occurrence(day=1, session_index=0),
        ]
    )
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.mean_gap_days == 1.0
    assert assessment.evidence.gap_regularity == 1.0
    assert assessment.evidence.cadence == HabitCadence.DAILY


def test_constant_one_day_gaps_classify_as_daily_cadence():
    candidates, all_series = _split([_occurrence(day=d, session_index=0) for d in range(3)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.cadence == HabitCadence.DAILY


def test_constant_seven_day_gaps_classify_as_weekly_cadence():
    candidates, all_series = _split([_occurrence(day=d, session_index=0) for d in (0, 7, 14)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.mean_gap_days == 7.0
    assert assessment.evidence.cadence == HabitCadence.WEEKLY


def test_constant_fourteen_day_gaps_classify_as_biweekly_cadence():
    candidates, all_series = _split([_occurrence(day=d, session_index=0) for d in (0, 14, 28)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.mean_gap_days == 14.0
    assert assessment.evidence.cadence == HabitCadence.BIWEEKLY


def test_constant_thirty_day_gaps_classify_as_monthly_cadence():
    candidates, all_series = _split([_occurrence(day=d, session_index=0) for d in (0, 30, 60)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.mean_gap_days == 30.0
    assert assessment.evidence.cadence == HabitCadence.MONTHLY


def test_inconsistent_gaps_classify_as_irregular_even_when_mean_gap_is_weekly_range():
    """Aynı gün kümesi `awe.testing.generators._day_list`'in `irregular_recurring` profiliyle
    aynıdır (buradan import EDİLMEZ, elle kurulur): ortalama boşluk 9.0 gün -- düzenli olsaydı
    WEEKLY aralığına düşerdi -- ama CV≈0.41 (>0.3 eşiği) örüntüyü diskalifiye eder. Düzenlilik
    kontrolünün gerçekten işe yaradığını kanıtlayan asıl test budur."""
    days = (1, 4, 11, 18, 29, 43, 55)
    candidates, all_series = _split([_occurrence(day=d, session_index=0) for d in days])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.mean_gap_days == 9.0
    assert assessment.evidence.cadence == HabitCadence.IRREGULAR


def test_support_ratio_reflects_unrelated_activity_within_the_window():
    """Pattern yalnızca day0/day3'te görülüyor ama subject bu pencerede (day1/day2) bu pattern
    DIŞINDA da aktifti -- support_ratio bu farkı yansıtmalı."""
    candidates, all_series = _split(
        [
            _occurrence(day=0, session_index=0),
            _occurrence(day=0, session_index=1),
            _occurrence(day=3, session_index=0),
        ]
    )
    all_series.append(make_series("sess-unrelated-1", _NOW + timedelta(days=1), ["browse"]))
    all_series.append(make_series("sess-unrelated-2", _NOW + timedelta(days=2), ["browse"]))
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.distinct_days == 2
    assert assessment.evidence.active_days_total == 4
    assert assessment.evidence.support_ratio == 0.5


def test_active_days_total_excludes_activity_outside_the_pattern_window():
    candidates, all_series = _split(
        [
            _occurrence(day=5, session_index=0),
            _occurrence(day=5, session_index=1),
            _occurrence(day=6, session_index=0),
        ]
    )
    all_series.append(make_series("sess-before", _NOW, ["browse"]))
    all_series.append(make_series("sess-after", _NOW + timedelta(days=20), ["browse"]))
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", _CONFIG)

    assert assessment.evidence.active_days_total == 2
    assert assessment.evidence.support_ratio == 1.0


def test_single_distinct_day_produces_zero_gap_statistics_without_crashing():
    """`min_distinct_days` proje bazında 1'e düşürülürse (varsayılan >= 2 zaten en az bir gap
    garanti eder), sıfır gap ile crash ETMEMELİ -- IRREGULAR + 0.0/0.0 döner."""
    lenient_config = HabitConfig(min_distinct_sessions=1, min_distinct_days=1)
    candidates, all_series = _split([_occurrence(day=0, session_index=0)])
    candidates_by_id = {c.candidate_id: c for c in candidates}
    variant = _variant([c.candidate_id for c in candidates])

    assessment = evaluate_habit(variant, candidates_by_id, all_series, "UTC", lenient_config)

    assert assessment.decision == HabitDecision.HABIT_DETECTED
    assert assessment.evidence.mean_gap_days == 0.0
    assert assessment.evidence.gap_regularity == 0.0
    assert assessment.evidence.cadence == HabitCadence.IRREGULAR
