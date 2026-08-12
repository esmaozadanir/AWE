"""Habit Evaluator'ın kanıt ve karar modelleri (bölüm 6.7).

Bilinçli olarak sade: regularity/entropy/lift gibi gelişmiş istatistikler burada yoktur
("Bu katman ... MVP dışında bırakılmıştır", bölüm 6.7). Değerlendirme, Base Family değil
`TargetVariant` seviyesinde yapılır (bölüm 6.6) — farklı hedefler kanıtlarını havuzlamaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import HabitDecision, ReasonCode


@dataclass(frozen=True, slots=True)
class StatusVector:
    success: int
    fail: int
    cancel: int
    unknown: int

    @property
    def total(self) -> int:
        return self.success + self.fail + self.cancel + self.unknown


@dataclass(frozen=True, slots=True)
class HabitEvidence:
    organic_occurrences: int
    """trigger=shortcut olan occurrence'lar hariç (bölüm 6.7, kısayol kullanımı organik kanıt
    sayılmaz — bkz. `ObservationTrigger.SHORTCUT` docstring'i)."""
    distinct_sessions: int
    distinct_days: int

    first_seen_at: datetime
    last_seen_at: datetime

    status_vector: StatusVector
    """Fail/cancel occurrence'lar sayımdan çıkarılmaz (bölüm 6.7) — yalnızca burada dağılım
    olarak kayıt altına alınır."""


@dataclass(frozen=True, slots=True)
class HabitAssessment:
    variant_id: str
    """Değerlendirilen `TargetVariant.variant_id`."""
    decision: HabitDecision
    evidence: HabitEvidence | None
    reason_codes: tuple[ReasonCode, ...] = ()
