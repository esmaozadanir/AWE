"""Risk katmanının kanıt ve karar modelleri (bölüm 79-83)."""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import EffectPolicy, ReasonCode, RiskDecisionType


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    effect_policy: EffectPolicy
    anchor_coverage: float
    state_confidence: float

    target_dominance: float | None
    target_coverage: float | None
    binding_dominance: float | None
    binding_coverage: float | None

    sample_size: int
    recent_drift: bool

    completion_rate: float
    failure_rate: float
    cancel_rate: float

    resolver_supported: bool
    requires_review: bool
    runtime_validation_passed: bool | None

    data_quality_score: float
    family_ambiguous: bool
    family_cohesion: float


@dataclass(frozen=True, slots=True)
class RiskDecisionResult:
    plan_id: str
    decision: RiskDecisionType
    evidence: RiskEvidence
    reason_codes: tuple[ReasonCode, ...]
    reduced_bindings: tuple[str, ...] = ()
