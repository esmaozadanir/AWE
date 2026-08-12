"""Episode Candidate Builder (bölüm 6.4): full-chunk + pairwise-maximal exact contiguous
common-run çıkarımı."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config.engine_config import EpisodeConfig
from awe.domain.enums import EpisodeCandidateKind
from awe.episodes import build_episode_candidates
from tests.support.builders import make_series

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_CONFIG = EpisodeConfig(min_symbols=2, max_symbols=8)


def test_single_chunk_produces_one_full_chunk_candidate():
    series = make_series("sess1", _NOW, ["open_cart", "checkout", "confirm"])
    candidates = build_episode_candidates([series], _CONFIG)

    assert len(candidates) == 1
    assert candidates[0].kind == EpisodeCandidateKind.FULL_CHUNK
    assert [s[0] for s in candidates[0].symbols] == ["open_cart", "checkout", "confirm"]


def test_chunk_shorter_than_min_symbols_produces_no_candidate():
    series = make_series("sess1", _NOW, ["single_action"])
    assert build_episode_candidates([series], EpisodeConfig(min_symbols=2, max_symbols=8)) == []


def test_identical_full_chunks_do_not_double_count_the_same_occurrence():
    """İki chunk baştan sona birebir aynıysa, pairwise-maximal ortak koşu tüm diziyi kapsar —
    bu durumda her chunk için YALNIZCA bir FULL_CHUNK adayı üretilmeli, ayrıca çakışan bir
    COMMON_RUN kopyası eklenmemelidir (regresyon: aksi halde tek gerçek occurrence iki kez
    sayılır)."""

    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_cart", "checkout"], series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert len(candidates) == 2
    assert {c.series_id for c in candidates} == {series_a.series_id, series_b.series_id}
    assert all(c.kind == EpisodeCandidateKind.FULL_CHUNK for c in candidates)


def test_common_contiguous_run_across_two_longer_different_chunks_is_extracted():
    # Ortak alt dizi: "open_settings" -> "change_theme". Her iki chunk'ın da farklı giriş/çıkış
    # adımları var, yalnızca bu iki adım ortak.
    series_a = make_series(
        "sess1", _NOW, ["open_app", "open_settings", "change_theme", "close_app"], series_suffix="a"
    )
    series_b = make_series(
        "sess2", _NOW, ["open_notifications", "open_settings", "change_theme"], series_suffix="b"
    )
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    common_runs = [c for c in candidates if c.kind == EpisodeCandidateKind.COMMON_RUN]
    assert len(common_runs) == 2  # bir tanesi series_a içinde, bir tanesi series_b içinde
    for candidate in common_runs:
        assert [s[0] for s in candidate.symbols] == ["open_settings", "change_theme"]

    full_chunks = [c for c in candidates if c.kind == EpisodeCandidateKind.FULL_CHUNK]
    assert len(full_chunks) == 2


def test_common_run_shorter_than_min_symbols_is_not_extracted():
    series_a = make_series("sess1", _NOW, ["open_app", "shared_step", "close_app"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_other", "shared_step", "close_other"], series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert all(c.kind != EpisodeCandidateKind.COMMON_RUN for c in candidates)


def test_max_symbols_caps_candidate_length():
    long_flow = [f"step_{i}" for i in range(12)]
    series = make_series("sess1", _NOW, long_flow)
    candidates = build_episode_candidates([series], EpisodeConfig(min_symbols=2, max_symbols=8))

    assert len(candidates) == 1
    assert len(candidates[0].steps) == 8
