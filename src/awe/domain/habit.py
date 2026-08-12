"""Habit Evaluator'ın kanıt ve karar modelleri (bölüm 6.7).

Değerlendirme, Base Family değil `TargetVariant` seviyesinde yapılır (bölüm 6.6) — farklı
hedefler kanıtlarını havuzlamaz.

`HabitEvidence`, hard-count gate'in (`distinct_sessions`/`distinct_days`) ÜZERİNE, kullanıcı
talebiyle eklenmiş deterministik bir regularity/support katmanı taşır (`cadence`,
`mean_gap_days`, `gap_regularity`, `active_days_total`, `support_ratio` — bkz.
docs/engine-decisions.md #7). Bu, spesifikasyonun "regularity/entropy/lift gibi gelişmiş
istatistikler ... MVP dışında bırakılmıştır" (bölüm 6.7) sınırının kasıtlı, kapsamı sınırlı bir
aşımıdır: hiçbiri yeni bir hard gate DEĞİLDİR, `HABIT_DETECTED` kararını etkilemez ve Selector
sıralamasına (`awe.selection.selector._ranking_key`) girmez — yalnızca kalıcı kanıt vektörüne
eklenip görünürlük/gelecekteki kullanım için taşınır.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import HabitCadence, HabitDecision, ReasonCode


@dataclass(frozen=True, slots=True)
class StatusVector:
    success: int
    fail: int
    cancel: int
    unknown: int

    @property
    def total(self) -> int:
        return self.success + self.fail + self.cancel + self.unknown


@dataclass(frozen=True, slots=True)
class HabitEvidence:
    organic_occurrences: int
    """trigger=shortcut olan occurrence'lar hariç (bölüm 6.7, kısayol kullanımı organik kanıt
    sayılmaz — bkz. `ObservationTrigger.SHORTCUT` docstring'i)."""
    distinct_sessions: int
    distinct_days: int

    first_seen_at: datetime
    last_seen_at: datetime

    status_vector: StatusVector
    """Fail/cancel occurrence'lar sayımdan çıkarılmaz (bölüm 6.7) — yalnızca burada dağılım
    olarak kayıt altına alınır."""

    active_days_total: int
    """Bu variant'ın kendi `[first_seen_at, last_seen_at]` penceresi İÇİNDE, subject'in TÜM
    session'larından (yalnızca bu pattern değil) gelen distinct aktif gün sayısı — proje zaman
    diliminde (bkz. `awe.habit.assessment`). `support_ratio`'nun paydası; pencere bu pattern'in
    kendi ilk/son gözlem tarihinden türediği için her zaman >= `distinct_days` (bkz.
    docs/engine-decisions.md #7)."""

    support_ratio: float
    """`distinct_days / active_days_total`. 1.0: subject'in bu penceredeki HER aktif günü bu
    pattern'i içeriyor. Düşük değer: subject sık aktif ama bu pattern yalnızca bir azınlık
    günde görülüyor. Tek başına bir gate DEĞİLDİR."""

    mean_gap_days: float
    """Sıralı distinct günler arası ardışık farkların aritmetik ortalaması."""

    gap_regularity: float
    """`max(0, 1 - coefficient_of_variation)`, `[0, 1]`. 1.0: sabit aralık. Tek bir gap'te (2
    distinct gün) matematiksel olarak 1.0'dır (popülasyon stdev'i tek örnekte 0'dır, "tanımsız"
    değil) — ince kanıtlı bir pattern'in DAILY etiketlenmesine yol açabilir; kasıtlı ve
    belgelenmiş bir düşük-güven durumu (bkz. docs/engine-decisions.md #7)."""

    cadence: HabitCadence
    """`mean_gap_days` + `gap_regularity`'den türetilen, salt açıklanabilirlik amaçlı kaba
    periyodiklik etiketi — ne bir gate ne Selector girdisidir."""


@dataclass(frozen=True, slots=True)
class HabitAssessment:
    variant_id: str
    """Değerlendirilen `TargetVariant.variant_id`."""
    decision: HabitDecision
    evidence: HabitEvidence | None
    reason_codes: tuple[ReasonCode, ...] = ()
