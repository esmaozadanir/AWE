"""Deterministik session içi sıralama (bölüm 6.3).

Bu modül yalnızca genel, sınıflandırmadan bağımsız sıralama + eşit-timestamp tespiti yapar.
Bir eşitliğin gerçek bir "ambiguity barrier" (yalnızca 2+ ACTION-classified event aynı
timestamp'i paylaştığında chunk'ı kesen sınır, bölüm 6.3) olup olmadığına O-Series Builder
karar verir — çünkü bu karar `classify_event` sonucunu bilmeyi gerektirir ve ordering
katmanı sınıflandırmayı tekrar hesaplamamalıdır.
"""

from __future__ import annotations

from collections import defaultdict

from awe.domain.enums import OrderingConfidence
from awe.domain.observation import Observation


def group_by_session(observations: list[Observation]) -> dict[str, list[Observation]]:
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.session_id].append(observation)
    return dict(grouped)


def order_session(observations: list[Observation]) -> tuple[list[Observation], OrderingConfidence]:
    """`(timestamp, event_id)` ile deterministik sıralar. `event_id` yalnızca determinizmi
    garanti eder — motor hiçbir zaman bir kaynak sıra numarası uydurmaz veya talep etmez.
    Eşit timestamp varsa `OrderingConfidence.LOW` döner (yalnızca bilgilendirme amaçlı; asıl
    ambiguity-barrier kararı O-Series Builder'da verilir)."""

    if not observations:
        return [], OrderingConfidence.HIGH

    ordered = sorted(observations, key=lambda o: (o.timestamp, o.event_id))
    has_ambiguous_tie = any(ordered[i].timestamp == ordered[i + 1].timestamp for i in range(len(ordered) - 1))
    confidence = OrderingConfidence.LOW if has_ambiguous_tie else OrderingConfidence.HIGH
    return ordered, confidence
