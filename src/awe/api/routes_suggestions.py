"""Suggestion listeleme ve dismiss endpoint'leri (bölüm 97)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import PlanResponse, SuggestionResponse
from awe.config import ProjectConfig
from awe.services import PlanView, SuggestionView, dismiss_suggestion, list_subject_suggestions

router = APIRouter(prefix="/projects/{project_id}/subjects/{subject_id}", tags=["suggestions"])


def _plan_response(plan: PlanView) -> PlanResponse:
    return PlanResponse(
        plan_id=plan.plan_id,
        plan_type=plan.plan_type,
        anchor_symbol=list(plan.anchor_symbol),
        anchor_screen=plan.anchor_screen,
        bindings=plan.bindings,
        target_binding=plan.target_binding,
        risk_decision=plan.risk_decision,
        benefit_median_saved_actions=plan.benefit_median_saved_actions,
    )


def _suggestion_response(view: SuggestionView) -> SuggestionResponse:
    return SuggestionResponse(
        suggestion_key=view.suggestion_key,
        state=view.state,
        reason_codes=view.reason_codes,
        primary_plan=_plan_response(view.primary_plan),
        fallback_plans=[_plan_response(p) for p in view.fallback_plans],
        created_at=view.created_at,
        updated_at=view.updated_at,
        dismissed_at=view.dismissed_at,
    )


@router.get("/suggestions", response_model=list[SuggestionResponse])
def get_suggestions(
    project_id: str,
    subject_id: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> list[SuggestionResponse]:
    views = list_subject_suggestions(session, project_id, subject_id)
    return [_suggestion_response(v) for v in views]


@router.post("/suggestions/{suggestion_key}/dismiss", response_model=SuggestionResponse)
def post_dismiss_suggestion(
    project_id: str,
    subject_id: str,
    suggestion_key: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> SuggestionResponse:
    view = dismiss_suggestion(
        session, project_id, subject_id, suggestion_key, datetime.now(UTC), project_config.engine.lifecycle
    )
    if view is None:
        raise HTTPException(status_code=404, detail=f"unknown suggestion_key '{suggestion_key}'")
    return _suggestion_response(view)
