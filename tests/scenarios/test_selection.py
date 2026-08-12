"""Bölüm 120'deki Final Selection test matrisinin doğrulaması.

Bu katman Habit/Risk/Benefit hesaplarını tekrar etmediği için testler doğrudan zaten
hesaplanmış `RiskDecisionResult`/`BenefitEvidence` nesneleri besler; yalnızca dominance,
fallback zinciri ve cross-family dedupe mantığını doğrular.
"""

from __future__ import annotations

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import EffectPolicy, FieldState, PlanType, RiskDecisionType
from awe.domain.plan import FieldBinding, PlanCandidate, ShortcutAnchor
from awe.domain.risk import RiskDecisionResult, RiskEvidence
from awe.selection import EvaluatedCandidate, FamilyPlan, dedupe_across_families, select_family_plan

_NEUTRAL_EVIDENCE = RiskEvidence(
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


def _plan(
    plan_id: str, plan_type: PlanType, core_position: int, bindings: tuple[FieldBinding, ...] = ()
) -> PlanCandidate:
    anchor = ShortcutAnchor(
        symbol=(f"action{core_position}", "route"), screen=None, core_position=core_position
    )
    return PlanCandidate(
        plan_id=plan_id,
        family_id="fam1",
        plan_type=plan_type,
        anchor=anchor,
        bindings=bindings,
        target_binding=None,
        supporting_occurrences=10,
    )


def _risk(plan_id: str, decision: RiskDecisionType) -> RiskDecisionResult:
    return RiskDecisionResult(plan_id=plan_id, decision=decision, evidence=_NEUTRAL_EVIDENCE, reason_codes=())


def _benefit(plan_id: str, median: float, meets_minimum: bool = True) -> BenefitEvidence:
    return BenefitEvidence(
        plan_id=plan_id,
        median_saved_actions=median,
        p25_saved_actions=median,
        p75_saved_actions=median,
        benefit_coverage=1.0,
        sample_size=10,
        meets_minimum=meets_minimum,
    )


def _evaluated(plan_id, plan_type, core_position, decision, median, bindings=()):
    return EvaluatedCandidate(
        candidate=_plan(plan_id, plan_type, core_position, bindings),
        risk=_risk(plan_id, decision),
        benefit=_benefit(plan_id, median),
    )


def test_deepest_navigate_dominates_shallower_navigate_candidates():
    shallow = _evaluated("nav-early", PlanType.NAVIGATE, 0, RiskDecisionType.ALLOW, 3.0)
    deep = _evaluated("nav-deep", PlanType.NAVIGATE, 2, RiskDecisionType.ALLOW, 3.0)

    selection = select_family_plan([shallow, deep])

    assert selection is not None
    assert selection.primary.candidate.plan_id == "nav-deep"
    assert selection.dominated_plan_ids == {"nav-early"}


def test_prefill_is_preferred_as_primary_with_navigate_as_fallback():
    navigate = _evaluated("nav", PlanType.NAVIGATE, 0, RiskDecisionType.ALLOW, 2.0)
    stable_binding = FieldBinding("recipient", FieldState.STABLE, "contact_1", 1.0, 1.0, 10, 1.0)
    prefill = _evaluated("prefill", PlanType.PREFILL, 2, RiskDecisionType.ALLOW, 4.0, (stable_binding,))

    selection = select_family_plan([navigate, prefill])

    assert selection is not None
    assert selection.primary.candidate.plan_id == "prefill"
    assert selection.fallback_plan_ids == ("nav",)


def test_no_surviving_candidates_yields_no_selection():
    blocked = _evaluated("nav", PlanType.NAVIGATE, 0, RiskDecisionType.BLOCK, 5.0)
    low_benefit = EvaluatedCandidate(
        candidate=_plan("prefill", PlanType.PREFILL, 1),
        risk=_risk("prefill", RiskDecisionType.ALLOW),
        benefit=_benefit("prefill", 0.5, meets_minimum=False),
    )

    selection = select_family_plan([blocked, low_benefit])

    assert selection is None


def test_downgraded_prefill_competes_in_the_navigate_pool():
    downgraded = _evaluated("prefill-downgraded", PlanType.PREFILL, 2, RiskDecisionType.DOWNGRADE_TO_NAVIGATE, 3.0)
    shallow_navigate = _evaluated("nav-shallow", PlanType.NAVIGATE, 0, RiskDecisionType.ALLOW, 3.0)

    selection = select_family_plan([downgraded, shallow_navigate])

    assert selection is not None
    assert selection.primary.candidate.plan_id == "prefill-downgraded"
    assert selection.dominated_plan_ids == {"nav-shallow"}


def test_cross_family_duplicate_keeps_the_higher_benefit_plan():
    # İki farklı family'nin birincil planı aynı yapısal anchor sembolüne ((action1, route))
    # düşüyor; yalnızca daha yüksek Benefit'e sahip olan tutulur, diğeri DUPLICATE_PLAN olur.
    family_a = FamilyPlan(
        family_id="famA",
        selection=select_family_plan([_evaluated("planA", PlanType.NAVIGATE, 1, RiskDecisionType.ALLOW, 3.0)]),
    )
    family_b = FamilyPlan(
        family_id="famB",
        selection=select_family_plan([_evaluated("planB", PlanType.NAVIGATE, 1, RiskDecisionType.ALLOW, 6.0)]),
    )

    kept, duplicate_ids = dedupe_across_families([family_a, family_b])

    assert [plan.family_id for plan in kept] == ["famB"]
    assert duplicate_ids == {"planA"}


def test_four_independent_families_all_remain_eligible_without_artificial_cap():
    # Her family yapısal olarak farklı bir anchor'a (farklı core_position -> farklı sembol)
    # sahip olduğu için dört bağımsız Habit, engine seviyesinde sabit bir üst sınırla
    # kesilmeden dördü de eligible kalmalıdır (bölüm 92).
    plans = [
        FamilyPlan(
            family_id=f"fam{i}",
            selection=select_family_plan(
                [
                    EvaluatedCandidate(
                        candidate=_plan(f"plan{i}", PlanType.NAVIGATE, i),
                        risk=_risk(f"plan{i}", RiskDecisionType.ALLOW),
                        benefit=_benefit(f"plan{i}", 3.0),
                    )
                ]
            ),
        )
        for i in range(4)
    ]

    kept, duplicate_ids = dedupe_across_families(plans)

    assert len(kept) == 4
    assert not duplicate_ids
