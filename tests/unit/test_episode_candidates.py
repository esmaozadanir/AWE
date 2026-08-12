"""Episode Candidate Builder: full-chunk + pairwise sıra-korumalı (LCS tabanlı) ortak alt
dizi çıkarımı."""

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
    """İki chunk baştan sona birebir aynıysa, ortak alt dizi tüm diziyi kapsar — bu durumda
    her chunk için YALNIZCA bir FULL_CHUNK adayı üretilmeli, ayrıca çakışan bir
    COMMON_SUBSEQUENCE kopyası eklenmemelidir (regresyon: aksi halde tek gerçek occurrence
    iki kez sayılır)."""

    series_a = make_series("sess1", _NOW, ["open_cart", "checkout"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_cart", "checkout"], series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert len(candidates) == 2
    assert {c.series_id for c in candidates} == {series_a.series_id, series_b.series_id}
    assert all(c.kind == EpisodeCandidateKind.FULL_CHUNK for c in candidates)


def test_common_contiguous_subsequence_across_two_longer_different_chunks_is_extracted():
    # Ortak alt dizi: "open_settings" -> "change_theme". Her iki chunk'ın da farklı giriş/çıkış
    # adımları var, yalnızca bu iki adım ortak (burada zaten ardışık haldeler).
    series_a = make_series(
        "sess1", _NOW, ["open_app", "open_settings", "change_theme", "close_app"], series_suffix="a"
    )
    series_b = make_series(
        "sess2", _NOW, ["open_notifications", "open_settings", "change_theme"], series_suffix="b"
    )
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    common = [c for c in candidates if c.kind == EpisodeCandidateKind.COMMON_SUBSEQUENCE]
    assert len(common) == 2  # bir tanesi series_a içinde, bir tanesi series_b içinde
    for candidate in common:
        assert [s[0] for s in candidate.symbols] == ["open_settings", "change_theme"]

    full_chunks = [c for c in candidates if c.kind == EpisodeCandidateKind.FULL_CHUNK]
    assert len(full_chunks) == 2


def test_common_subsequence_tolerates_a_step_inserted_in_the_middle():
    """Kullanıcı gerçek loglarda aynı davranışı neredeyse hiç birebir aynı, kesintisiz adım
    dizisiyle tekrar etmez (ör. araya bir bildirim kontrolü girer). Sıra korunduğu sürece bu
    ekstra adım ortak deseni bozmamalıdır — yalnızca ardışık (contiguous) eşleşme arayan eski
    algoritma bunu YAKALAYAMAZDI (open_settings sonrası tek adım farkla dizi bozulurdu)."""

    series_a = make_series("sess1", _NOW, ["open_settings", "change_theme"], series_suffix="a")
    series_b = make_series(
        "sess2", _NOW, ["open_settings", "check_notification", "change_theme"], series_suffix="b"
    )
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    common = [c for c in candidates if c.kind == EpisodeCandidateKind.COMMON_SUBSEQUENCE]
    assert len(common) == 1  # series_a'nın kendi LCS pozisyonu kendi FULL_CHUNK'ıyla çakışıp elenir
    (candidate,) = common
    assert candidate.series_id == series_b.series_id
    assert [s[0] for s in candidate.symbols] == ["open_settings", "change_theme"]
    # Pozisyonlar ardışık DEĞİL: index 1 ("check_notification") atlanmış.
    assert candidate.step_indices == (0, 2)


def test_common_subsequence_shorter_than_min_symbols_is_not_extracted():
    series_a = make_series("sess1", _NOW, ["open_app", "shared_step", "close_app"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["open_other", "shared_step", "close_other"], series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert all(c.kind != EpisodeCandidateKind.COMMON_SUBSEQUENCE for c in candidates)


def test_out_of_order_steps_produce_no_common_subsequence():
    """Sıra korunması hâlâ zorunludur — yalnızca contiguity toleransı gevşetildi. A,B sırası
    ile B,A sırası arasında (tekil ortak elemanlar dışında) uzunluk>=2 ortak alt dizi yoktur."""
    series_a = make_series("sess1", _NOW, ["step_a", "step_b"], series_suffix="a")
    series_b = make_series("sess2", _NOW, ["step_b", "step_a"], series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert all(c.kind != EpisodeCandidateKind.COMMON_SUBSEQUENCE for c in candidates)


def test_max_symbols_caps_candidate_length():
    long_flow = [f"step_{i}" for i in range(12)]
    series = make_series("sess1", _NOW, long_flow)
    candidates = build_episode_candidates([series], EpisodeConfig(min_symbols=2, max_symbols=8))

    assert len(candidates) == 1
    assert len(candidates[0].steps) == 8
