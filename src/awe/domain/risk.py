"""Risk Evaluator'ın kanıt ve karar modelleri (bölüm 6.13).

Tek bir skor değil, açıklanabilir bir vektördür. Selector yalnızca `RiskDecision` kapısına
bakar (`ALLOW`/`BLOCK`); vektörün diğer alanları açıklanabilirlik ve loglama içindir.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import EffectPolicy, ExecutionExposure, PlanMode, ReasonCode, RiskDecision


@dataclass(frozen=True, slots=True)
class ReliabilityEvidence:
    completion_rate: float
    failure_rate: float
    cancel_rate: float
    sample_size: int


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    policy: EffectPolicy
    """Anchor'ın effect'i için proje konfigürasyonunun tanımladığı güvenlik sınıfı."""
    plan_surface: PlanMode
    execution_exposure: ExecutionExposure
    interaction_guard_intact: bool
    """`automaticAction=NONE` ve `finalActionOwner=USER` koşulları sağlanıyor mu."""
    observed_goal_sensitivity: EffectPolicy
    """Scope içindeki adımların en hassas (en kısıtlayıcı) effect policy'si — yalnızca
    Anchor'ın kendi effect'i değil, oraya varan tüm gözlenen akış dikkate alınır."""
    reliability: ReliabilityEvidence
    data_quality_ok: bool


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    intent_id: str
    decision: RiskDecision
    evidence: RiskEvidence
    reason_codes: tuple[ReasonCode, ...] = ()
