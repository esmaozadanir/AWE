"""Anchor Resolver, Scope Projector, Destination Resolver ve Shortcut Intent Builder
çıktı modelleri (bölüm 6.9-6.12).

`FieldBinding`/çoklu-parametre kavramı kasıtlı olarak yoktur: yeni sözleşmede tek bir
skaler `target` alanı vardır, "workspace_1 + report_9" gibi compound identity taşınamaz
(bölüm 6.12) — bu durumda Intent `UNSUPPORTED` olur.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    AutomaticAction,
    FinalActionOwner,
    IntentState,
    PlanMode,
    ReasonCode,
)
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class ShortcutAnchor:
    symbol: Symbol
    position: int
    """TargetVariant'ın family sembol dizisi içindeki index — yalnızca açıklanabilirlik amaçlı."""
    strength: AnchorStrength
    status: AnchorStatus
    reason_codes: tuple[ReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class Scope:
    variant_id: str
    included: tuple[Symbol, ...]
    excluded_trailing: tuple[Symbol, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.included) == 0


@dataclass(frozen=True, slots=True)
class Destination:
    screen: str | None
    resolved: bool
    reason_codes: tuple[ReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class ShortcutIntent:
    intent_id: str
    variant_id: str
    anchor: ShortcutAnchor

    state: IntentState
    mode: PlanMode | None
    destination_screen: str | None
    target: str | None
    requires_user_confirmation: bool
    automatic_action: AutomaticAction
    final_action_owner: FinalActionOwner

    supporting_occurrences: int
    reason_codes: tuple[ReasonCode, ...] = ()
