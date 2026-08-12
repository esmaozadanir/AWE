"""Suggestion lifecycle geçişleri (bölüm 94).

Bir suggestion DISMISSED durumundayken cooldown süresi dolar ve davranış organik olarak
tekrar etmeye devam ederse ACTIVE'e geri döner — dismiss kalıcı bir ret değil, geçici bir
bastırmadır. Cooldown süresi dolmuş ama organik kanıt de kaybolmuşsa DISMISSED'te kalır
(kullanıcı zaten reddetmişti, yeniden canlanmak için tekrar organik kullanım gerekir).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from awe.config.engine_config import LifecycleConfig
from awe.domain.enums import HabitDecision, LivenessState, SuggestionState


def next_state_for_reanalysis(
    current_state: SuggestionState | None,
    dismiss_cooldown_until: datetime | None,
    habit_decision: HabitDecision,
    has_eligible_plan: bool,
    liveness: LivenessState | None,
    now: datetime,
) -> SuggestionState:
    if current_state == SuggestionState.DISMISSED:
        cooldown_expired = dismiss_cooldown_until is not None and now >= dismiss_cooldown_until
        if cooldown_expired and habit_decision == HabitDecision.PASS and has_eligible_plan:
            return SuggestionState.ACTIVE
        return SuggestionState.DISMISSED

    if habit_decision == HabitDecision.NOT_HABIT or not has_eligible_plan:
        return SuggestionState.INVALIDATED if current_state is not None else SuggestionState.PENDING_EVIDENCE

    if habit_decision == HabitDecision.PENDING_EVIDENCE:
        return SuggestionState.PENDING_EVIDENCE

    if liveness == LivenessState.STALE:
        return SuggestionState.STALE

    return SuggestionState.ACTIVE


def dismiss(now: datetime, config: LifecycleConfig) -> tuple[SuggestionState, datetime]:
    return SuggestionState.DISMISSED, now + timedelta(days=config.dismiss_cooldown_days)
