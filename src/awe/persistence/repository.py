"""Analiz pipeline'ının ihtiyaç duyduğu okuma/yazma işlemleri.

Bu katman iş kuralı içermez; yalnızca domain nesneleri ile veritabanı satırları arasında
köprü kurar. Var olan family/series kimlikleri asla yeniden numaralandırılmaz — yalnızca
işlenmemiş (henüz bir seriye atanmamış) observation'lar üzerinden artımlı olarak genişletilir
(`docs/architecture.md`, "artımlı analiz" bölümü).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from awe.adapter.classification import classify_event
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import EventClassification, ObservationStatus, ObservationTrigger, OrderingConfidence
from awe.domain.family import BehaviorFamily
from awe.domain.habit import HabitAssessment
from awe.domain.observation import Observation
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskDecisionResult
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken
from awe.persistence.models import (
    EventRecord,
    FamilyRecord,
    HabitEvaluationRecord,
    ObservationRecord,
    PlanCandidateRecord,
    SeriesRecord,
    SuggestionRecord,
)
from awe.persistence.serialization import (
    benefit_to_columns,
    dict_to_relationship,
    dict_to_variant,
    habit_evidence_to_dict,
    observation_to_record,
    plan_candidate_to_dict,
    reason_codes_to_list,
    record_to_observation,
    relationship_to_dict,
    risk_evidence_to_dict,
    variant_to_dict,
)
from awe.series.normalization import normalize_steps


def event_exists(session: Session, project_id: str, event_id: str) -> bool:
    stmt = select(EventRecord.id).where(EventRecord.project_id == project_id, EventRecord.event_id == event_id)
    return session.execute(stmt).first() is not None


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


def insert_observation(session: Session, observation: Observation) -> ObservationRecord:
    record = observation_to_record(observation)
    session.add(record)
    session.flush()
    return record


def fetch_unprocessed_observations(
    session: Session, project_id: str, subject_id: str
) -> tuple[list[Observation], dict[str, int]]:
    stmt = (
        select(ObservationRecord)
        .where(
            ObservationRecord.project_id == project_id,
            ObservationRecord.subject_id == subject_id,
            ObservationRecord.series_id.is_(None),
        )
        .order_by(ObservationRecord.timestamp)
    )
    records = session.execute(stmt).scalars().all()
    observations = [record_to_observation(r) for r in records]
    db_id_by_event_id = {r.event_id: r.id for r in records}
    return observations, db_id_by_event_id


def fetch_families(session: Session, project_id: str, subject_id: str) -> list[tuple[int, BehaviorFamily]]:
    stmt = select(FamilyRecord).where(
        FamilyRecord.project_id == project_id, FamilyRecord.subject_id == subject_id
    )
    records = session.execute(stmt).scalars().all()

    result: list[tuple[int, BehaviorFamily]] = []
    for record in records:
        stmt_series = select(SeriesRecord.series_key).where(SeriesRecord.family_id == record.id)
        member_series_ids = list(session.execute(stmt_series).scalars().all())
        family = BehaviorFamily(
            family_id=record.family_key,
            project_id=record.project_id,
            subject_id=record.subject_id,
            representative_variants=[dict_to_variant(v) for v in record.representative_variants],
            relationships=[dict_to_relationship(r) for r in record.relationships],
            cohesion=record.cohesion,
            member_series_ids=member_series_ids,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        result.append((record.id, family))
    return result


def create_family(
    session: Session, project_id: str, subject_id: str, family: BehaviorFamily, now: datetime
) -> int:
    record = FamilyRecord(
        family_key=f"fam_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        subject_id=subject_id,
        representative_variants=[variant_to_dict(v) for v in family.representative_variants],
        relationships=[relationship_to_dict(r) for r in family.relationships],
        cohesion=family.cohesion,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    family.family_id = record.family_key
    return record.id


def update_family(session: Session, family_db_id: int, family: BehaviorFamily, now: datetime) -> None:
    record = session.get(FamilyRecord, family_db_id)
    assert record is not None
    record.representative_variants = [variant_to_dict(v) for v in family.representative_variants]
    record.relationships = [relationship_to_dict(r) for r in family.relationships]
    record.cohesion = family.cohesion
    record.updated_at = now


def create_series(
    session: Session,
    series: OSeries,
    family_db_id: int | None,
    ambiguous_family_db_ids: list[int],
    db_id_by_event_id: dict[str, int],
) -> int:
    record = SeriesRecord(
        series_key=series.series_id,
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        started_at=series.started_at,
        ended_at=series.ended_at,
        ordering_confidence=series.ordering_confidence.value,
        ended_by_breaks_episode=series.ended_by_breaks_episode,
        entry_trigger=series.entry_trigger.value,
        entry_screen=series.entry_screen,
        has_shortcut_trigger=series.has_shortcut_trigger,
        final_status=series.final_status.value,
        family_id=family_db_id,
        ambiguous_family_ids=ambiguous_family_db_ids,
    )
    session.add(record)
    session.flush()

    observation_ids = [db_id_by_event_id[obs.event_id] for obs in series.raw_observations]
    session.query(ObservationRecord).filter(ObservationRecord.id.in_(observation_ids)).update(
        {"series_id": record.id}, synchronize_session=False
    )
    return record.id


def fetch_member_series(session: Session, family_db_id: int, detour_max_length: int) -> list[OSeries]:
    stmt = select(SeriesRecord).where(SeriesRecord.family_id == family_db_id).order_by(SeriesRecord.started_at)
    series_records = session.execute(stmt).scalars().all()

    result: list[OSeries] = []
    for series_record in series_records:
        obs_stmt = (
            select(ObservationRecord)
            .where(ObservationRecord.series_id == series_record.id)
            .order_by(ObservationRecord.timestamp)
        )
        observation_records = session.execute(obs_stmt).scalars().all()
        result.append(_rebuild_series(series_record, observation_records, detour_max_length))
    return result


def _rebuild_series(
    series_record: SeriesRecord, observation_records: Sequence[ObservationRecord], detour_max_length: int
) -> OSeries:
    observations = [record_to_observation(r) for r in observation_records]
    raw_steps = []
    for index, obs in enumerate(observations):
        if classify_event(obs) != EventClassification.ACTION:
            continue
        raw_steps.append(
            BehaviorStep(
                token=BehaviorToken(action=obs.action, effect=obs.effect),
                screen=obs.screen,
                widget=obs.widget,
                status=obs.status,
                observation_index=index,
            )
        )
    normalization = normalize_steps(raw_steps, detour_max_length)

    return OSeries(
        series_id=series_record.series_key,
        project_id=series_record.project_id,
        subject_id=series_record.subject_id,
        session_id=series_record.session_id,
        started_at=series_record.started_at,
        ended_at=series_record.ended_at,
        ordering_confidence=OrderingConfidence(series_record.ordering_confidence),
        raw_observations=tuple(observations),
        normalized_steps=tuple(normalization.steps),
        retries=tuple(normalization.retries),
        detour_observation_count=normalization.detour_step_count,
        ended_by_breaks_episode=series_record.ended_by_breaks_episode,
        entry_trigger=ObservationTrigger(series_record.entry_trigger),
        entry_screen=series_record.entry_screen,
        has_shortcut_trigger=series_record.has_shortcut_trigger,
        final_status=ObservationStatus(series_record.final_status),
    )


def upsert_habit_evaluation(
    session: Session, family_db_id: int, assessment: HabitAssessment, now: datetime
) -> None:
    stmt = select(HabitEvaluationRecord).where(HabitEvaluationRecord.family_id == family_db_id)
    record = session.execute(stmt).scalar_one_or_none()
    if record is None:
        record = HabitEvaluationRecord(family_id=family_db_id)
        session.add(record)
    record.decision = assessment.decision.value
    record.reason_codes = reason_codes_to_list(assessment.reason_codes)
    record.evidence = habit_evidence_to_dict(assessment.evidence) if assessment.evidence else None
    record.evaluated_at = now


def replace_plan_candidates(
    session: Session,
    family_db_id: int,
    evaluated: list[tuple[PlanCandidate, RiskDecisionResult, BenefitEvidence]],
    now: datetime,
) -> dict[str, int]:
    session.query(PlanCandidateRecord).filter(PlanCandidateRecord.family_id == family_db_id).delete(
        synchronize_session=False
    )
    session.flush()

    db_id_by_plan_id: dict[str, int] = {}
    for candidate, risk_result, benefit in evaluated:
        payload = plan_candidate_to_dict(candidate)
        record = PlanCandidateRecord(
            plan_key=candidate.plan_id,
            family_id=family_db_id,
            plan_type=payload["plan_type"],
            anchor=payload["anchor"],
            bindings=payload["bindings"],
            target_binding=payload["target_binding"],
            supporting_occurrences=candidate.supporting_occurrences,
            risk_decision=risk_result.decision.value,
            risk_reason_codes=reason_codes_to_list(risk_result.reason_codes),
            risk_evidence=risk_evidence_to_dict(risk_result.evidence),
            reduced_bindings=list(risk_result.reduced_bindings),
            evaluated_at=now,
            **benefit_to_columns(benefit),
        )
        session.add(record)
        session.flush()
        db_id_by_plan_id[candidate.plan_id] = record.id
    return db_id_by_plan_id


def fetch_suggestion(session: Session, family_db_id: int) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.family_id == family_db_id)
    return session.execute(stmt).scalar_one_or_none()


def upsert_suggestion(
    session: Session,
    project_id: str,
    subject_id: str,
    family_db_id: int,
    primary_plan_db_id: int,
    fallback_plan_db_ids: list[int],
    state: str,
    reason_codes: list[str],
    now: datetime,
    dismissed_at: datetime | None,
    dismiss_cooldown_until: datetime | None,
) -> SuggestionRecord:
    record = fetch_suggestion(session, family_db_id)
    if record is None:
        record = SuggestionRecord(
            suggestion_key=f"sug_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            subject_id=subject_id,
            family_id=family_db_id,
            primary_plan_id=primary_plan_db_id,
            created_at=now,
        )
        session.add(record)
    record.primary_plan_id = primary_plan_db_id
    record.fallback_plan_ids = fallback_plan_db_ids
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


def fetch_plan_candidate(session: Session, plan_db_id: int) -> PlanCandidateRecord | None:
    return session.get(PlanCandidateRecord, plan_db_id)
