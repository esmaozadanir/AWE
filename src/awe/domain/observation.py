"""Canonical Observation modeli (bkz. AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md bölüm 4).

Observation, müşteriye özel raw event'in Adapter tarafından üretilen, uygulamadan bağımsız
karşılığıdır. Aşağı katmanların hiçbiri bir daha müşterinin ham telemetry formatını görmez.
`role`, `widget`, `parameters`, `breaksEpisode`, `appVersion` kasıtlı olarak yoktur: bu alanlar
eski tasarımdan kalmıştı ve yeni sözleşme onları tanımıyor (bkz. bölüm 4, 9.10 dışı bırakılan
"online state" notları hariç).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import (
    ObservationEffect,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)


@dataclass(frozen=True, slots=True)
class ObservationQuality:
    """Adapter'ın canonicalization sırasında ürettiği veri kalitesi kanıtı (bölüm 6.1).

    `session_id` burada yer almaz: zorunlu bir alandır ve eksikse/boşsa event reddedilir
    (bölüm 6.1 "Zorunlu alan eksikse event reject edilir") — sentetik session_id üretme veya
    kısmi kabul yoktur."""

    has_screen: bool
    missing_target_field: bool = False
    """Raw payload'da `target` anahtarı hiç yoktu (bölüm 6.1: "target anahtarı yoksa
    MISSING_TARGET_FIELD üretilir"). `target=None` ile karıştırılmamalı: `target=None` "açıkça
    hedef yok" anlamına gelirken bu flag "hedef verisi bilinmiyor" anlamına gelir (bölüm 3, kural 6)."""
    invalid_duration: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Observation:
    event_id: str
    project_id: str
    subject_id: str
    session_id: str
    timestamp: datetime

    action: str
    source: ObservationSource
    trigger: ObservationTrigger
    effect: ObservationEffect
    status: ObservationStatus

    screen: str | None
    target: str | None
    """Hedef referansı. `None` = raw event'te `target` alanı açıkça `null` gönderildi ("açıkça
    hedef yok", bölüm 3 kural 6). Raw payload'da `target` anahtarı hiç yoksa değer yine `None`
    olur ama `quality.missing_target_field=True` ile işaretlenir ("hedef verisi bilinmiyor") —
    aşağı katmanlar bu ayrımı `quality` üzerinden okur, `target` tek başına bunu taşıyamaz."""
    duration_ms: int | None
    """Yalnızca audit amaçlı (bölüm 6.14, 9.9) — hiçbir karar bu alana bakmaz."""

    mapping_version: str = "unversioned"

    quality: ObservationQuality = field(default_factory=lambda: ObservationQuality(has_screen=False))
