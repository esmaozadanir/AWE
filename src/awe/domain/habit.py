"""Habit Evaluator'ın kanıt ve karar modelleri (bölüm 6.7).

Değerlendirme, Base Family değil `TargetVariant` seviyesinde yapılır (bölüm 6.6) — farklı
hedefler kanıtlarını havuzlamaz.

Bir önceki turda kullanıcı talebiyle `HabitEvidence`'a eklenmiş olan regularity/support
istatistik katmanı (`cadence`, `mean_gap_days`, `gap_regularity`, `active_days_total`,
`support_ratio`, `status_vector`) hiçbir yerde tüketilmediği için kaldırıldı (bkz.
docs/engine-decisions.md #11; ekleme gerekçesi için #7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import HabitDecision, ReasonCode


@dataclass(frozen=True, slots=True)
class HabitEvidence:
    organic_occurrences: int
    """trigger=shortcut olan occurrence'lar hariç (bölüm 6.7, kısayol kullanımı organik kanıt
    sayılmaz — bkz. `ObservationTrigger.SHORTCUT` docstring'i)."""
    distinct_sessions: int
    distinct_days: int

    first_seen_at: datetime
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class HabitAssessment:
    variant_id: str
    """Değerlendirilen `TargetVariant.variant_id`."""
    decision: HabitDecision
    evidence: HabitEvidence | None
    reason_codes: tuple[ReasonCode, ...] = ()
