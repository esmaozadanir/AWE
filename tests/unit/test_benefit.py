"""Benefit Evaluator (bölüm 6.14): `observed_actions - planned_actions` deterministik farkı."""

from __future__ import annotations

from awe.benefit import evaluate_benefit
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    AutomaticAction,
    BenefitLevel,
    FinalActionOwner,
    IntentState,
    PlanMode,
)
from awe.domain.plan import ShortcutAnchor, ShortcutIntent


def _intent(anchor_effect: str, mode: PlanMode | None = PlanMode.NAVIGATE) -> ShortcutIntent:
    anchor = ShortcutAnchor(
        symbol=("some_action", anchor_effect, "screen", "v1"),
        position=2,
        strength=AnchorStrength.STRONG,
        status=AnchorStatus.RESOLVED,
    )
    return ShortcutIntent(
        intent_id="intent1",
        variant_id="var1",
        anchor=anchor,
        state=IntentState.READY,
        mode=mode,
        destination_screen="screen",
        target=None,
        requires_user_confirmation=False,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=3,
    )


def test_direct_transition_anchor_only_costs_the_launch_tap():
    """Bölüm 7 örneği: K1->K2->K3 (route/open), observed=3, planned=1, saved=2 -> CLEAR."""
    intent = _intent("open")
    benefit = evaluate_benefit(intent, scope_length=3)

    assert benefit.observed_actions == 3
    assert benefit.planned_actions == 1
    assert benefit.saved_actions == 2
    assert benefit.level == BenefitLevel.CLEAR


def test_action_surface_anchor_also_costs_the_final_action():
    """Bölüm 6.14 örneği: open_messages -> apply_filter (select). observed=2, planned=2
    (dokunuş + hâlâ gereken filtre işlemi), saved=0 -> NONE."""
    intent = _intent("select")
    benefit = evaluate_benefit(intent, scope_length=2)

    assert benefit.planned_actions == 2
    assert benefit.saved_actions == 0
    assert benefit.level == BenefitLevel.NONE


def test_prefill_also_leaves_final_confirmation_to_the_user():
    intent = _intent("submit", mode=PlanMode.PREFILL)
    benefit = evaluate_benefit(intent, scope_length=4)

    assert benefit.planned_actions == 2
    assert benefit.saved_actions == 2
    assert benefit.level == BenefitLevel.CLEAR


def test_benefit_level_table():
    assert BenefitEvidence(intent_id="i", observed_actions=0, planned_actions=1).level == BenefitLevel.NEGATIVE
    assert BenefitEvidence(intent_id="i", observed_actions=1, planned_actions=1).level == BenefitLevel.NONE
    assert BenefitEvidence(intent_id="i", observed_actions=2, planned_actions=1).level == BenefitLevel.LIMITED
    assert BenefitEvidence(intent_id="i", observed_actions=3, planned_actions=1).level == BenefitLevel.CLEAR
