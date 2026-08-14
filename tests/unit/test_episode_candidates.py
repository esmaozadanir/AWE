"""Episode Candidate Builder: full-chunk + pairwise sıra-korumalı (LCS tabanlı) ortak alt
dizi çıkarımı."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config.engine_config import EpisodeConfig
from awe.domain.enums import EpisodeCandidateKind, ObservationEffect, ObservationStatus, ObservationTrigger
from awe.episodes import build_episode_candidates
from tests.support.builders import StepSpec, make_series, make_series_from_steps

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


def test_default_config_does_not_cap_candidate_length():
    """max_symbols varsayılanı artık None (sınırsız) -- kullanıcı kararıyla kaldırıldı (bkz.
    docs/engine-decisions.md). Gerçek uzun bir davranış akışı istenmeden kesilmemeli."""
    long_flow = [f"step_{i}" for i in range(12)]
    series = make_series("sess1", _NOW, long_flow)
    candidates = build_episode_candidates([series], EpisodeConfig(min_symbols=2))

    assert len(candidates) == 1
    assert len(candidates[0].steps) == 12


# --- "Endpoint hypothesis" segmentasyonu (bkz. docs/engine-decisions.md #10) -------------------
# Strong pozisyon = target-carrying ya da outcome-evidence effect'li adım. Reddedilen ilk
# tasarım (chunk'ı strong pozisyonlarda AYRIK span'lara bölmek) gerçek referans verisini
# kırıyordu -- aşağıdaki testler seçilen "çakışan önek hipotezleri" tasarımını doğrular.


def test_two_independent_strong_positions_produce_two_overlapping_candidates_neither_invalidating_the_other():
    """Farklı hedefli iki bağımsız strong pozisyon (place_order, sonra alakasız
    track_shipment) BİRBİRİNİ GEÇERSİZ KILMAMALI -- ikisi de kendi (çakışan) adayını almalı."""
    steps = [
        StepSpec(action="browse", effect=ObservationEffect.ROUTE),
        StepSpec(action="place_order", effect=ObservationEffect.CONFIRM, target="order_9"),
        StepSpec(action="open_reports", effect=ObservationEffect.ROUTE),
        StepSpec(action="track_shipment", effect=ObservationEffect.SELECT, target="shipment_4"),
    ]
    series = make_series_from_steps("sess1", _NOW, steps)
    candidates = build_episode_candidates([series], _CONFIG)

    assert len(candidates) == 2
    assert all(c.kind == EpisodeCandidateKind.EPISODE_SPAN for c in candidates)
    by_indices = sorted(candidates, key=lambda c: c.step_indices)
    assert by_indices[0].step_indices == (0, 1)
    assert [s[0] for s in by_indices[0].symbols] == ["browse", "place_order"]
    assert by_indices[1].step_indices == (0, 1, 2, 3)
    assert [s[0] for s in by_indices[1].symbols] == ["browse", "place_order", "open_reports", "track_shipment"]


def test_adjacent_strong_positions_sharing_the_same_target_both_survive():
    """Gerçekçi LearnLoop Pattern A şekli: open_course(target=X) hemen ardından
    continue_lesson(AYNI target=X). Reddedilen "ayrık span" tasarımında bu, continue_lesson'ı
    tek başına uzunluk-1 bırakıp TAMAMEN kaybederdi -- bu projenin asıl referans alışkanlığı.
    Endpoint-hypothesis tasarımında ikisi de (çakışarak) hayatta kalır."""
    steps = [
        StepSpec(action="open_my_courses", effect=ObservationEffect.ROUTE),
        StepSpec(action="open_course", effect=ObservationEffect.ROUTE, target="course_ds301"),
        StepSpec(action="continue_lesson", effect=ObservationEffect.OPEN, target="course_ds301"),
    ]
    series = make_series_from_steps("sess1", _NOW, steps)
    candidates = build_episode_candidates([series], _CONFIG)

    assert len(candidates) == 2
    assert all(c.kind == EpisodeCandidateKind.EPISODE_SPAN for c in candidates)
    by_indices = sorted(candidates, key=lambda c: c.step_indices)
    assert by_indices[0].step_indices == (0, 1)
    assert by_indices[1].step_indices == (0, 1, 2)
    assert set(by_indices[1].targets) == {None, "course_ds301"}


def test_adjacent_strong_positions_where_the_second_carries_no_target_both_survive():
    """awe.testing.generators._STANDARD_FLOW şekli: select_option(target=X) hemen ardından
    confirm_action (target YOK ama outcome-evidence effect). confirm_action'ın kendi target'ı
    olmaması yeni bir farklı hedefe geçildiği anlamına gelmez -- reddedilen tasarımda bu da
    confirm_action'ı tek başına kaybederdi."""
    steps = [
        StepSpec(action="open_dashboard", effect=ObservationEffect.ROUTE),
        StepSpec(action="open_detail", effect=ObservationEffect.ROUTE),
        StepSpec(action="select_option", effect=ObservationEffect.SELECT, target="item_1"),
        StepSpec(action="confirm_action", effect=ObservationEffect.CONFIRM),
    ]
    series = make_series_from_steps("sess1", _NOW, steps)
    candidates = build_episode_candidates([series], _CONFIG)

    assert len(candidates) == 2
    by_indices = sorted(candidates, key=lambda c: c.step_indices)
    assert by_indices[0].step_indices == (0, 1, 2)
    assert by_indices[1].step_indices == (0, 1, 2, 3)


