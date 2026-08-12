"""Suggestion lifecycle geçişleri.

Bir suggestion DISMISSED durumundayken cooldown süresi dolar ve davranış organik olarak
tekrar etmeye devam ederse ACTIVE'e geri döner — dismiss kalıcı bir ret değil, geçici bir
bastırmadır. Cooldown süresi dolmuş ama organik kanıt de kaybolmuşsa DISMISSED'te kalır
(kullanıcı zaten reddetmişti, yeniden canlanmak için tekrar organik kullanım gerekir).

Bu katman yeni tasarımda ele alınmamıştır (bölüm 9.11: "bu tasarımda tamamlanmamıştır") —
mevcut, çalışan mekanizma korunmuş ve yalnızca girdi şekli yeni pipeline'a uyarlanmıştır.
Staleness artık Habit Evaluator'dan gelen bir `liveness` skoruna değil (bölüm 6.7 artık böyle
bir skor üretmiyor — "regularity/entropy/lift ... MVP dışında bırakılmıştır"), doğrudan
`HabitEvidence.last_seen_at` üzerinden bu katmanın kendi basit eşiğine dayanır.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from awe.config.engine_config import LifecycleConfig
from awe.domain.enums import HabitDecision, SuggestionState


def next_state_for_reanalysis(
    current_state: SuggestionState | None,
    dismiss_cooldown_until: datetime | None,
    habit_decision: HabitDecision,
    has_eligible_intent: bool,
    last_seen_at: datetime | None,
    now: datetime,
    config: LifecycleConfig,
) -> SuggestionState:
    if current_state == SuggestionState.DISMISSED:
        cooldown_expired = dismiss_cooldown_until is not None and now >= dismiss_cooldown_until
        if cooldown_expired and habit_decision == HabitDecision.HABIT_DETECTED and has_eligible_intent:
            return SuggestionState.ACTIVE
        return SuggestionState.DISMISSED

    if habit_decision != HabitDecision.HABIT_DETECTED or not has_eligible_intent:
        return SuggestionState.INVALIDATED if current_state is not None else SuggestionState.PENDING_EVIDENCE

    if last_seen_at is not None:
        days_since_last_seen = (now - last_seen_at).total_seconds() / 86400
        if days_since_last_seen > config.stale_after_days:
            return SuggestionState.STALE

    return SuggestionState.ACTIVE


def dismiss(now: datetime, config: LifecycleConfig) -> tuple[SuggestionState, datetime]:
    return SuggestionState.DISMISSED, now + timedelta(days=config.dismiss_cooldown_days)
