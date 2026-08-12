"""Shortcut Planner çıktı modelleri: ShortcutAnchor, FieldBinding, PlanCandidate.

`destination` kavramı yoktur (bölüm 3.5, 70). Anchor bir index değil, family core sırası
içindeki yapısal bir sembol referansıdır (bölüm 71); her occurrence'ta kendi normalize
dizisi içinde sembol eşleştirmesiyle çözülür.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import FieldState, PlanType
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class ShortcutAnchor:
    symbol: Symbol
    screen: str | None
    core_position: int
    """Family core sırasındaki konum — yalnızca açıklanabilirlik/loglama amaçlıdır, occurrence
    çözümlemesi bu index'e değil `symbol` eşleşmesine dayanır."""


@dataclass(frozen=True, slots=True)
class FieldBinding:
    """Anchor öncesi state'te gözlenen bir alanın (target ya da parametre) kararlılığı."""

    field_name: str
    state: FieldState
    dominant_value: str | None
    dominance: float
    coverage: float
    sample_size: int
    recent_dominance: float | None
    """Son-K pencere içindeki dominance — concept drift kanıtı (bölüm 77). Yetersiz veri varsa None."""


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    plan_id: str
    family_id: str
    plan_type: PlanType
    anchor: ShortcutAnchor
    bindings: tuple[FieldBinding, ...]
    target_binding: FieldBinding | None
    supporting_occurrences: int
