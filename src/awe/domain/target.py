"""Target Resolver çıktı modeli (bölüm 6.6).

Bir Base Family, occurrence'larının target fingerprint'ine (her adımın gözlenen target'ı,
sırayla) göre alt kümelere bölünür. Her exact fingerprint ayrı bir `TargetVariant` olarak
Habit Evaluator'a gider — böylece örn. `course_42` ve `course_17` hedefleri aynı family
içinde görülse bile kanıtları havuzlanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import TargetVariantKind

TargetFingerprint = tuple[str | None, ...]
"""Occurrence içindeki her adımın gözlenen target'ı, adım sırasına göre. `None` = o adımda
açıkça hedef yok (bkz. `Observation.target` semantiği)."""


@dataclass
class TargetVariant:
    variant_id: str
    family_id: str
    kind: TargetVariantKind
    fingerprint: TargetFingerprint

    occurrence_ids: list[str] = field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def support(self) -> int:
        return len(self.occurrence_ids)

    @property
    def single_target(self) -> str | None:
        """Fingerprint'teki tek, boş-olmayan hedef değeri — Shortcut Intent Builder'ın
        `target` alanı için kullanılır. Birden fazla farklı non-null değer varsa (compound
        identity, bölüm 6.12) `None` döner; çağıran bunu `UNSUPPORTED` olarak ele almalıdır."""
        distinct = {value for value in self.fingerprint if value}
        if len(distinct) == 1:
            return next(iter(distinct))
        return None
