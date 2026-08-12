"""API'nin dışarıya sunduğu Pydantic request/response modelleri.

Bu modeller `awe.domain` nesnelerini birebir yansıtmaz; yalnızca dışarıya sunulması gereken
alanları taşır (ör. dahili veritabanı id'leri değil, opak `plan_key`/`suggestion_key` string'leri).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EventIngestResponse(BaseModel):
    accepted: bool
    duplicate: bool
    event_id: str | None = None
    error: str | None = None


class BatchIngestResponse(BaseModel):
    results: list[EventIngestResponse]
    accepted_count: int
    duplicate_count: int
    rejected_count: int


class FamilyAnalysisResponse(BaseModel):
    family_key: str
    habit_decision: str
    suggestion_state: str | None


class AnalysisResponse(BaseModel):
    project_id: str
    subject_id: str
    new_series_count: int
    families: list[FamilyAnalysisResponse]


class FieldBindingResponse(BaseModel):
    field_name: str
    state: str
    dominant_value: str | None
    dominance: float
    coverage: float
    sample_size: int
    recent_dominance: float | None


class PlanResponse(BaseModel):
    plan_id: str
    plan_type: str
    anchor_symbol: list[str]
    anchor_screen: str | None
    bindings: list[dict]
    target_binding: dict | None
    risk_decision: str
    benefit_median_saved_actions: float


class SuggestionResponse(BaseModel):
    suggestion_key: str
    state: str
    reason_codes: list[str]
    primary_plan: PlanResponse
    fallback_plans: list[PlanResponse]
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


class ResolverCapabilities(BaseModel):
    """İstemcinin bu analiz isteği için beyan ettiği Resolver yeteneği (bölüm 78).

    Body'de gönderilmezse proje varsayılanı (tam destek) kullanılır.
    """

    supports_navigate: bool = True
    supports_prefill: bool = True
    accepted_bindings: list[str] | None = None
    requires_review: bool = False
    supports_runtime_validation: bool = False


class AnalyzeRequest(BaseModel):
    resolver: ResolverCapabilities = Field(default_factory=ResolverCapabilities)
