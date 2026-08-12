"""Benefit: shortcut kullanıcının gerçek manuel işinden ne kadarını kaldırıyor (bölüm 84-89).

Ham event sayısı değil, yalnızca `role=action` (gerçek kullanıcı eylemi) adımları sayılır
(bölüm 85). Retry ve bounded detour'lar zaten O-Series normalizasyonunda tek adıma
sıkıştırıldığı için (bölüm 87) burada ayrıca bir düzeltme yapmaya gerek yoktur — misclick ve
teknik retry'ler Benefit'i suni biçimde şişirmez.
"""

from __future__ import annotations

import statistics

from awe.config.engine_config import BenefitConfig
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import ObservationRole
from awe.domain.plan import PlanCandidate
from awe.domain.series import OSeries
from awe.planner.state_reconstruction import resolve_anchor_step_index


def _saved_user_actions(series: OSeries, anchor_symbol: tuple[str, str]) -> int | None:
    anchor_index = resolve_anchor_step_index(series, anchor_symbol)
    if anchor_index is None:
        return None
    prefix = series.normalized_steps[: anchor_index + 1]
    return sum(
        1
        for step in prefix
        if series.raw_observations[step.observation_index].role == ObservationRole.ACTION
    )


def _quartiles(values: list[int]) -> tuple[float, float, float]:
    if len(values) == 1:
        only = float(values[0])
        return only, only, only
    p25, _, p75 = statistics.quantiles(values, n=4, method="inclusive")
    return p25, statistics.median(values), p75


def evaluate_benefit(
    candidate: PlanCandidate,
    member_series: list[OSeries],
    config: BenefitConfig,
) -> BenefitEvidence:
    observed = [
        value
        for series in member_series
        if (value := _saved_user_actions(series, candidate.anchor.symbol)) is not None
    ]

    total_considered = len(member_series) or 1
    benefit_coverage = len(observed) / total_considered

    if not observed:
        return BenefitEvidence(
            plan_id=candidate.plan_id,
            median_saved_actions=0.0,
            p25_saved_actions=0.0,
            p75_saved_actions=0.0,
            benefit_coverage=0.0,
            sample_size=0,
            meets_minimum=False,
        )

    p25, median, p75 = _quartiles(observed)
    meets_minimum = median >= config.min_median_saved_actions and benefit_coverage >= config.min_benefit_coverage

    return BenefitEvidence(
        plan_id=candidate.plan_id,
        median_saved_actions=median,
        p25_saved_actions=p25,
        p75_saved_actions=p75,
        benefit_coverage=benefit_coverage,
        sample_size=len(observed),
        meets_minimum=meets_minimum,
    )
