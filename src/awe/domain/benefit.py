"""Benefit katmanının kanıt modeli (bölüm 84-89)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenefitEvidence:
    plan_id: str
    median_saved_actions: float
    p25_saved_actions: float
    p75_saved_actions: float
    benefit_coverage: float
    sample_size: int
    meets_minimum: bool
