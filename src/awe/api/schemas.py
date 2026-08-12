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
