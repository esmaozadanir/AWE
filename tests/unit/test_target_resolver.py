"""Target Resolver (bölüm 6.6): Base Family occurrence'larını target fingerprint ile böler."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.domain.enums import EpisodeCandidateKind, TargetVariantKind
from awe.domain.episode import EpisodeCandidate
from awe.families import group_into_families
from awe.targeting import resolve_targets
from tests.support.builders import StepSpec, make_series_from_steps

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _candidate_from(series, suffix="full") -> EpisodeCandidate:
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:{suffix}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=EpisodeCandidateKind.FULL_CHUNK,
        steps=series.steps,
        start_index=0,
        observed_at=series.started_at,
        entry_trigger=series.entry_trigger,
        has_shortcut_trigger=series.has_shortcut_trigger,
        final_status=series.final_status,
    )


def _family_and_candidates(steps_per_occurrence: list[list[StepSpec]]):
    candidates_by_id = {}
    candidates = []
    for index, steps in enumerate(steps_per_occurrence):
        series = make_series_from_steps(f"sess{index}", _NOW, steps, series_suffix=str(index))
        candidate = _candidate_from(series)
        candidates.append(candidate)
        candidates_by_id[candidate.candidate_id] = candidate
    families = group_into_families(candidates)
    assert len(families) == 1
    return families[0], candidates_by_id


def test_all_null_targets_produce_no_explicit_target():
    family, candidates_by_id = _family_and_candidates(
        [[StepSpec(action="open_home")], [StepSpec(action="open_home")]]
    )
    variants = resolve_targets(family, candidates_by_id)

    assert len(variants) == 1
    assert variants[0].kind == TargetVariantKind.NO_EXPLICIT_TARGET


def test_consistent_single_target_produces_fixed_target():
    family, candidates_by_id = _family_and_candidates(
        [
            [StepSpec(action="open_course", target="course_42")],
            [StepSpec(action="open_course", target="course_42")],
            [StepSpec(action="open_course", target="course_42")],
        ]
    )
    variants = resolve_targets(family, candidates_by_id)

    assert len(variants) == 1
    assert variants[0].kind == TargetVariantKind.FIXED_TARGET
    assert variants[0].single_target == "course_42"
    assert variants[0].support == 3


def test_different_targets_split_into_separate_variants_without_pooling():
    """course_42 üç kez, course_17 bir kez görülse bile kanıtları havuzlanmaz (bölüm 6.6)."""
    family, candidates_by_id = _family_and_candidates(
        [
            [StepSpec(action="open_course", target="course_42")],
            [StepSpec(action="open_course", target="course_42")],
            [StepSpec(action="open_course", target="course_42")],
            [StepSpec(action="open_course", target="course_17")],
        ]
    )
    variants = resolve_targets(family, candidates_by_id)
    variants_by_target = {v.single_target: v for v in variants}

    assert len(variants) == 2
    assert variants_by_target["course_42"].support == 3
    assert variants_by_target["course_17"].support == 1


def test_occurrence_touching_two_distinct_targets_is_variable_target():
    family, candidates_by_id = _family_and_candidates(
        [
            [
                StepSpec(action="compare_start", target="item_a"),
                StepSpec(action="compare_add", target="item_b"),
            ]
        ]
    )
    variants = resolve_targets(family, candidates_by_id)

    assert len(variants) == 1
    assert variants[0].kind == TargetVariantKind.VARIABLE_TARGET
    assert variants[0].single_target is None


def test_missing_target_field_produces_unknown_target():
    family, candidates_by_id = _family_and_candidates(
        [[StepSpec(action="open_course", target=None, target_unknown=True)]]
    )
    variants = resolve_targets(family, candidates_by_id)

    assert len(variants) == 1
    assert variants[0].kind == TargetVariantKind.UNKNOWN_TARGET
