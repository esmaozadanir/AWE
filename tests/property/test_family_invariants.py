"""Exact Base Family değişmezleri (bölüm 6.5): hash-tabanlı deterministik gruplamanın
girdi sırasından bağımsız olduğunu ve exact eşitliğin tam olarak uygulandığını doğrular."""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from awe.domain.enums import EpisodeCandidateKind
from awe.domain.episode import EpisodeCandidate
from awe.families import compute_family_id, group_into_families
from tests.support.builders import make_series

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)

_ACTION_NAMES = st.sampled_from(["open_a", "open_b", "open_c", "confirm_x", "select_y"])
_SEQUENCES = st.lists(_ACTION_NAMES, min_size=1, max_size=5)


def _candidate_from(series, suffix) -> EpisodeCandidate:
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


@given(sequences=st.lists(_SEQUENCES, min_size=1, max_size=6))
def test_grouping_is_independent_of_candidate_insertion_order(sequences):
    candidates = [
        _candidate_from(make_series(f"sess{i}", _NOW, actions, series_suffix=str(i)), "full")
        for i, actions in enumerate(sequences)
    ]

    forward = group_into_families(candidates)
    backward = group_into_families(list(reversed(candidates)))

    forward_groups = {f.family_id: sorted(f.occurrence_ids) for f in forward}
    backward_groups = {f.family_id: sorted(f.occurrence_ids) for f in backward}
    assert forward_groups == backward_groups


@given(sequences=st.lists(_SEQUENCES, min_size=1, max_size=6))
def test_every_family_member_shares_the_exact_same_symbol_sequence(sequences):
    candidates = [
        _candidate_from(make_series(f"sess{i}", _NOW, actions, series_suffix=str(i)), "full")
        for i, actions in enumerate(sequences)
    ]
    candidates_by_id = {c.candidate_id: c for c in candidates}

    for family in group_into_families(candidates):
        member_symbol_sets = {candidates_by_id[oid].symbols for oid in family.occurrence_ids}
        assert len(member_symbol_sets) == 1
        assert next(iter(member_symbol_sets)) == family.symbols


@given(a=_SEQUENCES, b=_SEQUENCES)
def test_family_id_equality_matches_symbol_sequence_equality(a, b):
    symbols_a = tuple((action, "route", "screen", "v1") for action in a)
    symbols_b = tuple((action, "route", "screen", "v1") for action in b)

    same_id = compute_family_id("proj", "subj", symbols_a) == compute_family_id("proj", "subj", symbols_b)
    assert same_id == (symbols_a == symbols_b)
