"""Selector çıktısı ve suggestion lifecycle modeli (bölüm 6.15).

`SELECTED`, "kullanıcıya gösterildi" değil, "gösterilmeye uygun aday" demektir — gösterim
zamanlaması, cooldown ve dismiss/revive akışı ayrı bir lifecycle katmanıdır (bölüm 9.11,
bu tasarımda tamamlanmamıştır; mevcut lifecycle mekanizması korunmuştur).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import ReasonCode, SelectionOutcome, SuggestionState


@dataclass(frozen=True, slots=True)
class SelectionResult:
    intent_id: str
    outcome: SelectionOutcome
    reason_codes: tuple[ReasonCode, ...] = ()


@dataclass
class Suggestion:
    """Bir `TargetVariant` en fazla bir Anchor (dolayısıyla en fazla bir Shortcut Intent)
    üretebildiği için (bölüm 6.9-6.12), eski tasarımdaki "fallback plan" kavramı yoktur —
    bir variant'ın tek intent'i vardır."""

    suggestion_id: str
    project_id: str
    subject_id: str
    family_id: str
    variant_id: str

    primary_intent_id: str

    state: SuggestionState
    reason_codes: tuple[ReasonCode, ...] = field(default_factory=tuple)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismiss_cooldown_until: datetime | None = None
