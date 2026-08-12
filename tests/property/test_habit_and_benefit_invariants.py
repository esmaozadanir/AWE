"""Bölüm 123: property-based invariant testleri — Habit ve Benefit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from awe.config import default_engine_config
from awe.domain.enums import ObservationEffect, ObservationRole, ObservationStatus
from awe.habit import evaluate_habit
from awe.planner import build_plan_candidates
from tests.support.builders import StepSpec, build_family_from_steps, make_series

_HABIT_CONFIG = default_engine_config().habit
_ENGINE_CONFIG = default_engine_config()
_BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)
_STABLE_TARGET = "contact_1"


@given(
    organic_days=st.integers(min_value=3, max_value=15),
    shortcut_count=st.integers(min_value=0, max_value=15),
)
@settings(max_examples=40)
def test_shortcut_triggered_occurrences_never_count_as_organic_support(organic_days, shortcut_count):
    organic_series = [
        make_series(f"sess-organic-{day}", _BASE + timedelta(days=day), ["A", "B"], series_suffix=f"o{day}")
        for day in range(organic_days)
    ]
    shortcut_series = [
        make_series(
            f"sess-shortcut-{i}",
            _BASE + timedelta(days=1000 + i),
            ["A", "B"],
            has_shortcut_trigger=True,
            series_suffix=f"sc{i}",
        )
        for i in range(shortcut_count)
    ]

    now = _BASE + timedelta(days=max(organic_days, 1))
    result = evaluate_habit("fam", organic_series + shortcut_series, now, "UTC", _HABIT_CONFIG)

    if result.evidence is not None:
        assert result.evidence.organic_occurrences == organic_days
        assert result.evidence.shortcut_utility_occurrences == shortcut_count


@given(retry_failures=st.integers(min_value=0, max_value=6))
@settings(max_examples=30)
def test_server_side_retries_never_inflate_benefit_saved_actions(retry_failures):
    def occurrence():
        steps = [
            StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
            StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=_STABLE_TARGET),
        ]
        for _ in range(retry_failures):
            steps.append(
                StepSpec(
                    action_key="submit",
                    effect=ObservationEffect.SUBMIT,
                    role=ObservationRole.OUTCOME,
                    status=ObservationStatus.FAIL,
                )
            )
        steps.append(
            StepSpec(
                action_key="submit",
                effect=ObservationEffect.SUBMIT,
                role=ObservationRole.OUTCOME,
                status=ObservationStatus.SUCCESS,
            )
        )
        return steps

    occurrences = [occurrence() for _ in range(6)]
    family, series_list = build_family_from_steps(occurrences, _ENGINE_CONFIG, base_time=_BASE)

    from awe.benefit import evaluate_benefit

    candidates = build_plan_candidates(family, series_list, _ENGINE_CONFIG.planner, _ENGINE_CONFIG.risk)
    navigate = next(c for c in candidates if c.plan_type.value == "navigate")
    deepest = max(candidates, key=lambda c: c.anchor.core_position)

    benefit_navigate = evaluate_benefit(navigate, series_list, _ENGINE_CONFIG.benefit)
    benefit_deepest = evaluate_benefit(deepest, series_list, _ENGINE_CONFIG.benefit)

    # submit adımı role=outcome'dur (kullanıcı eylemi değildir); retry sayısı ne olursa olsun
    # yalnızca open_form ve select_recipient (role=action) "kaydedilen eylem" sayılır.
    assert benefit_navigate.median_saved_actions == 1.0
    assert benefit_deepest.median_saved_actions == 2.0
