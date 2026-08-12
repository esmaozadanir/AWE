"""Screen Transition Evidence modeli (bölüm 6.8).

Bir ACTION sonrasında gözlenen opaque screen anahtarının session'lar arası tutarlılığını
toplar. Nedensellik kanıtlamaz, yalnızca korelasyon gösterir (bölüm 9.2).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ScreenEvidenceState
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class ScreenTransitionEvidence:
    symbol: Symbol
    """Kanıtın toplandığı ACTION sembolü (genellikle aday Anchor)."""
    state: ScreenEvidenceState
    screen: str | None
    """`STABLE` ise session'lar arası ortak ekran; aksi halde `None`."""
    supporting_sessions: int
    conflicting_screens: tuple[str, ...] = ()
