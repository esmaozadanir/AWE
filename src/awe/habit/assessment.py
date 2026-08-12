"""Habit Evaluator (bölüm 6.7): tek görevi recurrence ölçmektir.

MVP kapısı: `distinct session >= 3 AND distinct calendar day >= 2`. Bu HÂLÂ TEK hard gate'tir
ve değişmedi. Bunun ÜZERİNE, kullanıcı talebiyle (bkz. docs/engine-decisions.md #7)
deterministik bir regularity/support istatistik katmanı eklendi: `HabitEvidence.cadence`,
`mean_gap_days`, `gap_regularity`, `active_days_total`, `support_ratio`. Bunların HİÇBİRİ yeni
bir gate değildir ve Selector sıralamasına girmez — yalnızca HABIT_DETECTED kararı verildikten
SONRA, aynı distinct-gün-kümesi üzerinde hesaplanıp kanıt vektörüne eklenir.

Kısayol tetiklemesiyle başlayan occurrence'lar organik kanıttan hariç tutulur (belgede yazılı
değil, bkz. `ObservationTrigger.SHORTCUT` docstring'i — kasıtlı bir superset koruması: aksi
halde bir kısayolun kendi kullanımı kendi önerisini besleyen bir döngü oluşturabilir)."""

from __future__ import annotations

import statistics
from datetime import date
from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import HabitCadence, HabitDecision, ObservationStatus, ReasonCode
from awe.domain.episode import EpisodeCandidate
from awe.domain.habit import HabitAssessment, HabitEvidence, StatusVector
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant


def _gap_statistics(days: set[date]) -> tuple[float, float]:
    """Distinct günlerin sıralı ardışık farklarından `(mean_gap_days, gap_regularity)`
    üretir. Popülasyon stdev'i (`statistics.pstdev`) kullanılır çünkü elimizdeki gap listesi
    bir örneklem değil, bu pattern'in gözlenen TÜM boşluklarıdır. Tek bir gap'te (iki distinct
    gün) pstdev matematiksel olarak 0'dır (n=1 için "tanımsız" değil, `statistics.stdev`'den
    farkı budur) — bu yüzden `gap_regularity=1.0` özel bir dal GEREKTİRMEDEN doğal olarak
    çıkar (bkz. docs/engine-decisions.md #7)."""
    ordered = sorted(days)
    # strict=False kasıtlı: `ordered[1:]` bir eleman kısadır -- ardışık çift üretmenin
    # standart deyimi budur (N nokta -> N-1 boşluk).
    gaps = [(later - earlier).days for earlier, later in zip(ordered, ordered[1:], strict=False)]
    if not gaps:
        # distinct_days == 1: yalnızca `min_distinct_days` proje bazında < 2'ye düşürülürse
        # ulaşılabilir (varsayılan kapı zaten en az bir gap garanti eder). Ölçülebilir hiçbir
        # aralık yok; sıfır kanıtla "düzenli" iddia etmek yanıltıcı olurdu.
        return 0.0, 0.0
    mean_gap = statistics.fmean(gaps)
    coefficient_of_variation = statistics.pstdev(gaps) / mean_gap  # mean_gap >= 1.0: distinct tarihler
    return mean_gap, max(0.0, 1.0 - coefficient_of_variation)


def _cadence_of(mean_gap_days: float, gap_regularity: float, config: HabitConfig) -> HabitCadence:
    if gap_regularity < config.min_gap_regularity_for_named_cadence:
        return HabitCadence.IRREGULAR
    if mean_gap_days <= config.daily_cadence_max_mean_gap_days:
        return HabitCadence.DAILY
    if mean_gap_days <= config.weekly_cadence_max_mean_gap_days:
        return HabitCadence.WEEKLY
    if mean_gap_days <= config.biweekly_cadence_max_mean_gap_days:
        return HabitCadence.BIWEEKLY
    if mean_gap_days <= config.monthly_cadence_max_mean_gap_days:
        return HabitCadence.MONTHLY
    return HabitCadence.IRREGULAR  # isimlendirilemeyecek kadar seyrek (ör. çeyreklik+)


def _active_days_total(all_series: list[OSeries], tz: ZoneInfo, window_start: date, window_end: date) -> int:
    all_dates = (series.started_at.astimezone(tz).date() for series in all_series)
    return len({day for day in all_dates if window_start <= day <= window_end})


def evaluate_habit(
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
    all_series: list[OSeries],
    timezone_name: str,
    config: HabitConfig,
) -> HabitAssessment:
    members = [candidates_by_id[occurrence_id] for occurrence_id in variant.occurrence_ids]
    organic = [candidate for candidate in members if not candidate.has_shortcut_trigger]

    if not organic:
        return HabitAssessment(
            variant_id=variant.variant_id,
            decision=HabitDecision.INSUFFICIENT_EVIDENCE,
            evidence=None,
            reason_codes=(ReasonCode.INSUFFICIENT_OCCURRENCES,),
        )

    tz = ZoneInfo(timezone_name)
    distinct_day_set = {candidate.observed_at.astimezone(tz).date() for candidate in organic}
    distinct_sessions = len({candidate.session_id for candidate in organic})
    distinct_days = len(distinct_day_set)

    reason_codes: list[ReasonCode] = []
    if distinct_sessions < config.min_distinct_sessions:
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS)
    if distinct_days < config.min_distinct_days:
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_DAYS)

    if reason_codes:
        return HabitAssessment(
            variant_id=variant.variant_id,
            decision=HabitDecision.INSUFFICIENT_EVIDENCE,
            evidence=None,
            reason_codes=tuple(reason_codes),
        )

    status_counts = dict.fromkeys(ObservationStatus, 0)
    for candidate in organic:
        status_counts[candidate.final_status] += 1

    first_seen_at = min(candidate.observed_at for candidate in organic)
    last_seen_at = max(candidate.observed_at for candidate in organic)

    mean_gap_days, gap_regularity = _gap_statistics(distinct_day_set)
    cadence = _cadence_of(mean_gap_days, gap_regularity, config)

    window_start = first_seen_at.astimezone(tz).date()
    window_end = last_seen_at.astimezone(tz).date()
    active_days_total = _active_days_total(all_series, tz, window_start, window_end)
    # Her `distinct_days` tarihi bir `EpisodeCandidate.observed_at` (== kaynak `OSeries.
    # started_at`, bkz. `episodes.candidates._candidate_from_indices`) demektir ve pencere bu
    # pattern'in kendi ilk/son gününden türediği için tanım gereği pencerenin içindedir --
    # bölünme asla sıfıra gitmez (bkz. docs/engine-decisions.md #7).
    assert active_days_total >= distinct_days

    evidence = HabitEvidence(
        organic_occurrences=len(organic),
        distinct_sessions=distinct_sessions,
        distinct_days=distinct_days,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        status_vector=StatusVector(
            success=status_counts[ObservationStatus.SUCCESS],
            fail=status_counts[ObservationStatus.FAIL],
            cancel=status_counts[ObservationStatus.CANCEL],
            unknown=status_counts[ObservationStatus.UNKNOWN],
        ),
        active_days_total=active_days_total,
        support_ratio=distinct_days / active_days_total,
        mean_gap_days=mean_gap_days,
        gap_regularity=gap_regularity,
        cadence=cadence,
    )
    return HabitAssessment(variant_id=variant.variant_id, decision=HabitDecision.HABIT_DETECTED, evidence=evidence)