def test_strong_position_followed_by_a_route_tail_keeps_final_status_and_shortcut_trigger_isolated():
    """place_order(SUCCESS) sonrası view_receipt/close_app(FAIL, SHORTCUT-triggered) -- iki
    ayrı candidate üretilmeli, birbirinin final_status/has_shortcut_trigger'ını kirletmemeli."""
    steps = [
        StepSpec(action="browse_cart", effect=ObservationEffect.ROUTE),
        StepSpec(
            action="place_order",
            effect=ObservationEffect.CONFIRM,
            target="order_9",
            status=ObservationStatus.SUCCESS,
        ),
        StepSpec(action="view_receipt", effect=ObservationEffect.ROUTE, status=ObservationStatus.SUCCESS),
        StepSpec(
            action="close_app",
            effect=ObservationEffect.ROUTE,
            status=ObservationStatus.FAIL,
            trigger=ObservationTrigger.SHORTCUT,
        ),
    ]
    series = make_series_from_steps("sess1", _NOW, steps)
    candidates = build_episode_candidates([series], _CONFIG)

    assert len(candidates) == 2
    assert all(c.kind == EpisodeCandidateKind.EPISODE_SPAN for c in candidates)
    leading, trailing = sorted(candidates, key=lambda c: c.step_indices)

    assert [s[0] for s in leading.symbols] == ["browse_cart", "place_order"]
    assert leading.final_status == ObservationStatus.SUCCESS
    assert leading.has_shortcut_trigger is False

    assert [s[0] for s in trailing.symbols] == ["view_receipt", "close_app"]
    assert trailing.final_status == ObservationStatus.FAIL
    assert trailing.has_shortcut_trigger is True


def test_identical_chunks_with_a_strong_position_do_not_double_count_via_common_subsequence():
    """İki chunk birebir aynıysa (`[browse, place_order(strong)]`), FULL_CHUNK'ın kendi
    hipotezi ile COMMON_SUBSEQUENCE'ın yeniden bulduğu AYNI aralık çakışmamalı (seen_keys
    regresyonu)."""
    steps = [
        StepSpec(action="browse", effect=ObservationEffect.ROUTE),
        StepSpec(action="place_order", effect=ObservationEffect.CONFIRM, target="order_9"),
    ]
    series_a = make_series_from_steps("sess1", _NOW, steps, series_suffix="a")
    series_b = make_series_from_steps("sess2", _NOW, steps, series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert len(candidates) == 2
    assert {c.series_id for c in candidates} == {series_a.series_id, series_b.series_id}


def test_two_identical_sessions_shaped_strong_then_route_tail_never_produce_a_combined_candidate():
    """En sık rastlanan tekrar biçimi: iki session birebir aynı, `place_order(strong) ->
    go_home(route)` ile bitiyor. Bu şekil TEK bir candidate'e (Anchor Resolver'da AMBIGUOUS'a
    düşecek) DÖNÜŞMEMELİ -- ne FULL_CHUNK ne COMMON_SUBSEQUENCE yolundan. `COMMON_SUBSEQUENCE`
    riskinin ertelenmeyip bu turda kapatıldığının doğrudan kanıtı."""
    steps = [
        StepSpec(action="browse", effect=ObservationEffect.ROUTE),
        StepSpec(action="place_order", effect=ObservationEffect.CONFIRM, target="order_9"),
        StepSpec(action="go_home", effect=ObservationEffect.ROUTE),
    ]
    series_a = make_series_from_steps("sess1", _NOW, steps, series_suffix="a")
    series_b = make_series_from_steps("sess2", _NOW, steps, series_suffix="b")
    candidates = build_episode_candidates([series_a, series_b], _CONFIG)

    assert len(candidates) == 2
    for candidate in candidates:
        assert [s[0] for s in candidate.symbols] == ["browse", "place_order"]
        assert candidate.kind == EpisodeCandidateKind.EPISODE_SPAN


def test_max_symbols_truncates_a_strong_ending_hypothesis_from_the_front():
    """Strong pozisyonda biten bir hipotez max_symbols'ü aşarsa BAŞTAN kırpılır -- bitiş
    noktası (asıl kanıt) korunur. Sıfır-strong bir bloğun SONDAN kırpıldığı
    (`test_max_symbols_caps_candidate_length`) davranışın tam tersi bir yön."""
    long_prefix = [StepSpec(action=f"step_{i}", effect=ObservationEffect.ROUTE) for i in range(9)]
    steps = [*long_prefix, StepSpec(action="place_order", effect=ObservationEffect.CONFIRM, target="order_9")]
    series = make_series_from_steps("sess1", _NOW, steps)
    candidates = build_episode_candidates([series], EpisodeConfig(min_symbols=2, max_symbols=8))

    assert len(candidates) == 1
    assert candidates[0].kind == EpisodeCandidateKind.FULL_CHUNK
    assert len(candidates[0].steps) == 8
    assert [s[0] for s in candidates[0].symbols][-1] == "place_order"


def test_leading_strong_position_with_nothing_to_merge_produces_no_candidate():
    """place_order strong pozisyon chunk'ın DAHA İLK adımıysa (önünde birleşecek bir şey yok)
    ve hemen ardından yalnızca kısa bir route kuyruğu geliyorsa, her iki taraf da kendi başına
    min_symbols altında kalıp düşer -- kabul edilen sınır durumu (bkz. docs/engine-decisions.md
    #10): tek adımlık bir scope zaten Benefit'te hiçbir zaman CLEAR olamaz, öneri kapasitesinde
    gerçek kayıp yoktur."""
    steps = [
        StepSpec(action="place_order", effect=ObservationEffect.CONFIRM, target="order_9"),
        StepSpec(action="go_home", effect=ObservationEffect.ROUTE),
    ]
    series = make_series_from_steps("sess1", _NOW, steps)
    assert build_episode_candidates([series], _CONFIG) == []
