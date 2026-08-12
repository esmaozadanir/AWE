"""O-Series modeli: bir session içindeki tek structural chunk (bölüm 6.3).

Eski tasarımdan farklı olarak sınır, açık bir `breaksEpisode` bayrağı veya "completion effect"
tahminiyle değil; yalnızca (a) aynı timestamp'te birden fazla ACTION gözlenip sıra üretilemediği
"ambiguity barrier" anları ve (b) `navigation`/`notification`/`deeplink` tetikleyicili bir ACTION'ın
mevcut akışın ortasında gelmesiyle çizilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import ObservationStatus, ObservationTrigger, OrderingConfidence
from awe.domain.observation import Observation
from awe.domain.tokens import BehaviorStep, Symbol


@dataclass(frozen=True, slots=True)
class OSeries:
    series_id: str
    project_id: str
    subject_id: str
    session_id: str

    started_at: datetime
    ended_at: datetime
    ordering_confidence: OrderingConfidence

    raw_observations: tuple[Observation, ...]
    """Ham Observation dizisi (CONTEXT/IGNORE dahil) — izlenebilirlik için korunur."""

    steps: tuple[BehaviorStep, ...]
    """Yalnız ACTION-classified adımlar, event-time sırasıyla. Normalizasyon/sıkıştırma yoktur
    (bölüm 6.4: "Fuzzy merge yoktur") — retry veya geri-navigasyon tekrarları olduğu gibi kalır."""

    entry_trigger: ObservationTrigger
    entry_screen: str | None
    has_shortcut_trigger: bool
    """Bu chunk bir shortcut tetiklemesiyle mi başladı — Habit'in organic-evidence dışlaması için."""

    final_status: ObservationStatus

    cut_by_ambiguity: bool
    """Bu chunk, aynı timestamp'te birden fazla ACTION gözlendiği için burada kesildi mi
    (bölüm 6.3 ambiguity barrier). Yalnızca açıklanabilirlik/log amaçlıdır."""

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(step.symbol for step in self.steps)

    @property
    def is_empty(self) -> bool:
        return len(self.steps) == 0
