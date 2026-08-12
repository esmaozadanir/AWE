"""O-Series modeli: tek session içerisindeki bir behavior attempt/occurrence (bölüm 35)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import ObservationStatus, ObservationTrigger, OrderingConfidence
from awe.domain.observation import Observation
from awe.domain.tokens import BehaviorStep, Symbol


@dataclass(frozen=True, slots=True)
class RetryEvidence:
    symbol: Symbol
    failed_attempts: int
    """Aynı sembolün normalize dizide tek adıma sıkıştırılmadan önceki başarısız deneme sayısı."""


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
    """Ham Observation dizisi — normalizasyon bu kanıtı yok etmez (bölüm 36)."""

    normalized_steps: tuple[BehaviorStep, ...]
    """Family karşılaştırması için üretilen, detour/retry sıkıştırılmış projeksiyon."""

    retries: tuple[RetryEvidence, ...]
    detour_observation_count: int
    ended_by_breaks_episode: bool

    entry_trigger: ObservationTrigger
    entry_screen: str | None

    has_shortcut_trigger: bool
    """Bu occurrence bir shortcut tetiklemesiyle mi başladı (bölüm 68)."""

    final_status: ObservationStatus

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(step.symbol for step in self.normalized_steps)

    @property
    def is_empty(self) -> bool:
        return len(self.normalized_steps) == 0
