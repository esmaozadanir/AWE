"""Exact Base Family modeli (bölüm 6.5).

Eski tasarımdan farklı olarak fuzzy/ağırlıklı benzerlik yoktur: bir family tamamen aynı
`(action, effect, screen, mapping_version)` sembol dizisini paylaşan occurrence'ların kümesidir.
`screen` artık sembolün parçası olduğundan ve tolerans olmadığından ayrı bir "variant" veya
"core ilişki" kavramına gerek yoktur — bir family zaten tek bir exact dizidir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.tokens import Symbol


@dataclass
class BaseFamily:
    family_id: str
    project_id: str
    subject_id: str
    symbols: tuple[Symbol, ...]

    occurrence_ids: list[str] = field(default_factory=list)
    """Bu exact diziye sahip `EpisodeCandidate.candidate_id` referansları."""

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def support(self) -> int:
        return len(self.occurrence_ids)
