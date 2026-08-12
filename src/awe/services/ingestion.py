"""Raw event ingestion: idempotent kabul ve canonical Observation üretimi (bölüm 11, 97)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.adapter import AdapterValidationError, build_observation
from awe.config import ProjectConfig, log_event
from awe.persistence.repository import event_exists, insert_event, insert_observation


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    accepted: bool
    duplicate: bool
    event_id: str | None = None
    error: str | None = None


def ingest_event(
    session: Session, project_config: ProjectConfig, url_project_id: str, raw_event: dict, now: datetime
) -> IngestOutcome:
    try:
        observation = build_observation(raw_event, project_config.mapping)
    except AdapterValidationError as exc:
        return IngestOutcome(accepted=False, duplicate=False, error=str(exc))

    if observation.project_id != url_project_id:
        return IngestOutcome(
            accepted=False,
            duplicate=False,
            error=f"payload project_id '{observation.project_id}' does not match '{url_project_id}'",
        )

    if event_exists(session, observation.project_id, observation.event_id):
        return IngestOutcome(accepted=True, duplicate=True, event_id=observation.event_id)

    insert_event(session, observation.project_id, observation.event_id, observation.subject_id, now, raw_event)
    insert_observation(session, observation)
    log_event(
        "event_ingested",
        project_id=observation.project_id,
        subject_id=observation.subject_id,
        action=observation.action,
    )
    return IngestOutcome(accepted=True, duplicate=False, event_id=observation.event_id)


def ingest_batch(
    session: Session, project_config: ProjectConfig, url_project_id: str, raw_events: list[dict], now: datetime
) -> list[IngestOutcome]:
    return [ingest_event(session, project_config, url_project_id, raw_event, now) for raw_event in raw_events]
