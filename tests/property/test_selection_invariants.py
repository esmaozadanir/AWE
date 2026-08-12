"""Bölüm 123: property-based invariant testleri — Risk veto ve suggestion sayısı üst sınırı yok."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import EffectPolicy, PlanType, RiskDecisionType
from awe.domain.plan import PlanCandidate, ShortcutAnchor
from awe.domain.risk import RiskDecisionResult, RiskEvidence
from awe.selection import EvaluatedCandidate, FamilyPlan, dedupe_across_families, select_family_plan

_NEUTRAL_EVIDENCE = RiskEvidence(
    effect_policy=EffectPolicy.BLOCKED,
    anchor_coverage=1.0,
    state_confidence=1.0,
    target_dominance=None,
    target_coverage=None,
    binding_dominance=None,
    binding_coverage=None,
    sample_size=10,
    recent_drift=False,
    completion_rate=1.0,
    failure_rate=0.0,
    cancel_rate=0.0,
    resolver_supported=True,
    requires_review=False,
    runtime_validation_passed=None,
    data_quality_score=1.0,
    family_ambiguous=False,
    family_cohesion=1.0,
)


def _blocked_candidate() -> PlanCandidate:
    return PlanCandidate(
        plan_id="blocked-plan",
        family_id="fam1",
        plan_type=PlanType.NAVIGATE,
        anchor=ShortcutAnchor(symbol=("confirm_action", "confirm"), screen=None, core_position=0),
        bindings=(),
        target_binding=None,
        supporting_occurrences=10,
    )


@given(median_saved_actions=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=50)
def test_risk_block_is_never_reopened_by_an_arbitrarily_high_benefit(median_saved_actions):
    candidate = _blocked_candidate()
    risk = RiskDecisionResult(
        plan_id=candidate.plan_id, decision=RiskDecisionType.BLOCK, evidence=_NEUTRAL_EVIDENCE, reason_codes=()
    )
    benefit = BenefitEvidence(
        plan_id=candidate.plan_id,
        median_saved_actions=median_saved_actions,
        p25_saved_actions=median_saved_actions,
        p75_saved_actions=median_saved_actions,
        benefit_coverage=1.0,
        sample_size=10,
        meets_minimum=True,
    )

    selection = select_family_plan([EvaluatedCandidate(candidate=candidate, risk=risk, benefit=benefit)])

    assert selection is None, "Risk BLOCK, ne kadar yuksek olursa olsun Benefit tarafindan acilamaz (bolum 90)"


def _make_evaluated(index: int) -> EvaluatedCandidate:
    candidate = PlanCandidate(
        plan_id=f"plan{index}",
        family_id=f"fam{index}",
        plan_type=PlanType.NAVIGATE,
        anchor=ShortcutAnchor(symbol=(f"distinct_action_{index}", "route"), screen=None, core_position=0),
        bindings=(),
        target_binding=None,
        supporting_occurrences=10,
    )
    evidence = RiskEvidence(
        effect_policy=EffectPolicy.SAFE,
        anchor_coverage=1.0,
        state_confidence=1.0,
        target_dominance=None,
        target_coverage=None,
        binding_dominance=None,
        binding_coverage=None,
        sample_size=10,
        recent_drift=False,
        completion_rate=1.0,
        failure_rate=0.0,
        cancel_rate=0.0,
        resolver_supported=True,
        requires_review=False,
        runtime_validation_passed=None,
        data_quality_score=1.0,
        family_ambiguous=False,
        family_cohesion=1.0,
    )
    risk = RiskDecisionResult(
        plan_id=candidate.plan_id, decision=RiskDecisionType.ALLOW, evidence=evidence, reason_codes=()
    )
    benefit = BenefitEvidence(
        plan_id=candidate.plan_id,
        median_saved_actions=3.0,
        p25_saved_actions=3.0,
        p75_saved_actions=3.0,
        benefit_coverage=1.0,
        sample_size=10,
        meets_minimum=True,
    )
    return EvaluatedCandidate(candidate=candidate, risk=risk, benefit=benefit)


@given(independent_habit_count=st.integers(min_value=1, max_value=12))
@settings(max_examples=30)
def test_engine_never_applies_a_hard_cap_on_the_number_of_eligible_suggestions(independent_habit_count):
    family_plans = []
    for index in range(independent_habit_count):
        evaluated = _make_evaluated(index)
        selection = select_family_plan([evaluated])
        assert selection is not None
        family_plans.append(FamilyPlan(family_id=f"fam{index}", selection=selection))

    kept, duplicate_ids = dedupe_across_families(family_plans)

    assert len(kept) == independent_habit_count
    assert not duplicate_ids
