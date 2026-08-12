"""Risk kararı: PlanCandidate güvenli mi (bölüm 79-83).

Karar önceliği: BLOCK > DOWNGRADE_TO_NAVIGATE > REDUCE_BINDINGS > ALLOW_WITH_REVIEW > ALLOW.
Hiçbir Benefit değeri, burada verilen BLOCK kararını geçersiz kılamaz (bölüm 90) — bu fonksiyon
Benefit'i hiç görmez, invariant çağıran katmanın Benefit'i Risk'ten sonra ve ondan bağımsız
uygulamasıyla korunur.
"""

from __future__ import annotations

import dataclasses

from awe.config.engine_config import PlannerConfig, RiskConfig
from awe.domain.enums import EffectPolicy, FieldState, PlanType, ReasonCode, RiskDecisionType
from awe.domain.family import BehaviorFamily
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskDecisionResult, RiskEvidence
from awe.domain.series import OSeries
from awe.risk.evidence import build_risk_evidence
from awe.risk.resolver import ResolverContract

_SEVERITY = {
    RiskDecisionType.ALLOW: 0,
    RiskDecisionType.ALLOW_WITH_REVIEW: 1,
    RiskDecisionType.REDUCE_BINDINGS: 2,
    RiskDecisionType.DOWNGRADE_TO_NAVIGATE: 3,
    RiskDecisionType.BLOCK: 4,
}


def _hard_block_reasons(
    evidence: RiskEvidence, runtime_validation_passed: bool | None
) -> tuple[ReasonCode, ...]:
    reasons = []
    if evidence.effect_policy == EffectPolicy.BLOCKED:
        reasons.append(ReasonCode.EXECUTE_BLOCKED)
    if not evidence.resolver_supported:
        reasons.append(ReasonCode.RESOLVER_UNSUPPORTED)
    if runtime_validation_passed is False:
        reasons.append(ReasonCode.RUNTIME_VALIDATION_FAILED)
    return tuple(reasons)


def evaluate_risk(
    candidate: PlanCandidate,
    family: BehaviorFamily,
    member_series: list[OSeries],
    resolver: ResolverContract,
    planner_config: PlannerConfig,
    risk_config: RiskConfig,
    *,
    runtime_validation_passed: bool | None = None,
) -> RiskDecisionResult:
    evidence = build_risk_evidence(candidate, family, member_series, resolver, planner_config, risk_config)
    if runtime_validation_passed is not None:
        evidence = dataclasses.replace(evidence, runtime_validation_passed=runtime_validation_passed)

    decision = RiskDecisionType.ALLOW
    reasons: list[ReasonCode] = []
    reduced_fields: list[str] = []

    def escalate(candidate_decision: RiskDecisionType, *reason_codes: ReasonCode) -> None:
        nonlocal decision
        if _SEVERITY[candidate_decision] > _SEVERITY[decision]:
            decision = candidate_decision
        reasons.extend(reason_codes)

    hard_block_reasons = _hard_block_reasons(evidence, runtime_validation_passed)
    if hard_block_reasons:
        escalate(RiskDecisionType.BLOCK, *hard_block_reasons)
        return RiskDecisionResult(
            plan_id=candidate.plan_id,
            decision=decision,
            evidence=evidence,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    if candidate.plan_type == PlanType.PREFILL:
        target = candidate.target_binding
        if target is not None and target.state != FieldState.STABLE:
            unstable_reason = (
                ReasonCode.UNKNOWN_TARGET if target.state == FieldState.UNKNOWN else ReasonCode.UNSTABLE_TARGET
            )
            escalate(RiskDecisionType.DOWNGRADE_TO_NAVIGATE, unstable_reason, ReasonCode.PREFILL_DOWNGRADED)
        else:
            # Target zaten stabil (ya da bu akışta hiç yoksa) — bu tek başına prefill'i
            # değerli kılmaya yeter (bölüm 117: "target stable + amount variable"). Yalnızca
            # ne target ne de HİÇBİR parametre stabilse prefill'in kazandıracağı bir şey
            # kalmaz ve NAVIGATE'e düşülür; aksi halde yalnızca stabil olmayan alanlar
            # düşürülür (REDUCE_BINDINGS).
            unstable = [b for b in candidate.bindings if b.state != FieldState.STABLE]
            stable = [b for b in candidate.bindings if b.state == FieldState.STABLE]
            target_is_usable = target is not None and target.state == FieldState.STABLE
            if unstable and not stable and not target_is_usable:
                escalate(
                    RiskDecisionType.DOWNGRADE_TO_NAVIGATE,
                    ReasonCode.LOW_BINDING_COVERAGE,
                    ReasonCode.PREFILL_DOWNGRADED,
                )
                reduced_fields.extend(b.field_name for b in unstable)
            elif unstable:
                escalate(
                    RiskDecisionType.REDUCE_BINDINGS,
                    ReasonCode.LOW_BINDING_COVERAGE,
                    ReasonCode.PREFILL_REDUCED,
                )
                reduced_fields.extend(b.field_name for b in unstable)

        if resolver.accepted_bindings is not None:
            rejected = [
                b.field_name for b in candidate.bindings if b.field_name not in resolver.accepted_bindings
            ]
            if rejected:
                escalate(RiskDecisionType.REDUCE_BINDINGS, ReasonCode.PREFILL_REDUCED)
                reduced_fields.extend(rejected)
    else:
        target = candidate.target_binding
        if target is not None and target.state != FieldState.STABLE:
            unstable_reason = (
                ReasonCode.UNKNOWN_TARGET if target.state == FieldState.UNKNOWN else ReasonCode.UNSTABLE_TARGET
            )
            escalate(RiskDecisionType.ALLOW_WITH_REVIEW, unstable_reason, ReasonCode.REVIEW_REQUIRED)

    if evidence.sample_size < risk_config.min_sample_size_for_confidence:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)
    if (
        evidence.failure_rate > risk_config.max_failure_rate_for_allow
        or evidence.cancel_rate > risk_config.max_cancel_rate_for_allow
    ):
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)
    if evidence.data_quality_score < risk_config.min_data_quality_for_allow:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)
    if evidence.family_ambiguous:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.AMBIGUOUS_FAMILY, ReasonCode.REVIEW_REQUIRED)
    elif evidence.family_cohesion < risk_config.min_family_cohesion_for_allow:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.LOW_COHESION, ReasonCode.REVIEW_REQUIRED)
    if resolver.requires_review:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)

    return RiskDecisionResult(
        plan_id=candidate.plan_id,
        decision=decision,
        evidence=evidence,
        reason_codes=tuple(dict.fromkeys(reasons)),
        reduced_bindings=tuple(dict.fromkeys(reduced_fields)),
    )
