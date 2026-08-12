"""PlanCandidate için Risk kanıtının toplanması (bölüm 81)."""

from __future__ import annotations

from awe.config.engine_config import PlannerConfig, RiskConfig
from awe.domain.enums import EffectPolicy, ObservationEffect, ObservationStatus, PlanType
from awe.domain.family import BehaviorFamily
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskEvidence
from awe.domain.series import OSeries
from awe.planner.state_reconstruction import resolve_anchor_step_index
from awe.risk.resolver import ResolverContract


def _drift_detected(candidate: PlanCandidate, planner_config: PlannerConfig) -> bool:
    bindings = list(candidate.bindings)
    if candidate.target_binding is not None:
        bindings.append(candidate.target_binding)
    for binding in bindings:
        if binding.recent_dominance is None:
            continue
        if binding.dominance - binding.recent_dominance >= planner_config.recent_drift_drop_threshold:
            return True
    return False


def build_risk_evidence(
    candidate: PlanCandidate,
    family: BehaviorFamily,
    member_series: list[OSeries],
    resolver: ResolverContract,
    planner_config: PlannerConfig,
    risk_config: RiskConfig,
) -> RiskEvidence:
    anchor_effect = candidate.anchor.symbol[1]
    effect_policy = risk_config.effect_policy.get(ObservationEffect(anchor_effect), EffectPolicy.REVIEW)

    total_family_occurrences = len(family.member_series_ids) or len(member_series)
    anchor_coverage = (
        candidate.supporting_occurrences / total_family_occurrences if total_family_occurrences else 0.0
    )

    coverages = [b.coverage for b in candidate.bindings]
    if candidate.target_binding is not None:
        coverages.append(candidate.target_binding.coverage)
    state_confidence = sum(coverages) / len(coverages) if coverages else 1.0

    binding_dominance = (
        sum(b.dominance for b in candidate.bindings) / len(candidate.bindings)
        if candidate.bindings
        else None
    )
    binding_coverage = (
        sum(b.coverage for b in candidate.bindings) / len(candidate.bindings)
        if candidate.bindings
        else None
    )

    reached = [
        series
        for series in member_series
        if resolve_anchor_step_index(series, candidate.anchor.symbol) is not None
    ]
    total_reached = len(reached) or 1
    completion_rate = sum(1 for s in reached if s.final_status == ObservationStatus.SUCCESS) / total_reached
    failure_rate = sum(1 for s in reached if s.final_status == ObservationStatus.FAIL) / total_reached
    cancel_rate = sum(1 for s in reached if s.final_status == ObservationStatus.CANCEL) / total_reached

    relevant_observations = [
        obs
        for series in reached
        for obs in series.raw_observations[: (resolve_anchor_step_index(series, candidate.anchor.symbol) or 0) + 1]
    ]
    data_quality_score = (
        sum(1.0 if not obs.quality.mapping_warnings else 0.5 for obs in relevant_observations)
        / len(relevant_observations)
        if relevant_observations
        else 1.0
    )

    resolver_supported = (
        resolver.supports_navigate if candidate.plan_type == PlanType.NAVIGATE else resolver.supports_prefill
    )

    return RiskEvidence(
        effect_policy=effect_policy,
        anchor_coverage=anchor_coverage,
        state_confidence=state_confidence,
        target_dominance=candidate.target_binding.dominance if candidate.target_binding else None,
        target_coverage=candidate.target_binding.coverage if candidate.target_binding else None,
        binding_dominance=binding_dominance,
        binding_coverage=binding_coverage,
        sample_size=candidate.supporting_occurrences,
        recent_drift=_drift_detected(candidate, planner_config),
        completion_rate=completion_rate,
        failure_rate=failure_rate,
        cancel_rate=cancel_rate,
        resolver_supported=resolver_supported,
        requires_review=resolver.requires_review,
        runtime_validation_passed=None,
        data_quality_score=data_quality_score,
        family_ambiguous=len(family.ambiguous_series_ids) > 0,
        family_cohesion=family.cohesion,
    )
