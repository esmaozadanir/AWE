"""Karşılaştırma için canonical davranış sembolü ve adım modeli.

Tasarım kararı (bkz. IMPLEMENTATION_PLAN.md 2.3): karşılaştırma sembolü yalnızca
`(action, effect)` ikilisidir. `screen` ve `widget` sembolün bir parçası değil,
ayrıştırıcı ağırlıklandırmaya tabi bağlamsal kanıttır — bu sayede widget rename veya
ortak başlangıç ekranı gibi durumlar Family kimliğini kırmaz (bölüm 22-24, 115).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ObservationEffect, ObservationStatus

Symbol = tuple[str, str]
"""(action, effect) — Family karşılaştırmasının atomik birimi."""


@dataclass(frozen=True, slots=True)
class BehaviorToken:
    action: str
    effect: ObservationEffect

    @property
    def symbol(self) -> Symbol:
        return (self.action, self.effect.value)


@dataclass(frozen=True, slots=True)
class BehaviorStep:
    """Normalize edilmiş dizideki tek bir adım: karşılaştırma sembolü + bağlamsal kanıt."""

    token: BehaviorToken
    screen: str | None
    widget: str | None
    status: ObservationStatus
    observation_index: int
    """Bu adımın ait olduğu ham Observation'ın occurrence içindeki sırası (izlenebilirlik)."""

    @property
    def symbol(self) -> Symbol:
        return self.token.symbol
