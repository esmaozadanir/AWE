"""Subject'e ait suggestion'ların dışa sunulacak görünümü ve dismiss akışı (bölüm 97)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.config.engine_config import LifecycleConfig
from awe.lifecycle import dismiss as dismiss_lifecycle
from awe.persistence.models import PlanCandidateRecord, SuggestionRecord
from awe.persistence.repository import (
    fetch_plan_candidate,
    fetch_suggestion_by_key,
    list_suggestions,
)

_VISIBLE_STATES = {"active", "stale", "eligible"}


@dataclass(frozen=True, slots=True)
class PlanView:
    plan_id: str
    plan_type: str
    """Kullanıcıya sunulacak fiili tip: Risk tarafından DOWNGRADE_TO_NAVIGATE kararı verilmiş
    bir PREFILL adayı burada 'navigate' olarak görünür ve binding'leri taşınmaz."""
    anchor_symbol: list[str]
    anchor_screen: str | None
    bindings: list[dict]
    target_binding: dict | None
    risk_decision: str
    benefit_median_saved_actions: float


@dataclass(frozen=True, slots=True)
class SuggestionView:
    suggestion_key: str
    project_id: str
    subject_id: str
    state: str
    reason_codes: list[str]
    primary_plan: PlanView
    fallback_plans: list[PlanView]
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


def _to_plan_view(record: PlanCandidateRecord) -> PlanView:
    effective_type = "navigate" if record.risk_decision == "downgrade_to_navigate" else record.plan_type
    bindings = record.bindings if effective_type == "prefill" else []
    return PlanView(
        plan_id=record.plan_key,
        plan_type=effective_type,
        anchor_symbol=record.anchor["symbol"],
        anchor_screen=record.anchor["screen"],
        bindings=bindings,
        target_binding=record.target_binding,
        risk_decision=record.risk_decision,
        benefit_median_saved_actions=record.benefit_median,
    )


def _to_suggestion_view(session: Session, record: SuggestionRecord) -> SuggestionView:
    primary = fetch_plan_candidate(session, record.primary_plan_id)
    assert primary is not None
    fallback_records = [fetch_plan_candidate(session, pid) for pid in record.fallback_plan_ids]
    return SuggestionView(
        suggestion_key=record.suggestion_key,
        project_id=record.project_id,
        subject_id=record.subject_id,
        state=record.state,
        reason_codes=record.reason_codes,
        primary_plan=_to_plan_view(primary),
        fallback_plans=[_to_plan_view(p) for p in fallback_records if p is not None],
        created_at=record.created_at,
        updated_at=record.updated_at,
        dismissed_at=record.dismissed_at,
    )


def list_subject_suggestions(session: Session, project_id: str, subject_id: str) -> list[SuggestionView]:
    records = list_suggestions(session, project_id, subject_id, states=_VISIBLE_STATES)
    return [_to_suggestion_view(session, record) for record in records]


def dismiss_suggestion(
    session: Session, project_id: str, subject_id: str, suggestion_key: str, now: datetime, config: LifecycleConfig
) -> SuggestionView | None:
    record = fetch_suggestion_by_key(session, suggestion_key)
    if record is None or record.project_id != project_id or record.subject_id != subject_id:
        return None

    state, cooldown_until = dismiss_lifecycle(now, config)
    record.state = state.value
    record.dismissed_at = now
    record.dismiss_cooldown_until = cooldown_until
    record.updated_at = now
    session.flush()
    return _to_suggestion_view(session, record)
