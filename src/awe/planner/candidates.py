"""Shortcut Planner: Habit'ten NAVIGATE/PREFILL PlanCandidate üretimi (bölüm 69-72).

Bu katman Risk veya Benefit kararı vermez; yalnızca güvenli biçimde önerilebilecek yapısal
adayları üretir. Bir Family, biri erken biri derin olmak üzere birden fazla NAVIGATE adayı ve
kısmi/derin birden fazla PREFILL adayı üretebilir — erken tek bir kazanan seçilmez (bölüm 72).
"""

from __future__ import annotations

from awe.config.engine_config import PlannerConfig, RiskConfig
from awe.domain.enums import PlanType
from awe.domain.family import BehaviorFamily
from awe.domain.plan import PlanCandidate, ShortcutAnchor
from awe.domain.series import OSeries
from awe.planner.anchors import select_navigate_anchors, select_prefill_anchors
from awe.planner.state_reconstruction import (
    TARGET_FIELD_NAME,
    compute_field_bindings,
    resolve_anchor_step_index,
)


def _plan_id(family_id: str, plan_type: PlanType, anchor: ShortcutAnchor) -> str:
    return f"{family_id}:{plan_type.value}:{anchor.core_position}"


def _build_candidate(
    family_id: str,
    plan_type: PlanType,
    anchor: ShortcutAnchor,
    member_series: list[OSeries],
    planner_config: PlannerConfig,
    include_parameter_bindings: bool,
) -> PlanCandidate | None:
    supporting_occurrences = sum(
        1 for series in member_series if resolve_anchor_step_index(series, anchor.symbol) is not None
    )
    if supporting_occurrences == 0:
        return None

    all_bindings = compute_field_bindings(member_series, anchor.symbol, planner_config)
    if include_parameter_bindings and not all_bindings:
        # PREFILL'in prefill edecek hiçbir alanı yoksa NAVIGATE'ten farksız, zayıf bir
        # kopya üretmek yerine bu adayı hiç oluşturmuyoruz.
        return None

    target_binding = next((b for b in all_bindings if b.field_name == TARGET_FIELD_NAME), None)
    parameter_bindings = tuple(b for b in all_bindings if b.field_name != TARGET_FIELD_NAME)
    if not include_parameter_bindings:
        parameter_bindings = ()

    return PlanCandidate(
        plan_id=_plan_id(family_id, plan_type, anchor),
        family_id=family_id,
        plan_type=plan_type,
        anchor=anchor,
        bindings=parameter_bindings,
        target_binding=target_binding,
        supporting_occurrences=supporting_occurrences,
    )


def build_plan_candidates(
    family: BehaviorFamily,
    member_series: list[OSeries],
    planner_config: PlannerConfig,
    risk_config: RiskConfig,
) -> list[PlanCandidate]:
    if not member_series:
        return []

    candidates: list[PlanCandidate] = []

    for anchor in select_navigate_anchors(family, member_series, risk_config):
        candidate = _build_candidate(
            family.family_id, PlanType.NAVIGATE, anchor, member_series, planner_config, False
        )
        if candidate is not None:
            candidates.append(candidate)

    for anchor in select_prefill_anchors(family, member_series, risk_config):
        candidate = _build_candidate(
            family.family_id, PlanType.PREFILL, anchor, member_series, planner_config, True
        )
        if candidate is not None:
            candidates.append(candidate)

    return candidates
