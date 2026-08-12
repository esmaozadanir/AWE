"""Habit katmanının kanıt ve karar modelleri (bölüm 61-67)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import HabitDecision, LivenessState, ReasonCode


@dataclass(frozen=True, slots=True)
class HabitEvidence:
    organic_occurrences: int
    distinct_sessions: int
    distinct_days: int

    first_seen_at: datetime
    last_seen_at: datetime
    active_span_days: int

    top_day_share: float
    top_session_share: float

    median_gap_days: float | None
    """Ardışık aktif günler arası medyan boşluk. <3 farklı gün varsa None (bölüm 66)."""

    regularity: float | None
    """0-1 arası düzenlilik kanıtı. Anlamlı örneklem yoksa None — asla 1.0'a düşürülmez."""

    staleness_ratio: float | None
    liveness: LivenessState

    shortcut_utility_occurrences: int
    """trigger=shortcut olan occurrence sayısı — organic_occurrences'a dahil değildir (bölüm 68)."""

    support_score: float
    """Doygunlaşan (saturating) support skoru — hard gate değil, açıklanabilirlik/sıralama içindir."""

    habit_strength: float
    """support_score, regularity ve liveness'i birleştiren, yalnızca gate geçildikten sonra
    anlamlı olan soft skor. Hiçbir hard gate kararını değiştirmez."""


@dataclass(frozen=True, slots=True)
class HabitAssessment:
    family_id: str
    decision: HabitDecision
    evidence: HabitEvidence | None
    reason_codes: tuple[ReasonCode, ...] = ()
