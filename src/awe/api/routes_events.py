"""Event ingestion ve subject analiz endpoint'leri (bölüm 97)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    BatchIngestResponse,
    EventIngestResponse,
    FamilyAnalysisResponse,
)
from awe.config import ProjectConfig
from awe.risk import ResolverContract
from awe.services import IngestOutcome, analyze_subject, ingest_batch, ingest_event

router = APIRouter(prefix="/projects/{project_id}", tags=["events"])


def _ingest_response(outcome: IngestOutcome) -> EventIngestResponse:
    return EventIngestResponse(
        accepted=outcome.accepted, duplicate=outcome.duplicate, event_id=outcome.event_id, error=outcome.error
    )


@router.post("/events", response_model=EventIngestResponse)
def post_event(
    project_id: str,
    raw_event: dict,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> EventIngestResponse:
    outcome = ingest_event(session, project_config, project_id, raw_event, datetime.now(UTC))
    return _ingest_response(outcome)


@router.post("/events/batch", response_model=BatchIngestResponse)
def post_event_batch(
    project_id: str,
    raw_events: list[dict],
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> BatchIngestResponse:
    outcomes = ingest_batch(session, project_config, project_id, raw_events, datetime.now(UTC))
    return BatchIngestResponse(
        results=[_ingest_response(o) for o in outcomes],
        accepted_count=sum(1 for o in outcomes if o.accepted and not o.duplicate),
        duplicate_count=sum(1 for o in outcomes if o.duplicate),
        rejected_count=sum(1 for o in outcomes if not o.accepted),
    )


def _resolver_from_request(request: AnalyzeRequest) -> ResolverContract:
    capabilities = request.resolver
    accepted = frozenset(capabilities.accepted_bindings) if capabilities.accepted_bindings is not None else None
    return ResolverContract(
        supports_navigate=capabilities.supports_navigate,
        supports_prefill=capabilities.supports_prefill,
        accepted_bindings=accepted,
        requires_review=capabilities.requires_review,
        supports_runtime_validation=capabilities.supports_runtime_validation,
    )


@router.post("/subjects/{subject_id}/analyze", response_model=AnalysisResponse)
def post_analyze_subject(
    project_id: str,
    subject_id: str,
    request: AnalyzeRequest = AnalyzeRequest(),
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> AnalysisResponse:
    resolver = _resolver_from_request(request)
    summary = analyze_subject(session, project_config, project_id, subject_id, resolver, datetime.now(UTC))
    return AnalysisResponse(
        project_id=summary.project_id,
        subject_id=summary.subject_id,
        new_series_count=summary.new_series_count,
        families=[
            FamilyAnalysisResponse(
                family_key=f.family_key,
                habit_decision=f.habit_decision.value,
                suggestion_state=f.suggestion_state.value if f.suggestion_state else None,
            )
            for f in summary.families
        ],
    )
