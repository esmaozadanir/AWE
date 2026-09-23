"""Analiz pipeline'ının ihtiyaç duyduğu okuma/yazma işlemleri.

Bu katman iş kuralı içermez; yalnızca domain nesneleri ile veritabanı satırları arasında köprü
kurar. Motor batch/recompute modelindedir (bkz. `awe.persistence.models` modül docstring'i):
her `analyze_subject` çağrısı bir subject'in TÜM `observations`'ını okur ve Habit/Intent
sonuçlarını sıfırdan yeniden hesaplayıp `habit_evaluations`/`shortcut_intents` tablolarını
tamamen değiştirir (delete+reinsert). Yalnızca `suggestions` gerçek kalıcı state taşır
(dismiss/cooldown) ve bu yüzden upsert edilir, asla toptan silinmez.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from awe.domain.benefit import BenefitEvidence
from awe.domain.habit import HabitAssessment
from awe.domain.observation import Observation
from awe.domain.plan import Scope, ShortcutIntent
from awe.domain.risk import RiskAssessment
from awe.persistence.models import (
    EventConflictRecord,
    EventRecord,
    HabitEvaluationRecord,
    ObservationRecord,
    ShortcutIntentRecord,
    SuggestionRecord,
)
from awe.persistence.serialization import (
    anchor_to_dict,
    habit_evidence_to_dict,
    observation_to_record,
    reason_codes_to_list,
    record_to_observation,
    risk_evidence_to_dict,
    scope_to_dict,
)


def event_exists(session: Session, project_id: str, event_id: str) -> bool:
    stmt = select(EventRecord.id).where(EventRecord.project_id == project_id, EventRecord.event_id == event_id)
    return session.execute(stmt).first() is not None


def fetch_event_payload(session: Session, project_id: str, event_id: str) -> dict | None:
    stmt = select(EventRecord.raw_payload).where(
        EventRecord.project_id == project_id, EventRecord.event_id == event_id
    )
    row = session.execute(stmt).first()
    return row[0] if row is not None else None


def insert_event(
    session: Session, project_id: str, event_id: str, subject_id: str, received_at: datetime, raw_payload: dict
) -> None:
    session.add(
        EventRecord(
            project_id=project_id,
            event_id=event_id,
            subject_id=subject_id,
            received_at=received_at,
            raw_payload=raw_payload,
        )
    )


def insert_event_conflict(
    session: Session,
    project_id: str,
    event_id: str,
    first_payload: dict,
    conflicting_payload: dict,
    detected_at: datetime,
) -> None:
    session.add(
        EventConflictRecord(
            project_id=project_id,
            event_id=event_id,
            first_payload=first_payload,
            conflicting_payload=conflicting_payload,
            detected_at=detected_at,
        )
    )


def insert_observation(session: Session, observation: Observation) -> ObservationRecord:
    record = observation_to_record(observation)
    session.add(record)
    session.flush()
    return record


def fetch_all_observations(session: Session, project_id: str, subject_id: str) -> list[Observation]:
    stmt = (
        select(ObservationRecord)
        .where(ObservationRecord.project_id == project_id, ObservationRecord.subject_id == subject_id)
        .order_by(ObservationRecord.timestamp)
    )
    records = session.execute(stmt).scalars().all()
    return [record_to_observation(record) for record in records]


def replace_habit_evaluations(
    session: Session,
    project_id: str,
    subject_id: str,
    assessments: list[HabitAssessment],
    family_key_by_variant: dict[str, str],
    now: datetime,
) -> None:
    session.query(HabitEvaluationRecord).filter(
        HabitEvaluationRecord.project_id == project_id, HabitEvaluationRecord.subject_id == subject_id
    ).delete(synchronize_session=False)

    for assessment in assessments:
        session.add(
            HabitEvaluationRecord(
                project_id=project_id,
                subject_id=subject_id,
                variant_key=assessment.variant_id,
                family_key=family_key_by_variant[assessment.variant_id],
                decision=assessment.decision.value,
                reason_codes=reason_codes_to_list(assessment.reason_codes),
                evidence=habit_evidence_to_dict(assessment.evidence) if assessment.evidence else None,
                evaluated_at=now,
            )
        )


def replace_shortcut_intents(
    session: Session,
    project_id: str,
    subject_id: str,
    entries: list[tuple[ShortcutIntent, Scope, str, RiskAssessment, BenefitEvidence, str, list[str]]],
    now: datetime,
) -> None:
    """`entries`: `(intent, scope, family_key, risk, benefit, selection_outcome, selection_reason_codes)`."""

    session.query(ShortcutIntentRecord).filter(
        ShortcutIntentRecord.project_id == project_id, ShortcutIntentRecord.subject_id == subject_id
    ).delete(synchronize_session=False)

    for intent, scope, family_key, risk, benefit, selection_outcome, selection_reasons in entries:
        session.add(
            ShortcutIntentRecord(
                intent_key=intent.intent_id,
                project_id=project_id,
                subject_id=subject_id,
                variant_key=intent.variant_id,
                family_key=family_key,
                anchor=anchor_to_dict(intent.anchor),
                scope=scope_to_dict(scope),
                state=intent.state.value,
                mode=intent.mode.value if intent.mode else None,
                destination_screen=intent.destination_screen,
                target=intent.target,
                requires_user_confirmation=intent.requires_user_confirmation,
                supporting_occurrences=intent.supporting_occurrences,
                intent_reason_codes=reason_codes_to_list(intent.reason_codes),
                risk_decision=risk.decision.value,
                risk_evidence=risk_evidence_to_dict(risk.evidence),
                risk_reason_codes=reason_codes_to_list(risk.reason_codes),
                benefit_observed_actions=benefit.observed_actions,
                benefit_planned_actions=benefit.planned_actions,
                selection_outcome=selection_outcome,
                selection_reason_codes=selection_reasons,
                evaluated_at=now,
            )
        )


def fetch_suggestion_by_variant(session: Session, variant_key: str) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.variant_key == variant_key)
    return session.execute(stmt).scalar_one_or_none()


def upsert_suggestion(
    session: Session,
    project_id: str,
    subject_id: str,
    family_key: str,
    variant_key: str,
    primary_intent_key: str,
    state: str,
    reason_codes: list[str],
    now: datetime,
    dismissed_at: datetime | None,
    dismiss_cooldown_until: datetime | None,
) -> SuggestionRecord:
    record = fetch_suggestion_by_variant(session, variant_key)
    if record is None:
        record = SuggestionRecord(
            suggestion_key=f"sug_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            subject_id=subject_id,
            family_key=family_key,
            variant_key=variant_key,
            created_at=now,
        )
        session.add(record)
    record.primary_intent_key = primary_intent_key
    record.state = state
    record.reason_codes = reason_codes
    record.updated_at = now
    record.dismissed_at = dismissed_at
    record.dismiss_cooldown_until = dismiss_cooldown_until
    session.flush()
    return record


def list_suggestions(
    session: Session, project_id: str, subject_id: str, states: set[str] | None = None
) -> list[SuggestionRecord]:
    stmt = select(SuggestionRecord).where(
        SuggestionRecord.project_id == project_id, SuggestionRecord.subject_id == subject_id
    )
    if states is not None:
        stmt = stmt.where(SuggestionRecord.state.in_(states))
    return list(session.execute(stmt).scalars().all())


def fetch_suggestion_by_key(session: Session, suggestion_key: str) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.suggestion_key == suggestion_key)
    return session.execute(stmt).scalar_one_or_none()


def fetch_shortcut_intent_by_key(session: Session, intent_key: str) -> ShortcutIntentRecord | None:
    stmt = select(ShortcutIntentRecord).where(ShortcutIntentRecord.intent_key == intent_key)
    return session.execute(stmt).scalar_one_or_none()


def fetch_habit_evaluation_by_variant(session: Session, variant_key: str) -> HabitEvaluationRecord | None:
    stmt = select(HabitEvaluationRecord).where(HabitEvaluationRecord.variant_key == variant_key)
    return session.execute(stmt).scalar_one_or_none()


def mark_suggestion_delivery(
    session: Session, suggestion_key: str, now: datetime, error: str | None
) -> SuggestionRecord | None:
    """`error=None`: başarılı gönderim, `delivered_at=now` yazılır ve önceki hata temizlenir.
    `error` verilmişse yalnızca `delivery_error` güncellenir, `delivered_at` DOKUNULMAZ --
    böylece bir sonraki çalıştırmada bu suggestion tekrar "pending" sayılır (retry)."""
    record = fetch_suggestion_by_key(session, suggestion_key)
    if record is None:
        return None
    if error is None:
        record.delivered_at = now
        record.delivery_error = None
    else:
        record.delivery_error = error
    session.flush()
    return record


def list_habit_evaluations(session: Session, project_id: str, subject_id: str) -> list[HabitEvaluationRecord]:
    stmt = select(HabitEvaluationRecord).where(
        HabitEvaluationRecord.project_id == project_id, HabitEvaluationRecord.subject_id == subject_id
    )
    return list(session.execute(stmt).scalars().all())
