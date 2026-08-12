"""Anchor öncesi canonical state çıkarımı ve field binding istatistikleri (bölüm 73-77).

PREFILL, gözlenen eventleri yeniden oynatmaz (bölüm 73): burada üretilen değer yalnızca
"kullanıcı bu noktaya kadar tipik olarak hangi state'i kurmuş" sorusuna verilen istatistiksel
bir cevaptır; hiçbir eylem otomatik tetiklenmez.
"""

from __future__ import annotations

from collections import Counter

from awe.config.engine_config import PlannerConfig
from awe.domain.enums import FieldState
from awe.domain.plan import FieldBinding
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol

TARGET_FIELD_NAME = "target"
_NO_TARGET_SENTINEL = "__no_target__"


def resolve_anchor_step_index(series: OSeries, anchor_symbol: Symbol) -> int | None:
    """Anchor'ı index'e değil, sembol eşleşmesine göre çözer (bölüm 71).

    Sembol birden fazla kez görülüyorsa (loop), ilk görülme noktası "bu yapısal adıma ilk
    ulaşım" anını temsil eder ve state reconstruction için referans alınır.
    """

    for index, step in enumerate(series.normalized_steps):
        if step.symbol == anchor_symbol:
            return index
    return None


def extract_state_before_anchor(series: OSeries, anchor_symbol: Symbol) -> dict[str, str] | None:
    anchor_index = resolve_anchor_step_index(series, anchor_symbol)
    if anchor_index is None:
        return None

    state: dict[str, str] = {}
    for step in series.normalized_steps[: anchor_index + 1]:
        observation = series.raw_observations[step.observation_index]
        if observation.target:
            state[TARGET_FIELD_NAME] = observation.target
        elif observation.target == "":
            # Mapping target'ı izliyor ama bu event'in açıkça hedefi yok (ör. "logout") —
            # `None` (mapping hiç izlemiyor/bilinmiyor) durumundan ayırt edilir (bkz.
            # `Observation.target` docstring'i).
            state[TARGET_FIELD_NAME] = _NO_TARGET_SENTINEL
        for key, value in observation.parameters.items():
            state[key] = value
    return state


def compute_field_bindings(
    member_series: list[OSeries], anchor_symbol: Symbol, config: PlannerConfig
) -> tuple[FieldBinding, ...]:
    observed_states = []
    for series in member_series:
        state = extract_state_before_anchor(series, anchor_symbol)
        if state is not None:
            observed_states.append((series, state))

    total_reaching_anchor = len(observed_states)
    if total_reaching_anchor == 0:
        return ()

    field_names: set[str] = set()
    for _, state in observed_states:
        field_names.update(state.keys())

    recent_window = sorted(observed_states, key=lambda item: item[0].started_at, reverse=True)[
        : config.recent_window_size
    ]

    bindings = []
    for field_name in sorted(field_names):
        values = [state[field_name] for _, state in observed_states if field_name in state]
        sample_size = len(values)
        coverage = sample_size / total_reaching_anchor

        counts = Counter(values)
        dominant_value, dominant_count = counts.most_common(1)[0]
        dominance = dominant_count / sample_size

        recent_values = [state[field_name] for _, state in recent_window if field_name in state]
        recent_dominance = None
        if len(recent_values) >= config.min_binding_sample_size:
            recent_counts = Counter(recent_values)
            recent_dominance = recent_counts.most_common(1)[0][1] / len(recent_values)

        if coverage < config.min_coverage_for_known_state or sample_size < config.min_binding_sample_size:
            field_state = FieldState.UNKNOWN
        elif dominance >= config.stable_dominance_threshold:
            field_state = FieldState.STABLE
        else:
            field_state = FieldState.VARIABLE

        bindings.append(
            FieldBinding(
                field_name=field_name,
                state=field_state,
                dominant_value=None if dominant_value == _NO_TARGET_SENTINEL else dominant_value,
                dominance=dominance,
                coverage=coverage,
                sample_size=sample_size,
                recent_dominance=recent_dominance,
            )
        )
    return tuple(bindings)
