"""Bölüm 117'deki PREFILL test matrisinin uçtan uca doğrulaması."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config import default_engine_config
from awe.domain.enums import FieldState, ObservationEffect, PlanType
from awe.planner import build_plan_candidates
from tests.support.builders import StepSpec, build_family_from_steps

_CONFIG = default_engine_config()
_BASE = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


def _build_family_and_series(steps_per_occurrence: list[list[StepSpec]]):
    return build_family_from_steps(steps_per_occurrence, _CONFIG, base_time=_BASE)


def _standard_steps(*, target: str | None, amount: str | None) -> list[StepSpec]:
    # `enter_amount` adımı her occurrence'ta gerçekleşir (family sembol dizisi sabit kalır);
    # yalnızca adapter'ın `amount` değerini yakalayıp yakalamadığı değişir. Bu, "adım hiç
    # gerçekleşmedi" (opsiyonel adım) ile "adım gerçekleşti ama alan kaydedilemedi" (düşük
    # coverage) durumlarını doğru biçimde birbirinden ayırır.
    steps = [
        StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
        StepSpec(action_key="select_recipient", effect=ObservationEffect.SELECT, target=target),
        StepSpec(
            action_key="enter_amount",
            effect=ObservationEffect.INPUT,
            parameters={"amount": amount} if amount is not None else {},
        ),
    ]
    steps.append(StepSpec(action_key="review_submit", effect=ObservationEffect.SUBMIT))
    return steps


def test_stable_target_with_variable_parameter_produces_partial_and_deep_prefill():
    stable_target = "contact_1"
    occurrences = [
        _standard_steps(target=stable_target, amount=amount)
        for amount in ["100", "250", "175", "300", "120"]
    ]
    family, series_list = _build_family_and_series(occurrences)

    candidates = build_plan_candidates(family, series_list, _CONFIG.planner, _CONFIG.risk)
    prefill_candidates = [c for c in candidates if c.plan_type == PlanType.PREFILL]

    assert len(prefill_candidates) == 2
    deep = max(prefill_candidates, key=lambda c: c.anchor.core_position)
    assert deep.target_binding is not None
    assert deep.target_binding.state == FieldState.STABLE
    assert deep.target_binding.dominant_value == "contact_1"

    amount_binding = next(b for b in deep.bindings if b.field_name == "amount")
    assert amount_binding.state == FieldState.VARIABLE


def test_unknown_target_never_becomes_a_confident_binding():
    occurrences = [_standard_steps(target=None, amount="100") for _ in range(5)]
    family, series_list = _build_family_and_series(occurrences)

    candidates = build_plan_candidates(family, series_list, _CONFIG.planner, _CONFIG.risk)
    deep = max(
        (c for c in candidates if c.plan_type == PlanType.PREFILL), key=lambda c: c.anchor.core_position
    )

    assert deep.target_binding is None


def test_low_coverage_field_is_marked_unknown_rather_than_stable():
    present = "contact_1"
    occurrences = [_standard_steps(target=present, amount="100") for _ in range(2)] + [
        _standard_steps(target=present, amount=None) for _ in range(5)
    ]
    family, series_list = _build_family_and_series(occurrences)

    candidates = build_plan_candidates(family, series_list, _CONFIG.planner, _CONFIG.risk)
    deep = max(
        (c for c in candidates if c.plan_type == PlanType.PREFILL), key=lambda c: c.anchor.core_position
    )

    amount_binding = next((b for b in deep.bindings if b.field_name == "amount"), None)
    assert amount_binding is not None
    assert amount_binding.coverage < 0.5
    assert amount_binding.state == FieldState.UNKNOWN


def test_small_sample_size_prevents_confident_stable_classification():
    present = "contact_1"
    occurrences = [_standard_steps(target=present, amount="100") for _ in range(2)]
    family, series_list = _build_family_and_series(occurrences)

    candidates = build_plan_candidates(family, series_list, _CONFIG.planner, _CONFIG.risk)
    deep = max(
        (c for c in candidates if c.plan_type == PlanType.PREFILL), key=lambda c: c.anchor.core_position
    )

    assert deep.target_binding.sample_size < _CONFIG.planner.min_binding_sample_size
    assert deep.target_binding.state == FieldState.UNKNOWN


def test_navigate_candidate_is_generated_for_entry_screen():
    present = "contact_1"
    occurrences = [_standard_steps(target=present, amount="100") for _ in range(5)]
    family, series_list = _build_family_and_series(occurrences)

    candidates = build_plan_candidates(family, series_list, _CONFIG.planner, _CONFIG.risk)
    navigate_candidates = [c for c in candidates if c.plan_type == PlanType.NAVIGATE]

    assert len(navigate_candidates) >= 1
    assert all(not c.bindings for c in navigate_candidates)
