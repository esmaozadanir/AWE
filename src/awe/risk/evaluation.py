"""Risk Evaluator (bölüm 6.13): üretilen gerçek Shortcut Intent'i değerlendirir; Anchor
effect'ini otomatik çalıştırdığını varsaymaz. Çıktı tek bir skor değil, açıklanabilir bir
vektördür — Selector yalnızca `RiskDecision.ALLOW`/`BLOCK` kapısına bakar.

MVP kuralları (belgeden birebir): delete bağlamı BLOCK; unknown effect BLOCK; kritik quality
flag BLOCK; unknown anchor status BLOCK; fail/cancel karışımı `MIXED_OBSERVED_OUTCOMES` olarak
korunur ama tek başına BLOCK nedeni değildir. State-changing gözlenen akış, kısayol onu
execute etmediği sürece (ki hiçbir zaman etmez — EXECUTE modu yoktur) otomatik BLOCK edilmez.
"""

from __future__ import annotations

from awe.config.engine_config import RiskConfig
from awe.domain.enums import (
    AutomaticAction,
    EffectPolicy,
    ExecutionExposure,
    FinalActionOwner,
    ObservationEffect,
    ObservationStatus,
    PlanMode,
    ReasonCode,
    RiskDecision,
)
from awe.domain.episode import EpisodeCandidate
from awe.domain.plan import Scope, ShortcutIntent
from awe.domain.risk import ReliabilityEvidence, RiskAssessment, RiskEvidence
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol


def _reliability(
    variant: TargetVariant, anchor_position: int, candidates_by_id: dict[str, EpisodeCandidate]
) -> ReliabilityEvidence:
    statuses = [
        candidates_by_id[occurrence_id].steps[anchor_position].status
        for occurrence_id in variant.occurrence_ids
        if anchor_position < len(candidates_by_id[occurrence_id].steps)
    ]
    sample_size = len(statuses)
    if sample_size == 0:
        return ReliabilityEvidence(completion_rate=0.0, failure_rate=0.0, cancel_rate=0.0, sample_size=0)
    return ReliabilityEvidence(
        completion_rate=statuses.count(ObservationStatus.SUCCESS) / sample_size,
        failure_rate=statuses.count(ObservationStatus.FAIL) / sample_size,
        cancel_rate=statuses.count(ObservationStatus.CANCEL) / sample_size,
        sample_size=sample_size,
    )


def _scope_data_quality_ok(
    variant: TargetVariant,
    scope_length: int,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: RiskConfig,
) -> bool:
    total = 0
    clean = 0
    for occurrence_id in variant.occurrence_ids:
        candidate = candidates_by_id[occurrence_id]
        series = series_by_id[candidate.series_id]
        for step in candidate.steps[:scope_length]:
            observation = series.raw_observations[step.observation_index]
            total += 1
            if (
                not observation.quality.missing_target_field
                and not observation.quality.invalid_duration
                and not observation.quality.warnings
            ):
                clean += 1
    if total == 0:
        return True
    return (clean / total) >= config.min_data_quality_for_allow


def _policy_of(symbol: Symbol, config: RiskConfig) -> EffectPolicy:
    return config.effect_policy.get(ObservationEffect(symbol[1]), EffectPolicy.SENSITIVE)


def _observed_goal_sensitivity(excluded_trailing: tuple[Symbol, ...], config: RiskConfig) -> EffectPolicy:
    """Anchor'dan SONRA gözlenen ama Scope'a (dolayısıyla kısayola) dahil OLMAYAN adımların en
    hassas policy'si — yalnızca açıklanabilirlik: kısayolun neyi kasıtlı olarak dışarıda
    bıraktığını gösterir, kendisi bir BLOCK nedeni değildir."""
    if not excluded_trailing:
        return EffectPolicy.SAFE
    policies = [_policy_of(symbol, config) for symbol in excluded_trailing]
    if EffectPolicy.BLOCKED in policies:
        return EffectPolicy.BLOCKED
    if EffectPolicy.SENSITIVE in policies:
        return EffectPolicy.SENSITIVE
    return EffectPolicy.SAFE


def evaluate_risk(
    intent: ShortcutIntent,
    variant: TargetVariant,
    scope: Scope,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: RiskConfig,
) -> RiskAssessment:
    anchor_effect = intent.anchor.symbol[1]
    anchor_policy = _policy_of(intent.anchor.symbol, config)
    reliability = _reliability(variant, intent.anchor.position, candidates_by_id)
    data_quality_ok = _scope_data_quality_ok(variant, len(scope.included), candidates_by_id, series_by_id, config)
    goal_sensitivity = _observed_goal_sensitivity(scope.excluded_trailing, config)

    reason_codes: list[ReasonCode] = []
    decision = RiskDecision.ALLOW

    if anchor_policy == EffectPolicy.BLOCKED:
        decision = RiskDecision.BLOCK
        is_unknown_effect = anchor_effect == ObservationEffect.UNKNOWN.value
        reason_codes.append(ReasonCode.UNKNOWN_EFFECT if is_unknown_effect else ReasonCode.EXECUTE_BLOCKED_EFFECT)

    if not data_quality_ok:
        decision = RiskDecision.BLOCK
        reason_codes.append(ReasonCode.CRITICAL_QUALITY_FLAG)

    all_unknown_status = (
        reliability.sample_size > 0
        and reliability.completion_rate == 0.0
        and reliability.failure_rate == 0.0
        and reliability.cancel_rate == 0.0
    )
    if all_unknown_status:
        decision = RiskDecision.BLOCK
        reason_codes.append(ReasonCode.UNKNOWN_ANCHOR_STATUS)

    if (
        reliability.failure_rate > config.mixed_outcome_rate_threshold
        or reliability.cancel_rate > config.mixed_outcome_rate_threshold
    ):
        reason_codes.append(ReasonCode.MIXED_OBSERVED_OUTCOMES)

    evidence = RiskEvidence(
        policy=anchor_policy,
        plan_surface=intent.mode if intent.mode is not None else PlanMode.NAVIGATE,
        execution_exposure=ExecutionExposure.NONE,
        interaction_guard_intact=intent.automatic_action == AutomaticAction.NONE
        and intent.final_action_owner == FinalActionOwner.USER,
        observed_goal_sensitivity=goal_sensitivity,
        reliability=reliability,
        data_quality_ok=data_quality_ok,
    )
    return RiskAssessment(
        intent_id=intent.intent_id,
        decision=decision,
        evidence=evidence,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )
