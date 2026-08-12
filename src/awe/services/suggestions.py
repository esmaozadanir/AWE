"""Subject'e ait suggestion'ların dışa sunulacak görünümü ve dismiss akışı."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.config.engine_config import LifecycleConfig
from awe.domain.benefit import BenefitEvidence
from awe.lifecycle import dismiss as dismiss_lifecycle
from awe.persistence.models import ShortcutIntentRecord, SuggestionRecord
from awe.persistence.repository import (
    fetch_shortcut_intent_by_key,
    fetch_suggestion_by_key,
    list_suggestions,
)

_VISIBLE_STATES = {"active", "stale"}


@dataclass(frozen=True, slots=True)
class IntentView:
    intent_key: str
    mode: str | None
    destination_screen: str | None
    target: str | None
    requires_user_confirmation: bool
    risk_decision: str
    benefit_saved_actions: int
    benefit_level: str


@dataclass(frozen=True, slots=True)
class SuggestionView:
    suggestion_key: str
    project_id: str
    subject_id: str
    state: str
    reason_codes: list[str]
    intent: IntentView
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


def _to_intent_view(record: ShortcutIntentRecord) -> IntentView:
    benefit = BenefitEvidence(
        intent_id=record.intent_key,
        observed_actions=record.benefit_observed_actions,
        planned_actions=record.benefit_planned_actions,
    )
    return IntentView(
        intent_key=record.intent_key,
        mode=record.mode,
        destination_screen=record.destination_screen,
        target=record.target,
        requires_user_confirmation=record.requires_user_confirmation,
        risk_decision=record.risk_decision,
        benefit_saved_actions=benefit.saved_actions,
        benefit_level=benefit.level.value,
    )


def _to_suggestion_view(session: Session, record: SuggestionRecord) -> SuggestionView | None:
    intent_record = fetch_shortcut_intent_by_key(session, record.primary_intent_key)
    if intent_record is None:
        return None
    return SuggestionView(
        suggestion_key=record.suggestion_key,
        project_id=record.project_id,
        subject_id=record.subject_id,
        state=record.state,
        reason_codes=record.reason_codes,
        intent=_to_intent_view(intent_record),
        created_at=record.created_at,
        updated_at=record.updated_at,
        dismissed_at=record.dismissed_at,
    )


def list_subject_suggestions(session: Session, project_id: str, subject_id: str) -> list[SuggestionView]:
    records = list_suggestions(session, project_id, subject_id, states=_VISIBLE_STATES)
    views = [_to_suggestion_view(session, record) for record in records]
    return [view for view in views if view is not None]


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
