"""API'nin dışarıya sunduğu Pydantic request/response modelleri.

Bu modeller `awe.domain` nesnelerini birebir yansıtmaz; yalnızca dışarıya sunulması gereken
alanları taşır (ör. dahili veritabanı id'leri değil, opak `intent_key`/`suggestion_key` string'leri).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventIngestResponse(BaseModel):
    accepted: bool
    duplicate: bool
    conflict: bool = False
    event_id: str | None = None
    error: str | None = None


class BatchIngestResponse(BaseModel):
    results: list[EventIngestResponse]
    accepted_count: int
    duplicate_count: int
    rejected_count: int


class VariantAnalysisResponse(BaseModel):
    variant_key: str
    habit_decision: str
    suggestion_state: str | None


class AnalysisResponse(BaseModel):
    project_id: str
    subject_id: str
    series_count: int
    variants: list[VariantAnalysisResponse]


class IntentResponse(BaseModel):
    intent_key: str
    mode: str | None
    destination_screen: str | None
    target: str | None
    requires_user_confirmation: bool
    risk_decision: str
    benefit_saved_actions: int
    benefit_level: str


class SuggestionResponse(BaseModel):
    suggestion_key: str
    state: str
    reason_codes: list[str]
    intent: IntentResponse
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


class SuggestionExplanationResponse(BaseModel):
    suggestion_key: str
    steps: list[str]
    repeat_count: int
    saved_steps: int
    target: str | None
    anchor: str


class PatternStepResponse(BaseModel):
    action: str
    effect: str
    screen: str | None


class PullResponse(BaseModel):
    success: bool
    error: str | None = None
    ingested_count: int = 0
    rejected_count: int = 0
    series_count: int = 0


class PushResponse(BaseModel):
    success: bool
    error: str | None = None
    pushed_count: int = 0
    push_failed_count: int = 0


class VariantPatternResponse(BaseModel):
    variant_key: str
    family_key: str
    pattern: list[PatternStepResponse]
    decision: str
    reason_codes: list[str]
    recommended: bool
    suggestion_state: str | None
    repeat_count: int | None
    distinct_days: int | None
    mode: str | None
    destination_screen: str | None
    target: str | None
    saved_steps: int | None
