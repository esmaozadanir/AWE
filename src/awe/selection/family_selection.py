"""Family içi dominance ve fallback zinciri seçimi (bölüm 91, 83).

Bu katman Habit/Risk/Benefit hesaplarını tekrar etmez; yalnızca önceki katmanlardan gelen
sonuçlar arasında birincil planı ve güvenli fallback zincirini belirler. Bir PREFILL adayı
Risk tarafından `DOWNGRADE_TO_NAVIGATE` olarak işaretlenmişse, bu seçim aşamasında fiilen bir
NAVIGATE adayı gibi değerlendirilir (bölüm 83'teki "PREFILL kaybolmasın, güvenli olana düşsün"
prensibi).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import FieldState, PlanType, RiskDecisionType
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskDecisionResult

_SURVIVING_DECISIONS = (
    RiskDecisionType.ALLOW,
    RiskDecisionType.ALLOW_WITH_REVIEW,
    RiskDecisionType.REDUCE_BINDINGS,
    RiskDecisionType.DOWNGRADE_TO_NAVIGATE,
)


@dataclass(frozen=True, slots=True)
class EvaluatedCandidate:
    candidate: PlanCandidate
    risk: RiskDecisionResult
    benefit: BenefitEvidence


@dataclass(frozen=True, slots=True)
class FamilySelection:
    primary: EvaluatedCandidate
    fallback_plan_ids: tuple[str, ...]
    dominated_plan_ids: frozenset[str]


def _effective_navigate_position(item: EvaluatedCandidate) -> int | None:
    if item.risk.decision not in _SURVIVING_DECISIONS:
        return None
    if item.candidate.plan_type == PlanType.NAVIGATE:
        return item.candidate.anchor.core_position
    if item.risk.decision == RiskDecisionType.DOWNGRADE_TO_NAVIGATE:
        return item.candidate.anchor.core_position
    return None


def _is_true_prefill(item: EvaluatedCandidate) -> bool:
    return item.candidate.plan_type == PlanType.PREFILL and item.risk.decision in (
        RiskDecisionType.ALLOW,
        RiskDecisionType.ALLOW_WITH_REVIEW,
        RiskDecisionType.REDUCE_BINDINGS,
    )


def _prefill_richness(item: EvaluatedCandidate) -> tuple[int, int, float]:
    stable_bindings = sum(1 for b in item.candidate.bindings if b.state == FieldState.STABLE)
    return (stable_bindings, item.candidate.anchor.core_position, item.benefit.median_saved_actions)


def select_family_plan(evaluated: list[EvaluatedCandidate]) -> FamilySelection | None:
    survivors = [
        item
        for item in evaluated
        if item.risk.decision in _SURVIVING_DECISIONS and item.benefit.meets_minimum
    ]
    if not survivors:
        return None

    dominated: set[str] = set()

    navigate_pool = [item for item in survivors if _effective_navigate_position(item) is not None]
    primary_navigate: EvaluatedCandidate | None = None
    if navigate_pool:
        navigate_pool.sort(key=lambda item: _effective_navigate_position(item) or 0, reverse=True)
        primary_navigate = navigate_pool[0]
        dominated.update(item.candidate.plan_id for item in navigate_pool[1:])

    prefill_pool = [item for item in survivors if _is_true_prefill(item)]
    primary_prefill: EvaluatedCandidate | None = None
    if prefill_pool:
        prefill_pool.sort(key=_prefill_richness, reverse=True)
        primary_prefill = prefill_pool[0]
        dominated.update(item.candidate.plan_id for item in prefill_pool[1:])

    if primary_prefill is not None:
        primary = primary_prefill
        fallback = (
            (primary_navigate.candidate.plan_id,)
            if primary_navigate is not None
            and primary_navigate.candidate.plan_id != primary_prefill.candidate.plan_id
            else ()
        )
    elif primary_navigate is not None:
        primary = primary_navigate
        fallback = ()
    else:
        return None

    dominated.discard(primary.candidate.plan_id)
    for plan_id in fallback:
        dominated.discard(plan_id)

    return FamilySelection(primary=primary, fallback_plan_ids=fallback, dominated_plan_ids=frozenset(dominated))
