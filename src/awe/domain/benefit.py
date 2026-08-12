"""Benefit Evaluator'ın kanıt modeli (bölüm 6.14).

`observed_actions - planned_actions` deterministik farkıdır; eski tasarımın medyan/p25/p75
popülasyon istatistiği yoktur — her Shortcut Intent kendi tek Benefit değerini taşır.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import BenefitLevel


@dataclass(frozen=True, slots=True)
class BenefitEvidence:
    intent_id: str
    observed_actions: int
    planned_actions: int

    @property
    def saved_actions(self) -> int:
        return self.observed_actions - self.planned_actions

    @property
    def level(self) -> BenefitLevel:
        if self.saved_actions < 0:
            return BenefitLevel.NEGATIVE
        if self.saved_actions == 0:
            return BenefitLevel.NONE
        if self.saved_actions == 1:
            return BenefitLevel.LIMITED
        return BenefitLevel.CLEAR
