"""Selector (bölüm 6.15): eligibility kapıları, weak-anchor istisnası, exact-intent dedupe,
lexicographic sıralama."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    AutomaticAction,
    EffectPolicy,
    ExecutionExposure,
    FinalActionOwner,
    HabitDecision,
    IntentState,
    PlanMode,
    ReasonCode,
    RiskDecision,
    SelectionOutcome,
)
from awe.domain.habit import HabitAssessment, HabitEvidence
from awe.domain.plan import Scope, ShortcutAnchor, ShortcutIntent
from awe.domain.risk import ReliabilityEvidence, RiskAssessment, RiskEvidence
from awe.selection import Candidate, select

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _evidence(days=3, sessions=3) -> HabitEvidence:
    return HabitEvidence(
        organic_occurrences=sessions,
        distinct_sessions=sessions,
        distinct_days=days,
        first_seen_at=_NOW,
        last_seen_at=_NOW,
    )


def _candidate(
    intent_id: str,
    *,
    strength=AnchorStrength.STRONG,
    anchor_status=AnchorStatus.RESOLVED,
    habit_decision=HabitDecision.HABIT_DETECTED,
    intent_state=IntentState.READY,
    mode=PlanMode.PREFILL,
    target: str | None = "item_1",
    destination_screen="detail",
    risk_decision=RiskDecision.ALLOW,
    observed=3,
    planned=1,
    saved_days=3,
    saved_sessions=3,
    supporting_occurrences=3,
) -> Candidate:
    anchor = ShortcutAnchor(
        symbol=("open_item", "route", "detail", "v1"), position=1, strength=strength, status=anchor_status
    )
    intent = ShortcutIntent(
        intent_id=intent_id,
        variant_id=f"var-{intent_id}",
        anchor=anchor,
        state=intent_state,
        mode=mode,
        destination_screen=destination_screen,
        target=target,
        requires_user_confirmation=mode == PlanMode.PREFILL,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=supporting_occurrences,
    )
    scope = Scope(variant_id=intent.variant_id, included=(anchor.symbol,), excluded_trailing=())
    habit = HabitAssessment(
        variant_id=intent.variant_id,
        decision=habit_decision,
        evidence=_evidence(days=saved_days, sessions=saved_sessions)
        if habit_decision == HabitDecision.HABIT_DETECTED
        else None,
    )
    risk = RiskAssessment(
        intent_id=intent_id,
        decision=risk_decision,
        evidence=RiskEvidence(
            policy=EffectPolicy.SAFE,
            plan_surface=mode or PlanMode.NAVIGATE,
            execution_exposure=ExecutionExposure.NONE,
            interaction_guard_intact=True,
            observed_goal_sensitivity=EffectPolicy.SAFE,
            reliability=ReliabilityEvidence(completion_rate=1.0, failure_rate=0.0, cancel_rate=0.0, sample_size=3),
            data_quality_ok=True,
        ),
    )
    benefit = BenefitEvidence(intent_id=intent_id, observed_actions=observed, planned_actions=planned)
    return Candidate(intent=intent, scope=scope, habit=habit, risk=risk, benefit=benefit)


def _outcome(results, intent_id):
    return next(r for r in results if r.intent_id == intent_id).outcome


def test_fully_eligible_candidate_is_selected():
    candidate = _candidate("i1")
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.SELECTED


def test_intent_not_ready_is_rejected():
    candidate = _candidate("i1", intent_state=IntentState.UNSUPPORTED)
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.REJECTED


def test_attempt_only_anchor_is_rejected():
    candidate = _candidate("i1", anchor_status=AnchorStatus.ATTEMPT_ONLY)
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.REJECTED


def test_risk_block_is_rejected():
    candidate = _candidate("i1", risk_decision=RiskDecision.BLOCK)
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.REJECTED


def test_limited_benefit_is_rejected_high_precision_policy():
    """Bölüm 6.15: LIMITED dahil CLEAR dışındaki Benefit seviyeleri reddedilir."""
    candidate = _candidate("i1", observed=2, planned=1)  # saved=1 -> LIMITED
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.REJECTED


def test_weak_navigate_with_allow_and_clear_is_eligible():
    candidate = _candidate("i1", strength=AnchorStrength.WEAK, mode=PlanMode.NAVIGATE, target=None)
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.SELECTED


def test_weak_prefill_is_rejected_by_the_defensive_mode_check():
    candidate = _candidate("i1", strength=AnchorStrength.WEAK, mode=PlanMode.PREFILL, target="x")
    results = select([candidate], "proj", "subj")
    assert _outcome(results, "i1") == SelectionOutcome.REJECTED


def test_identical_runtime_intents_are_deduped_keeping_the_stronger_one():
    weak = _candidate(
        "weak",
        strength=AnchorStrength.MEDIUM,
        mode=PlanMode.PREFILL,
        target="item_1",
        destination_screen="detail",
        saved_days=2,
        saved_sessions=2,
        supporting_occurrences=2,
    )
    strong = _candidate(
        "strong",
        strength=AnchorStrength.STRONG,
        mode=PlanMode.PREFILL,
        target="item_1",
        destination_screen="detail",
        saved_days=5,
        saved_sessions=5,
        supporting_occurrences=5,
    )
    results = select([weak, strong], "proj", "subj")

    assert _outcome(results, "strong") == SelectionOutcome.SELECTED
    assert _outcome(results, "weak") == SelectionOutcome.DEDUPED
    weak_result = next(r for r in results if r.intent_id == "weak")
    assert ReasonCode.DUPLICATE_PLAN in weak_result.reason_codes


def test_dedupe_prefers_stronger_evidence_over_larger_saved_actions():
    """Regresyon: aynı (mode, destination, target)'a iki farklı family düşüp dedupe olduğunda,
    nadir ama tesadüfen bir adım fazla tasarruf eden varyant, çok daha sık/tutarlı gözlenen
    varyantı ezmemeli. Gerçekçi LearnLoop probu bunu tam tersi (saved_actions önce) sırayla
    üretmişti: 3 occurrence'lık bir bildirim-molası yolu (saved=3), 12 occurrence'lık temiz
    yolu (saved=2) deduped ediyordu."""

    common = _candidate(
        "common_path",
        observed=3,
        planned=1,
        saved_days=12,
        saved_sessions=12,
        supporting_occurrences=12,
    )
    detour = _candidate(
        "rare_detour",
        observed=4,
        planned=1,
        saved_days=3,
        saved_sessions=3,
        supporting_occurrences=3,
    )
    results = select([common, detour], "proj", "subj")

    assert _outcome(results, "common_path") == SelectionOutcome.SELECTED
    assert _outcome(results, "rare_detour") == SelectionOutcome.DEDUPED


def test_different_targets_are_never_deduped():
    first = _candidate("i1", target="item_1", destination_screen="detail")
    second = _candidate("i2", target="item_2", destination_screen="detail")
    results = select([first, second], "proj", "subj")

    assert _outcome(results, "i1") == SelectionOutcome.SELECTED
    assert _outcome(results, "i2") == SelectionOutcome.SELECTED
