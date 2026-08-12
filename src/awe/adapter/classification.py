"""Canonical Observation'dan ACTION/CONTEXT/IGNORE sınıflandırması (bölüm 6.2).

Sınıflandırma yalnızca `trigger`, `effect` ve `source` üçlüsünden yapısal olarak türetilir.
Sonuç kalıcı bir Observation alanı değildir; ihtiyaç anında hesaplanan bir değerdir.

Bilinçli davranış değişiklikleri (önceki tasarıma göre — bkz. final rapor):
- `status` artık sınıflandırmayı hiç etkilemez ("status=fail/cancel olan kullanıcı
  ACTION'ları diziden atılmaz", bölüm 3 kural 4). Başarısız denemenin genel occurrence'ı
  `ATTEMPT_ONLY` mi `RESOLVED` mi yaptığı Anchor Resolver'ın işidir (bölüm 6.9), burada değil.
- `source != "client"` artık her zaman CONTEXT üretir. Önceki tasarımda source hiçbir zaman
  gerçek bir kullanıcı ACTION'ını dışlamak için kullanılmazdı; yeni belge (bölüm 6.2) bunun
  tersini söylüyor ve burada harfiyen uygulanmıştır.
"""

from __future__ import annotations

from awe.domain.enums import EventClassification, ObservationEffect, ObservationSource, ObservationTrigger
from awe.domain.observation import Observation

USER_TRIGGERS = frozenset(
    {
        ObservationTrigger.BUTTON,
        ObservationTrigger.KEYBOARD,
        ObservationTrigger.VOICE,
        ObservationTrigger.LONG_PRESS,
        ObservationTrigger.HARDWARE,
        ObservationTrigger.BIOMETRIC,
        ObservationTrigger.SWIPE,
        ObservationTrigger.DRAG,
        ObservationTrigger.NAVIGATION,
        ObservationTrigger.NOTIFICATION,
        ObservationTrigger.DEEPLINK,
        ObservationTrigger.SHORTCUT,
    }
)
"""Belgede tanımı verilmemiş; `classify_event` sözde kodunda yalnızca isim olarak geçer
(bölüm 6.2). Bölüm 4'ün trigger sözlüğünden `automatic` ve `unknown` çıkarılarak türetilmiştir
— geri kalan tüm tetikleyiciler kullanıcının doğrudan girdisidir. `shortcut` (bölüm 4'te
literal olarak yok, bkz. `ObservationTrigger.SHORTCUT` docstring'i) kasıtlı olarak dahildir:
bir kısayolun tetiklediği event de gerçek bir kullanıcı ACTION'ıdır, yalnızca Habit'in organik
kanıt sayımından ayrıca dışlanır (bkz. `awe.habit.assessment`)."""


def classify_event(observation: Observation) -> EventClassification:
    if observation.effect == ObservationEffect.NONE:
        return EventClassification.IGNORE

    if observation.effect == ObservationEffect.VIEW:
        return EventClassification.CONTEXT

    if observation.source != ObservationSource.CLIENT or observation.trigger == ObservationTrigger.AUTOMATIC:
        return EventClassification.CONTEXT

    if observation.trigger in USER_TRIGGERS:
        return EventClassification.ACTION

    return EventClassification.CONTEXT
