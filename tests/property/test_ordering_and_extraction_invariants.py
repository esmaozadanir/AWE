"""Bölüm 123: property-based invariant testleri — Ordering ve O-Series extraction."""

from __future__ import annotations

import string
from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from awe.config import default_engine_config
from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.domain.observation import Observation, ObservationQuality
from awe.ordering import order_session
from awe.series import extract_series

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_ACTION_ALPHABET = st.text(alphabet=string.ascii_uppercase, min_size=1, max_size=3)


def _observation(
    action_key: str,
    index: int,
    *,
    role: ObservationRole = ObservationRole.ACTION,
    effect: ObservationEffect = ObservationEffect.ROUTE,
    trigger: ObservationTrigger = ObservationTrigger.BUTTON,
) -> Observation:
    return Observation(
        event_id=f"evt{index}",
        project_id="proj",
        subject_id="subj",
        session_id="sess",
        timestamp=_BASE_TIME + timedelta(seconds=index),
        source=ObservationSource.CLIENT,
        action=action_key,
        role=role,
        effect=effect,
        trigger=trigger,
        screen="scr",
        widget=None,
        target=None,
        status=ObservationStatus.SUCCESS,
        breaks_episode=False,
        mapping_version="v1",
        quality=ObservationQuality(has_screen=True, has_widget=False, has_session_id=True),
    )


@given(symbols=st.lists(_ACTION_ALPHABET, min_size=1, max_size=8))
@settings(max_examples=50)
def test_session_ordering_is_independent_of_input_batch_order(symbols):
    observations = [_observation(symbol, index) for index, symbol in enumerate(symbols)]

    ordered_forward, _ = order_session(observations)
    ordered_reversed, _ = order_session(list(reversed(observations)))

    assert [o.event_id for o in ordered_forward] == [o.event_id for o in ordered_reversed]


@given(
    symbols=st.lists(_ACTION_ALPHABET, min_size=1, max_size=6, unique=True),
    noise_positions=st.lists(st.integers(min_value=0, max_value=12), max_size=5),
)
@settings(max_examples=50)
def test_inserting_noise_observations_does_not_change_normalized_symbols(symbols, noise_positions):
    config = default_engine_config().family
    base_observations = [_observation(symbol, index) for index, symbol in enumerate(symbols)]
    baseline = extract_series(base_observations, OrderingConfidence.HIGH, config)

    augmented = list(base_observations)
    for offset, position in enumerate(sorted(noise_positions)):
        clamped = min(position, len(augmented))
        # Yapısal olarak IGNORE sınıflanan bir event (bkz. awe.adapter.classification):
        # trigger=scroll, effect'ten bağımsız olarak her zaman dışlanır (PASSIVE_TRIGGERS).
        noise_obs = _observation(
            f"noise{offset}",
            1000 + offset,
            role=ObservationRole.NOISE,
            trigger=ObservationTrigger.SCROLL,
        )
        augmented.insert(clamped, noise_obs)

    noisy = extract_series(augmented, OrderingConfidence.HIGH, config)

    baseline_symbols = tuple(step.symbol for series in baseline for step in series.normalized_steps)
    noisy_symbols = tuple(step.symbol for series in noisy for step in series.normalized_steps)
    assert baseline_symbols == noisy_symbols
