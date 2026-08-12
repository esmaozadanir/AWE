"""Episode Candidate modeli.

Family eşleştirmesine giren aday davranış birimi. İki kaynaktan üretilir: bir OSeries'in
tamamı (`FULL_CHUNK`) ya da farklı chunk/session'lar arasında bulunan, sıra-korumalı exact
ortak alt diziler (`COMMON_SUBSEQUENCE` — bkz. `awe.episodes.candidates` modül docstring'i).
Henüz habit kararı vermez — yalnızca Exact Base Family'nin girişidir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import EpisodeCandidateKind, ObservationStatus, ObservationTrigger
from awe.domain.tokens import BehaviorStep, Symbol


@dataclass(frozen=True, slots=True)
class EpisodeCandidate:
    candidate_id: str
    project_id: str
    subject_id: str
    session_id: str
    series_id: str
    """Kaynak OSeries'in `series_id`'si — izlenebilirlik."""

    kind: EpisodeCandidateKind
    steps: tuple[BehaviorStep, ...]
    step_indices: tuple[int, ...]
    """Kaynak OSeries.steps içindeki, `steps` ile aynı sırada karşılık gelen pozisyonlar
    (izlenebilirlik). `FULL_CHUNK` için ardışıktır (`0..len-1`); `COMMON_SUBSEQUENCE` için
    sıra korunur ama ardışık olması gerekmez (araya kaynak dizide eşleşmeyen adımlar
    girebilir)."""

    observed_at: datetime
    entry_trigger: ObservationTrigger
    has_shortcut_trigger: bool
    final_status: ObservationStatus

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(step.symbol for step in self.steps)

    @property
    def targets(self) -> tuple[str | None, ...]:
        return tuple(step.target for step in self.steps)
