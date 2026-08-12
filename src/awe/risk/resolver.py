"""Client Resolver sözleşmesi (bölüm 78).

Backend, geçmiş loglardan istemci uygulamanın belirli bir state'e gerçekten programatik
olarak gidebileceğini bilemez. Bu minimal sözleşme, entegrasyonun neyi destekleyip
desteklemediğini açıkça beyan etmesini sağlar — ağır bir capability manifest sistemi değildir
(bölüm 3.6).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolverContract:
    supports_navigate: bool = True
    supports_prefill: bool = True
    accepted_bindings: frozenset[str] | None = None
    """None: her binding kabul edilir. Boş olmayan bir küme: yalnızca bu alan adları
    prefill edilebilir, geri kalanı REDUCE_BINDINGS ile düşürülür."""
    requires_review: bool = False
    supports_runtime_validation: bool = False

    @staticmethod
    def permissive() -> ResolverContract:
        return ResolverContract()
