"""Suggestion listeleme ve dismiss endpoint'leri."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import (
    IntentResponse,
    PatternStepResponse,
    SuggestionExplanationResponse,
    SuggestionResponse,
    VariantPatternResponse,
)
from awe.config import ProjectConfig
from awe.services import (
    IntentView,
    SuggestionExplanationView,
    SuggestionView,
    VariantPatternView,
    dismiss_suggestion,
    explain_suggestion,
    list_subject_suggestions,
    list_variant_patterns,
)

router = APIRouter(prefix="/projects/{project_id}/subjects/{subject_id}", tags=["suggestions"])


def _intent_response(intent: IntentView) -> IntentResponse:
    return IntentResponse(
        intent_key=intent.intent_key,
        mode=intent.mode,
        destination_screen=intent.destination_screen,
        target=intent.target,
        requires_user_confirmation=intent.requires_user_confirmation,
        risk_decision=intent.risk_decision,
        benefit_saved_actions=intent.benefit_saved_actions,
        benefit_level=intent.benefit_level,
    )


def _suggestion_response(view: SuggestionView) -> SuggestionResponse:
    return SuggestionResponse(
        suggestion_key=view.suggestion_key,
        state=view.state,
        reason_codes=view.reason_codes,
        intent=_intent_response(view.intent),
        created_at=view.created_at,
        updated_at=view.updated_at,
        dismissed_at=view.dismissed_at,
    )


def _explanation_response(view: SuggestionExplanationView) -> SuggestionExplanationResponse:
    return SuggestionExplanationResponse(
        suggestion_key=view.suggestion_key,
        steps=view.steps,
        repeat_count=view.repeat_count,
        saved_steps=view.saved_steps,
        target=view.target,
        anchor=view.anchor,
    )


def _pattern_response(view: VariantPatternView) -> VariantPatternResponse:
    return VariantPatternResponse(
        variant_key=view.variant_key,
        family_key=view.family_key,
        pattern=[PatternStepResponse(action=s.action, effect=s.effect, screen=s.screen) for s in view.pattern],
        decision=view.decision,
        reason_codes=view.reason_codes,
        recommended=view.recommended,
        suggestion_state=view.suggestion_state,
        repeat_count=view.repeat_count,
        distinct_days=view.distinct_days,
        mode=view.mode,
        destination_screen=view.destination_screen,
        target=view.target,
        saved_steps=view.saved_steps,
    )


@router.get("/patterns", response_model=list[VariantPatternResponse])
def get_variant_patterns(
    project_id: str,
    subject_id: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> list[VariantPatternResponse]:
    """Son `/analyze` çalışmasının bulduğu HER variant için (öneriye dönüşsün ya da dönüşmesin)
    tespit edilen davranış dizisini ve kararın gerekçesini döndürür -- demo/açıklanabilirlik
    amaçlı, önerilen ve önerilmeyen örüntüleri aynı sözleşmede karşılaştırmak için."""
    views = list_variant_patterns(session, project_config, project_id, subject_id)
    return [_pattern_response(v) for v in views]


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


@router.get("/suggestions/{suggestion_key}/explanation", response_model=SuggestionExplanationResponse)
def get_suggestion_explanation(
    project_id: str,
    subject_id: str,
    suggestion_key: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> SuggestionExplanationResponse:
    view = explain_suggestion(session, project_id, subject_id, suggestion_key)
    if view is None:
        raise HTTPException(status_code=404, detail=f"unknown suggestion_key '{suggestion_key}'")
    return _explanation_response(view)
