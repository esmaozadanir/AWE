"""Canonical Observation'dan ACTION/CONTEXT/IGNORE sınıflandırması.

Sınıflandırma yalnızca `trigger`, `effect` ve `status` üçlüsünden yapısal olarak türetilir.
`role` alanına, role tahminine ya da müşteriye özel `action`/`screen`/`widget` string'lerine
hiçbir zaman bakılmaz — aksi halde motor belirli bir uygulamaya özel davranmaya başlar
(bölüm 1). Sonuç kalıcı bir Observation alanı değildir; ihtiyaç anında hesaplanan bir
değerdir (bkz. `EventClassification`).
"""

from __future__ import annotations

from awe.domain.enums import EventClassification, ObservationEffect, ObservationStatus, ObservationTrigger
from awe.domain.observation import Observation

USER_TRIGGERS = frozenset(
    {
        ObservationTrigger.BUTTON,
        ObservationTrigger.KEYBOARD,
        ObservationTrigger.VOICE,
        ObservationTrigger.LONG_PRESS,
        ObservationTrigger.HARDWARE,
        ObservationTrigger.BIOMETRIC,
        ObservationTrigger.DEEPLINK,
        ObservationTrigger.NOTIFICATION,
    }
)

GESTURE_TRIGGERS = frozenset({ObservationTrigger.SWIPE, ObservationTrigger.DRAG})

PASSIVE_TRIGGERS = frozenset({ObservationTrigger.SCROLL, ObservationTrigger.HOVER, ObservationTrigger.FOCUS})

SYSTEM_TRIGGERS = frozenset(
    {
        ObservationTrigger.AUTOMATIC,
        ObservationTrigger.SCHEDULED,
        ObservationTrigger.LIFECYCLE,
        ObservationTrigger.SENSOR,
    }
)

NON_USER_TRIGGERS = frozenset(
    {
        ObservationTrigger.API,
        ObservationTrigger.WEBHOOK,
        ObservationTrigger.ADMIN,
        ObservationTrigger.SHORTCUT,
        ObservationTrigger.UNKNOWN,
    }
)

CONTEXT_EFFECTS = frozenset(
    {
        ObservationEffect.VIEW,
        ObservationEffect.ROUTE,
        ObservationEffect.OPEN_MODAL,
        ObservationEffect.CLOSE_MODAL,
    }
)

EMPTY_EFFECTS = frozenset({ObservationEffect.NONE, ObservationEffect.UNKNOWN})


def classify_event(observation: Observation) -> EventClassification:
    if observation.status != ObservationStatus.SUCCESS:
        return EventClassification.IGNORE

    if observation.effect in EMPTY_EFFECTS:
        return EventClassification.IGNORE

    # Saf view hiçbir zaman action adımı değildir.
    if observation.effect == ObservationEffect.VIEW:
        if observation.trigger in USER_TRIGGERS or observation.trigger in SYSTEM_TRIGGERS:
            return EventClassification.CONTEXT
        return EventClassification.IGNORE

    if observation.trigger in USER_TRIGGERS:
        return EventClassification.ACTION

    # Swipe/drag, view dışındaki bilinen bir sonuç doğuruyorsa action'dır.
    if observation.trigger in GESTURE_TRIGGERS:
        return EventClassification.ACTION

    # Scroll/hover/focus dizeye girmez.
    if observation.trigger in PASSIVE_TRIGGERS:
        return EventClassification.IGNORE

    # Sistem tarafından açılan ekran/modal yalnızca context'tir.
    if observation.trigger in SYSTEM_TRIGGERS:
        if observation.effect in {
            ObservationEffect.ROUTE,
            ObservationEffect.OPEN_MODAL,
            ObservationEffect.CLOSE_MODAL,
        }:
            return EventClassification.CONTEXT
        return EventClassification.IGNORE

    # api/webhook/admin/shortcut/unknown/system(legacy) — hiçbiri yukarıdaki gruplara
    # girmeyen tetikleyiciler de dahil (NON_USER_TRIGGERS + gruplanmamış legacy değerler).
    return EventClassification.IGNORE
