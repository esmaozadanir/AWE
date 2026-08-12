"""Habit Evaluator (bölüm 6.7): tek görevi recurrence ölçmektir.

MVP kapısı: `distinct session >= 3 AND distinct calendar day >= 2`. Bu katman regularity/
entropy/lift gibi gelişmiş istatistikler kullanmaz — yalnızca hard count-based gate.

Kısayol tetiklemesiyle başlayan occurrence'lar organik kanıttan hariç tutulur (belgede yazılı
değil, bkz. `ObservationTrigger.SHORTCUT` docstring'i — kasıtlı bir superset koruması: aksi
halde bir kısayolun kendi kullanımı kendi önerisini besleyen bir döngü oluşturabilir)."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import HabitDecision, ObservationStatus, ReasonCode
from awe.domain.episode import EpisodeCandidate
from awe.domain.habit import HabitAssessment, HabitEvidence, StatusVector
from awe.domain.target import TargetVariant


def evaluate_habit(
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
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
    distinct_sessions = len({candidate.session_id for candidate in organic})
    distinct_days = len({candidate.observed_at.astimezone(tz).date() for candidate in organic})

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

    evidence = HabitEvidence(
        organic_occurrences=len(organic),
        distinct_sessions=distinct_sessions,
        distinct_days=distinct_days,
        first_seen_at=min(candidate.observed_at for candidate in organic),
        last_seen_at=max(candidate.observed_at for candidate in organic),
        status_vector=StatusVector(
            success=status_counts[ObservationStatus.SUCCESS],
            fail=status_counts[ObservationStatus.FAIL],
            cancel=status_counts[ObservationStatus.CANCEL],
            unknown=status_counts[ObservationStatus.UNKNOWN],
        ),
    )
    return HabitAssessment(variant_id=variant.variant_id, decision=HabitDecision.HABIT_DETECTED, evidence=evidence)
