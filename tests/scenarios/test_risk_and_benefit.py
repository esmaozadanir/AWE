"""Bölüm 118-119'daki Risk ve Benefit test matrislerinin uçtan uca doğrulaması."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.benefit import evaluate_benefit
from awe.config import default_engine_config
from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationStatus,
    PlanType,
    ReasonCode,
    RiskDecisionType,
)
from awe.domain.plan import PlanCandidate, ShortcutAnchor
from awe.planner import build_plan_candidates
from awe.risk import ResolverContract, evaluate_risk
from tests.support.builders import StepSpec, build_family_from_steps

_CONFIG = default_engine_config()
_BASE = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
_STABLE_TARGET = "contact_1"


def _standard_occurrence(*, amount: str, target: str | None = _STABLE_TARGET) -> list[StepSpec]:
    return [
        StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
        StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=target),
        StepSpec(action_key="enter_amount", effect=ObservationEffect.INPUT, parameters={"amount": amount}),
        StepSpec(action_key="review_submit", effect=ObservationEffect.CONFIRM),
    ]


def _candidates(occurrences, *, count=7):
    family, series = build_family_from_steps(
        [_standard_occurrence(amount="100") for _ in range(count)] if occurrences is None else occurrences,
        _CONFIG,
        base_time=_BASE,
    )
    plans = build_plan_candidates(family, series, _CONFIG.planner, _CONFIG.risk)
    return family, series, plans


def _navigate(plans: list[PlanCandidate]) -> PlanCandidate:
    return next(c for c in plans if c.plan_type == PlanType.NAVIGATE)


def _deepest_prefill(plans: list[PlanCandidate]) -> PlanCandidate:
    return max((c for c in plans if c.plan_type == PlanType.PREFILL), key=lambda c: c.anchor.core_position)


def test_safe_navigate_with_enough_evidence_is_allowed():
    family, series, plans = _candidates(None, count=7)

    result = evaluate_risk(
        _navigate(plans), family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.ALLOW


def test_resolver_without_navigate_support_blocks_navigate_plan():
    family, series, plans = _candidates(None, count=7)
    resolver = ResolverContract(supports_navigate=False)

    result = evaluate_risk(_navigate(plans), family, series, resolver, _CONFIG.planner, _CONFIG.risk)

    assert result.decision == RiskDecisionType.BLOCK
    assert ReasonCode.RESOLVER_UNSUPPORTED in result.reason_codes


def test_small_sample_requires_review_even_when_evidence_is_stable():
    family, series, plans = _candidates(None, count=2)

    result = evaluate_risk(
        _navigate(plans), family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.ALLOW_WITH_REVIEW
    assert ReasonCode.REVIEW_REQUIRED in result.reason_codes


def test_stable_prefill_with_enough_evidence_is_allowed_without_review():
    family, series, plans = _candidates(None, count=8)

    result = evaluate_risk(
        _deepest_prefill(plans), family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.ALLOW


def test_stable_target_with_variable_amount_only_reduces_bindings():
    occurrences = [_standard_occurrence(amount=str(100 + i)) for i in range(8)]
    family, series, plans = _candidates(occurrences)

    result = evaluate_risk(
        _deepest_prefill(plans), family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.REDUCE_BINDINGS
    assert "amount" in result.reduced_bindings


def test_unstable_target_downgrades_prefill_to_navigate():
    occurrences = [
        _standard_occurrence(amount="100", target=f"contact_{i}")
        for i in range(7)
    ]
    family, series, plans = _candidates(occurrences)

    result = evaluate_risk(
        _deepest_prefill(plans), family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.DOWNGRADE_TO_NAVIGATE
    assert ReasonCode.PREFILL_DOWNGRADED in result.reason_codes


def test_runtime_validation_failure_blocks_the_plan():
    family, series, plans = _candidates(None, count=7)

    result = evaluate_risk(
        _navigate(plans),
        family,
        series,
        ResolverContract.permissive(),
        _CONFIG.planner,
        _CONFIG.risk,
        runtime_validation_passed=False,
    )

    assert result.decision == RiskDecisionType.BLOCK
    assert ReasonCode.RUNTIME_VALIDATION_FAILED in result.reason_codes


def test_high_failure_rate_requires_review_even_when_otherwise_safe():
    occurrences = [
        _standard_occurrence(amount="100")[:3]
        + [StepSpec(action_key="review_submit", effect=ObservationEffect.SUBMIT, status=ObservationStatus.FAIL)]
        for _ in range(7)
    ]
    family, series, plans = _candidates(occurrences)

    result = evaluate_risk(
        _navigate(plans), family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.ALLOW_WITH_REVIEW
    assert ReasonCode.REVIEW_REQUIRED in result.reason_codes


def test_execute_like_effect_is_hard_blocked_regardless_of_evidence_quality():
    family, series, _ = _candidates(None, count=7)
    confirm_anchor = ShortcutAnchor(symbol=("review_submit", "confirm"), screen=None, core_position=3)
    candidate = PlanCandidate(
        plan_id="manual-confirm-anchor",
        family_id=family.family_id,
        plan_type=PlanType.NAVIGATE,
        anchor=confirm_anchor,
        bindings=(),
        target_binding=None,
        supporting_occurrences=7,
    )

    result = evaluate_risk(
        candidate, family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )

    assert result.decision == RiskDecisionType.BLOCK
    assert ReasonCode.EXECUTE_BLOCKED in result.reason_codes


def test_high_benefit_cannot_override_a_risk_block():
    family, series, _ = _candidates(None, count=7)
    confirm_anchor = ShortcutAnchor(symbol=("review_submit", "confirm"), screen=None, core_position=3)
    candidate = PlanCandidate(
        plan_id="manual-confirm-anchor",
        family_id=family.family_id,
        plan_type=PlanType.NAVIGATE,
        anchor=confirm_anchor,
        bindings=(),
        target_binding=None,
        supporting_occurrences=7,
    )

    risk_result = evaluate_risk(
        candidate, family, series, ResolverContract.permissive(), _CONFIG.planner, _CONFIG.risk
    )
    benefit_result = evaluate_benefit(candidate, series, _CONFIG.benefit)

    assert benefit_result.median_saved_actions >= _CONFIG.benefit.min_median_saved_actions
    assert risk_result.decision == RiskDecisionType.BLOCK, "yuksek Benefit BLOCK karari uzerine yazamaz (bolum 90)"


def test_benefit_counts_only_meaningful_user_actions_not_system_noise():
    occurrences = [
        [
            StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
            StepSpec(action_key="spinner", effect=ObservationEffect.ROUTE, role=ObservationRole.NOISE),
            StepSpec(action_key="page_view", effect=ObservationEffect.ROUTE, role=ObservationRole.CONTEXT),
            StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=_STABLE_TARGET),
            StepSpec(action_key="redirect", effect=ObservationEffect.ROUTE, role=ObservationRole.NOISE),
            StepSpec(action_key="review_submit", effect=ObservationEffect.SUBMIT),
        ]
        for _ in range(6)
    ]
    family, series = build_family_from_steps(occurrences, _CONFIG, base_time=_BASE)
    plans = build_plan_candidates(family, series, _CONFIG.planner, _CONFIG.risk)
    deepest = max((c for c in plans if c.plan_type == PlanType.PREFILL), key=lambda c: c.anchor.core_position)

    result = evaluate_benefit(deepest, series, _CONFIG.benefit)

    # role=action olan yalnızca open_form ve select_recipient'tir; noise/context sayılmaz.
    assert result.median_saved_actions == 2.0


def test_misclick_detour_does_not_inflate_benefit():
    with_detour = [
        StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
        StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=_STABLE_TARGET),
        StepSpec(action_key="wrong_screen", effect=ObservationEffect.ROUTE),
        StepSpec(action_key="back_button", effect=ObservationEffect.NAVIGATE_BACK),
        StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=_STABLE_TARGET),
        StepSpec(action_key="review_submit", effect=ObservationEffect.SUBMIT),
    ]
    clean = [
        StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
        StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=_STABLE_TARGET),
        StepSpec(action_key="review_submit", effect=ObservationEffect.SUBMIT),
    ]
    occurrences = [with_detour] + [clean for _ in range(6)]
    family, series = build_family_from_steps(occurrences, _CONFIG, base_time=_BASE)
    plans = build_plan_candidates(family, series, _CONFIG.planner, _CONFIG.risk)
    deepest = max((c for c in plans if c.plan_type == PlanType.PREFILL), key=lambda c: c.anchor.core_position)

    result = evaluate_benefit(deepest, series, _CONFIG.benefit)

    assert result.median_saved_actions == 2.0
    assert result.p75_saved_actions == 2.0


def test_low_median_benefit_does_not_meet_minimum():
    occurrences = [
        [
            StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
            StepSpec(action_key="review_submit", effect=ObservationEffect.SUBMIT),
        ]
        for _ in range(6)
    ]
    family, series = build_family_from_steps(occurrences, _CONFIG, base_time=_BASE)
    plans = build_plan_candidates(family, series, _CONFIG.planner, _CONFIG.risk)
    navigate = _navigate(plans)

    result = evaluate_benefit(navigate, series, _CONFIG.benefit)

    assert result.median_saved_actions < _CONFIG.benefit.min_median_saved_actions
    assert result.meets_minimum is False
