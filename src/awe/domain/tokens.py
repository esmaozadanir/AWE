"""Karşılaştırma için canonical davranış sembolü ve adım modeli.

Tasarım kararı (bölüm 6.4 Episode Candidate Builder, 6.5 Exact Base Family): karşılaştırma
sembolü `(actionKey, exact effect, opaque screen, mappingVersion)` dörtlüsüdür. Eski tasarımdan
farklı olarak `screen` artık sembolün bir parçasıdır — fuzzy/ağırlıklı benzerlik yoktur, yalnız
exact eşitlik vardır ("Fuzzy merge yoktur. Optional step toleransı yoktur.", bölüm 6.4). Bu,
precision'ı artırır ama varyasyonlu gerçek akışları parçalayabilir (bkz. bölüm 9.3 — bilinçli
kabul edilmiş bir ödünleşim, motor tarafında telafi edilmez).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ObservationEffect, ObservationStatus

Symbol = tuple[str, str, str | None, str]
"""(action, effect, screen, mapping_version) — Episode Candidate ve Exact Base Family
karşılaştırmasının atomik birimi."""


@dataclass(frozen=True, slots=True)
class BehaviorToken:
    action: str
    effect: ObservationEffect
    screen: str | None
    mapping_version: str

    @property
    def symbol(self) -> Symbol:
        return (self.action, self.effect.value, self.screen, self.mapping_version)


@dataclass(frozen=True, slots=True)
class BehaviorStep:
    """Bir ACTION-classified adım: karşılaştırma sembolü + hedef + izlenebilirlik."""

    token: BehaviorToken
    target: str | None
    target_unknown: bool
    """Kaynak Observation'ın `quality.missing_target_field` değeri — bu adımda target verisi
    hiç gönderilmemiş miydi (bölüm 3 kural 6). Target Resolver'ın `UNKNOWN_TARGET` kararı için
    gereklidir; `target=None` tek başına "açıkça yok" ile "bilinmiyor"u ayırt edemez."""
    status: ObservationStatus
    observation_index: int
    """Bu adımın ait olduğu ham Observation'ın chunk içindeki sırası (izlenebilirlik)."""

    @property
    def symbol(self) -> Symbol:
        return self.token.symbol
