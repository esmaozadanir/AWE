"""Final Selection çıktısı ve lifecycle modeli (bölüm 91-95)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import ReasonCode, SuggestionState


@dataclass
class Suggestion:
    suggestion_id: str
    project_id: str
    subject_id: str
    family_id: str

    primary_plan_id: str
    fallback_plan_ids: tuple[str, ...]

    state: SuggestionState
    reason_codes: tuple[ReasonCode, ...] = field(default_factory=tuple)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismiss_cooldown_until: datetime | None = None
