"""Behavior Family modeli: farklı sessionlardaki O-Series'lerin toplandığı davranış ailesi.

Yapı, tek bir exact sequence yerine sınırlı sayıda temsilci variant ve bunlar üzerinden
türetilen core/optional ilişki tablosu üzerine kuruludur (bölüm 51, IMPLEMENTATION_PLAN.md 2.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import FamilyMatchOutcome
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class FamilyVariant:
    symbols: tuple[Symbol, ...]
    support: int
    """Bu tam normalize diziye sahip üye O-Series sayısı (exact variant compression, bölüm 47)."""
    last_observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CoreRelationship:
    predecessor: Symbol
    successor: Symbol
    coverage: float
    """Bu ardışık çiftin temsilci variant'lar içindeki kapsama oranı."""
    is_core: bool


@dataclass
class BehaviorFamily:
    family_id: str
    project_id: str
    subject_id: str

    representative_variants: list[FamilyVariant] = field(default_factory=list)
    relationships: list[CoreRelationship] = field(default_factory=list)
    cohesion: float = 1.0

    member_series_ids: list[str] = field(default_factory=list)
    ambiguous_series_ids: list[str] = field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def core_symbols_in_order(self) -> list[Symbol]:
        """Core ilişkilerden türetilen, açıklanabilirlik amaçlı yaklaşık ana sıra."""
        core = [r for r in self.relationships if r.is_core]
        if not core:
            return list(self.representative_variants[0].symbols) if self.representative_variants else []
        ordered: list[Symbol] = []
        successors = {r.predecessor: r.successor for r in core}
        starts = {r.predecessor for r in core} - {r.successor for r in core}
        current: Symbol | None = next(iter(starts), core[0].predecessor)
        seen: set[Symbol] = set()
        while current is not None and current not in seen:
            ordered.append(current)
            seen.add(current)
            current = successors.get(current)
        return ordered

    @property
    def total_support(self) -> int:
        return sum(v.support for v in self.representative_variants)


@dataclass(frozen=True, slots=True)
class FamilyMatchDecision:
    outcome: FamilyMatchOutcome
    family_id: str | None
    best_similarity: float
    core_coverage: float
    ambiguous_family_ids: tuple[str, ...] = ()
