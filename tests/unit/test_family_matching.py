"""Exact Base Family (bölüm 6.5): tamamen aynı `(action, effect, screen, mapping_version)`
dizisini paylaşan occurrence'ların gruplanması. Fuzzy benzerlik yoktur."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.domain.enums import EpisodeCandidateKind
from awe.domain.episode import EpisodeCandidate
from awe.families import compute_family_id, group_into_families
from tests.support.builders import make_series

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


def test_identical_symbol_sequences_land_in_the_same_family():
    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_cart", "checkout"], series_suffix="b")
    families = group_into_families([_candidate_from(series_a), _candidate_from(series_b)])

    assert len(families) == 1
    assert set(families[0].occurrence_ids) == {f"{series_a.series_id}:full", f"{series_b.series_id}:full"}


def test_different_symbol_sequences_land_in_different_families():
    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_settings", "change_theme"], series_suffix="b")
    families = group_into_families([_candidate_from(series_a), _candidate_from(series_b)])

    assert len(families) == 2
    assert families[0].family_id != families[1].family_id


def test_a_single_extra_step_fragments_the_family_no_fuzzy_tolerance():
    """Bölüm 6.4: 'Fuzzy merge yoktur. Optional step toleransı yoktur.' — tek bir ekstra adım
    bile ayrı bir family üretir (bölüm 9.3'te kabul edilen bilinçli bir ödünleşim)."""
    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_cart", "apply_coupon", "checkout"], series_suffix="b")
    families = group_into_families([_candidate_from(series_a), _candidate_from(series_b)])

    assert len(families) == 2


def test_screen_difference_alone_fragments_the_family():
    """`screen` artık sembolün parçasıdır (bölüm 6.5) — eski tasarımdan farklı olarak ekran
    farkı tek başına family kimliğini böler."""
    from tests.support.builders import StepSpec, make_series_from_steps

    series_a = make_series_from_steps(
        "sess1", _NOW, [StepSpec(action="open_item", screen="catalog")], series_suffix="a"
    )
    series_b = make_series_from_steps(
        "sess2", _NOW, [StepSpec(action="open_item", screen="search_results")], series_suffix="b"
    )
    families = group_into_families([_candidate_from(series_a), _candidate_from(series_b)])

    assert len(families) == 2


def test_family_id_is_deterministic_across_calls():
    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    symbols = series_a.symbols
    first = compute_family_id("project", "subject", symbols)
    second = compute_family_id("project", "subject", symbols)
    assert first == second


def test_family_id_differs_across_subjects_for_the_same_symbols():
    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    symbols = series_a.symbols
    assert compute_family_id("project", "subject_a", symbols) != compute_family_id("project", "subject_b", symbols)


def test_empty_candidate_list_produces_no_families():
    assert group_into_families([]) == []
