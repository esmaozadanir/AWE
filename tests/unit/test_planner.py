"""Anchor Resolver + Scope Projector + Destination Resolver + Shortcut Intent Builder
(bölüm 6.9-6.12), uçtan uca zincir olarak test edilir."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    EpisodeCandidateKind,
    IntentState,
    ObservationEffect,
    PlanMode,
    ReasonCode,
    TargetVariantKind,
)
from awe.domain.episode import EpisodeCandidate
from awe.families import group_into_families
from awe.planner import build_shortcut_intent, project_scope, resolve_anchor, resolve_destination
from awe.targeting import resolve_targets
from tests.support.builders import StepSpec, make_series_from_steps

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_SCREEN_CONFIG = ScreenEvidenceConfig(min_supporting_sessions=2)


def _candidate_from(series, suffix="full") -> EpisodeCandidate:
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:{suffix}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=EpisodeCandidateKind.FULL_CHUNK,
        steps=series.steps,
        step_indices=tuple(range(len(series.steps))),
        observed_at=series.started_at,
        entry_trigger=series.entry_trigger,
        has_shortcut_trigger=series.has_shortcut_trigger,
        final_status=series.final_status,
    )


def _build(occurrences: list[tuple[list[StepSpec], dict[int, list[str]]]]):
    """Her occurrence için `(steps, views_after)` alır; tek family + tek variant (occurrence'lar
    exact aynı sembol dizisini paylaşmalı) + gerekli lookup haritalarını döner."""

    series_list = []
    candidates = []
    candidates_by_id = {}
    series_by_id = {}

    for index, (steps, views_after) in enumerate(occurrences):
        series = make_series_from_steps(
            f"sess{index}", _NOW, steps, series_suffix=str(index), views_after=views_after
        )
        series_list.append(series)
        series_by_id[series.series_id] = series
        candidate = _candidate_from(series)
        candidates.append(candidate)
        candidates_by_id[candidate.candidate_id] = candidate

    families = group_into_families(candidates)
    assert len(families) == 1, f"expected a single exact family, got {len(families)}"
    family = families[0]
    variants = resolve_targets(family, candidates_by_id)
    assert len(variants) == 1, f"expected a single target variant, got {len(variants)}"
    return family, variants[0], candidates_by_id, series_by_id


def test_target_carrying_position_is_a_strong_anchor():
    steps = [
        StepSpec(action="open_courses", effect=ObservationEffect.ROUTE),
        StepSpec(action="open_course", effect=ObservationEffect.ROUTE, target="course_42"),
    ]
    family, variant, candidates_by_id, series_by_id = _build([(steps, {}), (steps, {}), (steps, {})])

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.strength == AnchorStrength.STRONG
    assert anchor.status == AnchorStatus.RESOLVED
    assert anchor.symbol[0] == "open_course"


def test_outcome_evidence_effect_without_target_is_a_medium_anchor():
    steps = [
        StepSpec(action="open_form", effect=ObservationEffect.ROUTE),
        StepSpec(action="submit_form", effect=ObservationEffect.CONFIRM),
    ]
    family, variant, candidates_by_id, series_by_id = _build([(steps, {}), (steps, {}), (steps, {})])

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.strength == AnchorStrength.MEDIUM
    assert anchor.symbol[0] == "submit_form"


def test_route_only_trail_with_stable_post_view_resolves_as_weak_anchor():
    """Bölüm 7'nin uçtan uca örneği: K1(route:home->menu) -> K2(route:menu->reports) ->
    K3(open:reports->daily_report); tamamı route/open, K3 sonrası >=2 session'da aynı ekran
    stabil gözlenir -> K3 WEAK RESOLVED anchor olur."""
    steps = [
        StepSpec(action="k1_open_menu", effect=ObservationEffect.ROUTE, screen="home"),
        StepSpec(action="k2_open_reports", effect=ObservationEffect.ROUTE, screen="menu"),
        StepSpec(action="k3_open_daily_report", effect=ObservationEffect.OPEN, screen="reports"),
    ]
    occurrences = [
        (steps, {2: ["daily_report"]}),
        (steps, {2: ["daily_report"]}),
        (steps, {2: ["daily_report"]}),
    ]
    family, variant, candidates_by_id, series_by_id = _build(occurrences)

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.strength == AnchorStrength.WEAK
    assert anchor.status == AnchorStatus.RESOLVED
    assert anchor.symbol[0] == "k3_open_daily_report"

    scope = project_scope(family.symbols, variant.variant_id, anchor)
    destination = resolve_destination(anchor, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    intent = build_shortcut_intent(variant, anchor, scope, destination)

    assert destination.resolved is True
    assert destination.screen == "daily_report"
    assert intent.state == IntentState.READY
    assert intent.mode == PlanMode.NAVIGATE
    assert intent.target is None
    assert intent.requires_user_confirmation is False


def test_route_only_trail_without_stable_post_view_stays_ambiguous():
    steps = [
        StepSpec(action="k1", effect=ObservationEffect.ROUTE),
        StepSpec(action="k2", effect=ObservationEffect.ROUTE),
    ]
    # Yalnızca bir occurrence -> min_supporting_sessions=2 karşılanmaz.
    family, variant, candidates_by_id, series_by_id = _build([(steps, {1: ["destination_a"]})])

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.status == AnchorStatus.AMBIGUOUS


def test_strong_candidate_followed_by_targetless_route_tail_stays_ambiguous():
    steps = [
        StepSpec(action="submit_order", effect=ObservationEffect.CONFIRM),
        StepSpec(action="go_home", effect=ObservationEffect.ROUTE),
    ]
    family, variant, candidates_by_id, series_by_id = _build([(steps, {}), (steps, {}), (steps, {})])

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.status == AnchorStatus.AMBIGUOUS
    assert ReasonCode.AMBIGUOUS_ANCHOR in anchor.reason_codes


def test_unknown_target_variant_blocks_anchor_resolution():
    family, variant, candidates_by_id, series_by_id = _build(
        [([StepSpec(action="open_item", target=None, target_unknown=True)], {})]
    )
    assert variant.kind == TargetVariantKind.UNKNOWN_TARGET

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.status == AnchorStatus.UNRESOLVED
    assert ReasonCode.UNKNOWN_TARGET_BLOCKS_ANCHOR in anchor.reason_codes


def test_no_successful_occurrence_yields_attempt_only():
    from awe.domain.enums import ObservationStatus

    steps_fail = [StepSpec(action="submit_order", effect=ObservationEffect.CONFIRM, status=ObservationStatus.FAIL)]
    family, variant, candidates_by_id, series_by_id = _build(
        [(steps_fail, {}), (steps_fail, {}), (steps_fail, {})]
    )

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert anchor.status == AnchorStatus.ATTEMPT_ONLY
    assert ReasonCode.ATTEMPT_ONLY in anchor.reason_codes


def test_action_surface_destination_uses_the_anchor_own_screen_not_the_next_screen():
    """Bölüm 6.11 örneği: feedback_form -> submit_feedback -> thank_you. Destination
    `thank_you` DEĞİL `feedback_form` olmalıdır — kısayol submit işlemini yapmaz."""
    steps = [StepSpec(action="submit_feedback", effect=ObservationEffect.SUBMIT, screen="feedback_form")]
    occurrences = [(steps, {0: ["thank_you"]}), (steps, {0: ["thank_you"]}), (steps, {0: ["thank_you"]})]
    family, variant, candidates_by_id, series_by_id = _build(occurrences)

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    destination = resolve_destination(anchor, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)

    assert destination.resolved is True
    assert destination.screen == "feedback_form"


def test_scope_is_empty_when_anchor_is_not_resolvable():
    family, variant, candidates_by_id, series_by_id = _build(
        [([StepSpec(action="open_item", target=None, target_unknown=True)], {})]
    )
    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    scope = project_scope(family.symbols, variant.variant_id, anchor)

    assert scope.is_empty is True


def test_intent_is_unsupported_for_compound_target():
    """Bölüm 6.12: tek `target` alanı compound identity taşıyamaz."""
    steps = [
        StepSpec(action="compare_start", effect=ObservationEffect.ROUTE, target="item_a"),
        StepSpec(action="compare_add", effect=ObservationEffect.SELECT, target="item_b"),
    ]
    family, variant, candidates_by_id, series_by_id = _build([(steps, {}), (steps, {}), (steps, {})])
    assert variant.kind == TargetVariantKind.VARIABLE_TARGET

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    scope = project_scope(family.symbols, variant.variant_id, anchor)
    destination = resolve_destination(anchor, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    intent = build_shortcut_intent(variant, anchor, scope, destination)

    assert intent.state == IntentState.UNSUPPORTED
    assert ReasonCode.UNSUPPORTED_COMPOUND_TARGET in intent.reason_codes


def test_intent_is_unsupported_when_intermediate_step_is_not_route_or_open():
    """Bölüm 6.12 örneği: open_form -> input_name -> input_address -> submit. Motor input
    değerlerini bilmediği için sahte kısayol üretemez."""
    steps = [
        StepSpec(action="open_form", effect=ObservationEffect.ROUTE),
        StepSpec(action="input_name", effect=ObservationEffect.INPUT),
        StepSpec(action="input_address", effect=ObservationEffect.INPUT),
        StepSpec(action="submit_form", effect=ObservationEffect.SUBMIT),
    ]
    family, variant, candidates_by_id, series_by_id = _build([(steps, {}), (steps, {}), (steps, {})])

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    scope = project_scope(family.symbols, variant.variant_id, anchor)
    destination = resolve_destination(anchor, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    intent = build_shortcut_intent(variant, anchor, scope, destination)

    assert intent.state == IntentState.UNSUPPORTED
    assert ReasonCode.UNREPRESENTED_INTERMEDIATE_ACTION in intent.reason_codes


def test_fixed_target_produces_a_ready_prefill_intent_requiring_confirmation():
    steps = [
        StepSpec(action="open_courses", effect=ObservationEffect.ROUTE),
        StepSpec(action="open_course", effect=ObservationEffect.SELECT, target="course_42"),
    ]
    family, variant, candidates_by_id, series_by_id = _build([(steps, {}), (steps, {}), (steps, {})])

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    scope = project_scope(family.symbols, variant.variant_id, anchor)
    destination = resolve_destination(anchor, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    intent = build_shortcut_intent(variant, anchor, scope, destination)

    assert intent.state == IntentState.READY
    assert intent.mode == PlanMode.PREFILL
    assert intent.target == "course_42"
    assert intent.requires_user_confirmation is True
    assert intent.automatic_action.value == "none"
    assert intent.final_action_owner.value == "user"
