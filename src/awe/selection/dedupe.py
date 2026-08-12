"""Family'ler arası aynı yapısal anchor'a düşen çakışan önerilerin ayıklanması (bölüm 91)."""

from __future__ import annotations

from dataclasses import dataclass

from awe.selection.family_selection import FamilySelection


@dataclass(frozen=True, slots=True)
class FamilyPlan:
    family_id: str
    selection: FamilySelection


def _dedupe_key(plan) -> tuple:
    return (plan.anchor.symbol, plan.plan_type)


def dedupe_across_families(family_plans: list[FamilyPlan]) -> tuple[list[FamilyPlan], frozenset[str]]:
    """Aynı (anchor sembolü, plan tipi) çiftine sahip birincil planlardan yalnızca en yüksek
    Benefit'e sahip olanı tutar; geri kalanlar `DUPLICATE_PLAN` olarak dışarıda bırakılır."""

    groups: dict[tuple, list[FamilyPlan]] = {}
    for plan in family_plans:
        key = _dedupe_key(plan.selection.primary.candidate)
        groups.setdefault(key, []).append(plan)

    kept: list[FamilyPlan] = []
    duplicate_plan_ids: set[str] = set()
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue
        group.sort(key=lambda p: p.selection.primary.benefit.median_saved_actions, reverse=True)
        kept.append(group[0])
        duplicate_plan_ids.update(p.selection.primary.candidate.plan_id for p in group[1:])

    return kept, frozenset(duplicate_plan_ids)
