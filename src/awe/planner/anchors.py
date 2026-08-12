"""Family core sırasından NAVIGATE/PREFILL adayları için yapısal anchor seçimi.

`destination` kavramı yoktur (bölüm 70); anchor yalnızca family core'undaki bir sembol
referansıdır. Bir anchor, canonical `effect` politikası BLOCKED olan bir sembolde asla
oluşturulmaz — bu, Risk katmanından önce Planner seviyesinde uygulanan yapısal bir güvenlik
kısıtıdır (bölüm 80); Risk katmanı ayrıca kendi kanıt tabanlı kararını bağımsız olarak verir.
"""

from __future__ import annotations

from collections import Counter

from awe.config.engine_config import RiskConfig
from awe.domain.enums import EffectPolicy, ObservationEffect
from awe.domain.family import BehaviorFamily
from awe.domain.plan import ShortcutAnchor
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol

_NAVIGATE_EFFECTS = (ObservationEffect.ROUTE, ObservationEffect.OPEN_MODAL)
_PREFILL_EFFECTS = (
    ObservationEffect.INPUT,
    ObservationEffect.SELECT,
    ObservationEffect.PREPARE,
    ObservationEffect.UPDATE,
)
_TERMINAL_EFFECTS = (ObservationEffect.SUBMIT, ObservationEffect.CONFIRM)


def _effect_of(symbol: Symbol) -> ObservationEffect:
    return ObservationEffect(symbol[1])


def _is_anchorable(symbol: Symbol, effect_policy: dict[ObservationEffect, EffectPolicy]) -> bool:
    effect = _effect_of(symbol)
    if effect in _TERMINAL_EFFECTS:
        return False
    return effect_policy.get(effect, EffectPolicy.REVIEW) != EffectPolicy.BLOCKED


def _representative_screen(core: list[Symbol], position: int, member_series: list[OSeries]) -> str | None:
    symbol = core[position]
    screens = [
        step.screen
        for series in member_series
        for step in series.normalized_steps
        if step.symbol == symbol and step.screen is not None
    ]
    if not screens:
        return None
    return Counter(screens).most_common(1)[0][0]


def _build_anchor(core: list[Symbol], position: int, member_series: list[OSeries]) -> ShortcutAnchor:
    return ShortcutAnchor(
        symbol=core[position],
        screen=_representative_screen(core, position, member_series),
        core_position=position,
    )


def select_navigate_anchors(
    family: BehaviorFamily, member_series: list[OSeries], risk_config: RiskConfig
) -> list[ShortcutAnchor]:
    core = family.core_symbols_in_order
    positions = [
        i
        for i, symbol in enumerate(core)
        if _effect_of(symbol) in _NAVIGATE_EFFECTS and _is_anchorable(symbol, risk_config.effect_policy)
    ]
    if not positions:
        return []
    selected = {positions[0], positions[-1]}
    return [_build_anchor(core, position, member_series) for position in sorted(selected)]


def select_prefill_anchors(
    family: BehaviorFamily, member_series: list[OSeries], risk_config: RiskConfig
) -> list[ShortcutAnchor]:
    core = family.core_symbols_in_order
    anchorable = [i for i, symbol in enumerate(core) if _is_anchorable(symbol, risk_config.effect_policy)]
    if not anchorable:
        return []

    positions = {i for i in anchorable if _effect_of(core[i]) in _PREFILL_EFFECTS}
    positions.add(max(anchorable))
    return [_build_anchor(core, position, member_series) for position in sorted(positions)]
