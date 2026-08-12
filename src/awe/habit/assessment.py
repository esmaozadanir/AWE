"""Habit hard-evidence gate'leri ve nihai karar (bölüm 61-62, IMPLEMENTATION_PLAN.md 2.2).

Gate'ler yalnızca gün/session/occurrence SAYIMINA dayanır — herhangi bir oran formülüne değil.
Bu yüzden "günde 5-10 kullanım" gibi yoğun ama gerçek Habit'ler cezalandırılmaz, buna karşın
one-day/two-day burst ve single-session repeater güvenilir biçimde reddedilir.

Bir gate'in kendi boyutu (gün ya da session sayısı) yetersizken toplam occurrence sayısı zaten
`min_occurrences` eşiğini geçmişse, bu "zamanla düzelecek eksik kanıt" değil, "davranış zaten
yoğun biçimde denendi ama yalnızca bir/iki günde/session'da yoğunlaştı" anlamına gelir — yani
NOT_HABIT olarak değerlendirilir. Occurrence sayısı da eşiğin altındaysa aile henüz genç demektir
ve PENDING_EVIDENCE ile bırakılır.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import HabitDecision, ReasonCode
from awe.domain.habit import HabitAssessment
from awe.domain.series import OSeries
from awe.habit.evidence import build_habit_evidence


def _gate_status(dimension_count: int, min_dimension: int, organic_count: int, min_occurrences: int) -> str:
    if dimension_count >= min_dimension:
        return "ok"
    if organic_count >= min_occurrences:
        return "burst_like"
    return "insufficient"


def evaluate_habit(
    family_id: str,
    member_series: list[OSeries],
    now: datetime,
    timezone_name: str,
    config: HabitConfig,
) -> HabitAssessment:
    organic_series = [s for s in member_series if not s.has_shortcut_trigger]
    shortcut_count = len(member_series) - len(organic_series)
    organic_count = len(organic_series)

    if organic_count == 0:
        return HabitAssessment(
            family_id=family_id,
            decision=HabitDecision.PENDING_EVIDENCE,
            evidence=None,
            reason_codes=(ReasonCode.INSUFFICIENT_OCCURRENCES,),
        )

    tz = ZoneInfo(timezone_name)
    distinct_sessions = len({s.session_id for s in organic_series})
    distinct_days = len({s.started_at.astimezone(tz).date() for s in organic_series})

    session_status = _gate_status(
        distinct_sessions, config.min_distinct_sessions, organic_count, config.min_occurrences
    )
    day_status = _gate_status(
        distinct_days, config.min_distinct_days, organic_count, config.min_occurrences
    )

    reason_codes: list[ReasonCode] = []
    if organic_count < config.min_occurrences:
        reason_codes.append(ReasonCode.INSUFFICIENT_OCCURRENCES)
    if session_status != "ok":
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS)
    if day_status != "ok":
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_DAYS)
        if distinct_days <= 2:
            reason_codes.append(ReasonCode.ONE_DAY_BURST)

    if reason_codes:
        decision = (
            HabitDecision.NOT_HABIT
            if "burst_like" in (session_status, day_status)
            else HabitDecision.PENDING_EVIDENCE
        )
        return HabitAssessment(
            family_id=family_id, decision=decision, evidence=None, reason_codes=tuple(reason_codes)
        )

    evidence = build_habit_evidence(organic_series, shortcut_count, now, timezone_name, config)
    stale_reason = (ReasonCode.STALE_BEHAVIOR,) if evidence.liveness.value == "stale" else ()
    return HabitAssessment(
        family_id=family_id, decision=HabitDecision.PASS, evidence=evidence, reason_codes=stale_reason
    )
