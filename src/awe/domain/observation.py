"""Canonical Observation modeli (spesifikasyon bölüm 30).

Observation, müşteriye özel raw event'in Adapter tarafından üretilen, uygulamadan bağımsız
karşılığıdır. Aşağı katmanların hiçbiri bir daha müşterinin ham telemetry formatını görmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)


@dataclass(frozen=True, slots=True)
class ObservationQuality:
    """Adapter'ın canonicalization sırasında ürettiği veri kalitesi kanıtı."""

    has_screen: bool
    has_widget: bool
    has_session_id: bool
    is_synthetic_session: bool = False
    mapping_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Observation:
    event_id: str
    project_id: str
    subject_id: str
    session_id: str
    timestamp: datetime

    source: ObservationSource

    action: str
    role: ObservationRole
    effect: ObservationEffect
    trigger: ObservationTrigger

    screen: str | None
    widget: str | None

    target: str | None
    """Hedef referansı (ör. tıklanan öğenin id'si). `None` iki durumu birden temsil eder:
    mapping target'ı hiç izlemiyor ya da bu event için raw değer boş — ikisi de aşağı
    katmanlar için "bilinen, kararlı bir hedef yok" anlamına gelir. Boş string (`""`),
    mapping target'ı izliyor ama bu event'in AÇIKÇA hedefi olmadığını (ör. "logout")
    `None`'dan ayırt etmek için kullanılır (bkz. `awe.planner.state_reconstruction`)."""
    parameters: dict[str, str] = field(default_factory=dict)

    status: ObservationStatus = ObservationStatus.UNKNOWN
    breaks_episode: bool = False

    app_version: str | None = None
    mapping_version: str = "unversioned"

    quality: ObservationQuality = field(
        default_factory=lambda: ObservationQuality(
            has_screen=False, has_widget=False, has_session_id=False
        )
    )
