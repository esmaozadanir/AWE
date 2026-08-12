"""Shortcut Intent Builder (bölüm 6.12): yalnızca çözülmüş Habit + Anchor + Scope + Destination
sonucunu runtime sözleşmesine çevirir. `EXECUTE` modu yoktur.
"""

from __future__ import annotations

from awe.domain.enums import (
    AnchorStatus,
    AutomaticAction,
    FinalActionOwner,
    IntentState,
    PlanMode,
    ReasonCode,
    TargetVariantKind,
)
from awe.domain.plan import Destination, Scope, ShortcutAnchor, ShortcutIntent
from awe.domain.target import TargetVariant
from awe.planner.anchors import ROUTE_OPEN_EFFECTS


def _unsupported(
    variant: TargetVariant,
    anchor: ShortcutAnchor,
    destination_screen: str | None,
    reason_codes: tuple[ReasonCode, ...],
) -> ShortcutIntent:
    return ShortcutIntent(
        intent_id=f"{variant.variant_id}:{anchor.position}",
        variant_id=variant.variant_id,
        anchor=anchor,
        state=IntentState.UNSUPPORTED,
        mode=None,
        destination_screen=destination_screen,
        target=None,
        requires_user_confirmation=False,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=len(variant.occurrence_ids),
        reason_codes=reason_codes,
    )


def build_shortcut_intent(
    variant: TargetVariant, anchor: ShortcutAnchor, scope: Scope, destination: Destination
) -> ShortcutIntent:
    if anchor.status not in (AnchorStatus.RESOLVED, AnchorStatus.ATTEMPT_ONLY) or scope.is_empty:
        reasons = anchor.reason_codes or (ReasonCode.AMBIGUOUS_ANCHOR,)
        return _unsupported(variant, anchor, destination.screen, reasons)

    if not destination.resolved:
        return _unsupported(
            variant, anchor, None, destination.reason_codes or (ReasonCode.DESTINATION_UNRESOLVED,)
        )

    # Anchor'dan önceki ara adımlar yalnız route/open olabilir; başka bir ara effect varsa
    # generic screen+target sözleşmesi o adımı yeniden oluşturamaz (bölüm 6.12).
    intermediate = scope.included[:-1]
    if any(symbol[1] not in ROUTE_OPEN_EFFECTS for symbol in intermediate):
        return _unsupported(variant, anchor, destination.screen, (ReasonCode.UNREPRESENTED_INTERMEDIATE_ACTION,))

    if variant.kind == TargetVariantKind.VARIABLE_TARGET:
        return _unsupported(variant, anchor, destination.screen, (ReasonCode.UNSUPPORTED_COMPOUND_TARGET,))

    target = variant.single_target if variant.kind == TargetVariantKind.FIXED_TARGET else None
    mode = PlanMode.PREFILL if target is not None else PlanMode.NAVIGATE

    return ShortcutIntent(
        intent_id=f"{variant.variant_id}:{anchor.position}",
        variant_id=variant.variant_id,
        anchor=anchor,
        state=IntentState.READY,
        mode=mode,
        destination_screen=destination.screen,
        target=target,
        requires_user_confirmation=mode == PlanMode.PREFILL,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=len(variant.occurrence_ids),
    )
