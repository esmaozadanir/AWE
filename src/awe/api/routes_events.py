"""Event ingestion ve subject analiz endpoint'leri."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import (
    AnalysisResponse,
    BatchIngestResponse,
    EventIngestResponse,
    PullResponse,
    VariantAnalysisResponse,
)
from awe.config import ProjectConfig
from awe.services import IngestOutcome, analyze_subject, ingest_batch, ingest_event, pull_and_analyze

router = APIRouter(tags=["events"])


def _ingest_response(outcome: IngestOutcome) -> EventIngestResponse:
    return EventIngestResponse(
        accepted=outcome.accepted,
        duplicate=outcome.duplicate,
        conflict=outcome.conflict,
        event_id=outcome.event_id,
        error=outcome.error,
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


@router.post("/analyze", response_model=AnalysisResponse)
def post_analyze_subject(
    project_id: str,
    subject_id: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> AnalysisResponse:
    summary = analyze_subject(session, project_config, project_id, subject_id, datetime.now(UTC))
    return AnalysisResponse(
        project_id=summary.project_id,
        subject_id=summary.subject_id,
        series_count=summary.series_count,
        variants=[
            VariantAnalysisResponse(
                variant_key=v.variant_key,
                habit_decision=v.habit_decision.value,
                suggestion_state=v.suggestion_state.value if v.suggestion_state else None,
            )
            for v in summary.variants
        ],
    )


@router.post("/pull", response_model=PullResponse)
def post_pull_subject(
    project_id: str,
    subject_id: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> PullResponse:
    """Dış sunucudan veri çekip (PULL), AWE'ye besleyip (INGEST) analiz eder (ANALYZE) -- bkz.
    `awe.services.ingest_sync.pull_and_analyze`. Önerileri geri gönderme (PUSH) BAĞIMSIZ bir
    yetenektir, ayrı endpoint'te (`POST .../push`) -- bkz. `awe.api.routes_suggestions`.
    `project_config.pull.enabled=False` ise ya da bu proje için `awe.transforms.{project_id}`
    henüz yazılmadıysa `success=False` + açıklayıcı `error` ile döner (5xx değil 200 -- bunlar
    HTTP hatası değil, projenin henüz tamamlanmamış konfigürasyonunun beklenen bir sonucu)."""
    result = pull_and_analyze(session, project_config, project_id, subject_id, datetime.now(UTC))
    return PullResponse(
        success=result.success,
        error=result.error,
        ingested_count=result.ingested_count,
        rejected_count=result.rejected_count,
        series_count=result.series_count,
    )
