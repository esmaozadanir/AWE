"""Selector (bölüm 6.15): upstream kararları tekrar hesaplamaz, tek final skor üretmez.

MVP yüksek-precision politikası nedeniyle `LIMITED` dahil `CLEAR` dışındaki Benefit seviyeleri
reddedilir. Weak Anchor yalnızca mode=NAVIGATE + Risk=ALLOW + Benefit=CLEAR koşullarının
tamamında eligible olabilir (bir WEAK anchor, target taşıyan hiçbir pozisyon olmadığı için
zaten yalnızca NAVIGATE üretebilir — bkz. `awe.planner.anchors` — bu kontrol savunma amaçlıdır).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    BenefitLevel,
    HabitDecision,
    IntentState,
    PlanMode,
    ReasonCode,
    RiskDecision,
    SelectionOutcome,
)
from awe.domain.habit import HabitAssessment
from awe.domain.plan import Scope, ShortcutIntent
from awe.domain.risk import RiskAssessment
from awe.domain.suggestion import SelectionResult

_STRENGTH_RANK = {AnchorStrength.STRONG: 2, AnchorStrength.MEDIUM: 1, AnchorStrength.WEAK: 0}


@dataclass(frozen=True, slots=True)
class Candidate:
    """Selector'ın işlediği tek birim: bir intent'in tüm upstream sonuçlarıyla birlikte hali."""

    intent: ShortcutIntent
    scope: Scope
    habit: HabitAssessment
    risk: RiskAssessment
    benefit: BenefitEvidence


def _is_eligible(candidate: Candidate) -> bool:
    if candidate.habit.decision != HabitDecision.HABIT_DETECTED or candidate.habit.evidence is None:
        return False
    if candidate.intent.state != IntentState.READY:
        return False
    if candidate.intent.anchor.status != AnchorStatus.RESOLVED:
        return False
    if candidate.risk.decision != RiskDecision.ALLOW:
        return False
    if candidate.benefit.level != BenefitLevel.CLEAR:
        return False
    if candidate.intent.anchor.strength == AnchorStrength.WEAK:
        return candidate.intent.mode == PlanMode.NAVIGATE
    return True


def _dedupe_key(candidate: Candidate, project_id: str, subject_id: str) -> tuple:
    mapping_versions = frozenset(symbol[3] for symbol in candidate.scope.included)
    intent = candidate.intent
    return (
        project_id,
        subject_id,
        mapping_versions,
        intent.mode,
        intent.destination_screen,
        intent.target,
        intent.requires_user_confirmation,
        intent.automatic_action,
        intent.final_action_owner,
    )


def _ranking_key(candidate: Candidate) -> tuple:
    evidence = candidate.habit.evidence
    assert evidence is not None  # eligibility already guarantees this
    return (
        -_STRENGTH_RANK[candidate.intent.anchor.strength],
        -candidate.benefit.saved_actions,
        -evidence.distinct_days,
        -evidence.distinct_sessions,
        -candidate.intent.supporting_occurrences,
        candidate.intent.intent_id,
    )


def select(candidates: list[Candidate], project_id: str, subject_id: str) -> list[SelectionResult]:
    results: list[SelectionResult] = []
    dedupe_groups: dict[tuple, list[Candidate]] = defaultdict(list)

    for candidate in candidates:
        if not _is_eligible(candidate):
            reasons = (
                candidate.risk.reason_codes or candidate.intent.reason_codes or (ReasonCode.NO_PLAN_CANDIDATE,)
            )
            results.append(
                SelectionResult(
                    intent_id=candidate.intent.intent_id, outcome=SelectionOutcome.REJECTED, reason_codes=reasons
                )
            )
            continue
        dedupe_groups[_dedupe_key(candidate, project_id, subject_id)].append(candidate)

    for group in dedupe_groups.values():
        ranked = sorted(group, key=_ranking_key)
        winner = ranked[0]
        results.append(SelectionResult(intent_id=winner.intent.intent_id, outcome=SelectionOutcome.SELECTED))
        for loser in ranked[1:]:
            results.append(
                SelectionResult(
                    intent_id=loser.intent.intent_id,
                    outcome=SelectionOutcome.DEDUPED,
                    reason_codes=(ReasonCode.DUPLICATE_PLAN,),
                )
            )

    return results
