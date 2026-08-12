"""O-Series sınır tespitinin sağlamlığı: az outcome/çok context, uzun session, tek session
içinde iki bağımsız iş.

Bu testler, `extract_series`'in bölüm 35-44'teki sınır kurallarının (breaksEpisode ve doğal
tamamlanma noktası) beklenmedik girdi şekillerinde de deterministik ve tutarlı davrandığını
doğrular; `tests/unit/test_series_normalization.py`'deki testlerden farkı, burada odak tek bir
normalizasyon kuralı değil session'ın GENEL yapısal sağlamlığıdır (çok sayıda context event,
çok uzun session, tamamlanma sinyali üretmeyen konu değişikliği).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.config import default_engine_config
from awe.domain.enums import (
    FamilyMatchOutcome,
    ObservationEffect,
    ObservationRole,
    ObservationStatus,
    OrderingConfidence,
)
from awe.families import accept_series, match_series, seed_family
from awe.series import extract_series
from tests.support.builders import make_observation

_CONFIG = default_engine_config().family
_BASE_TIME = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _obs(
    action_key: str,
    *,
    index: int,
    effect: ObservationEffect = ObservationEffect.ROUTE,
    role: ObservationRole = ObservationRole.ACTION,
    status: ObservationStatus = ObservationStatus.SUCCESS,
):
    return make_observation(
        action_key,
        event_id=f"evt{index}",
        session_id="sess",
        timestamp=_BASE_TIME + timedelta(seconds=index),
        effect=effect,
        role=role,
        status=status,
    )


def test_many_context_events_and_a_single_late_outcome_stay_one_series():
    # Gerçekçi bir gezinme deseni: çok sayıda screen-view (role=context), araya bir ürüne
    # ikinci kez bakma (context tekrar), ve en sonda TEK bir outcome. Tamamlanma sinyali
    # yalnızca son adımda üretildiği için tüm session tek bir O-Series olmalı ve context
    # adımları (bölüm 38) normalize edilmiş diziden silinmemeli.
    observations = [
        _obs("view_home", index=0, role=ObservationRole.CONTEXT),
        _obs("view_category", index=1, role=ObservationRole.CONTEXT),
        _obs("view_product_a", index=2, role=ObservationRole.CONTEXT),
        _obs("view_product_b", index=3, role=ObservationRole.CONTEXT),
        _obs("view_product_b", index=4, role=ObservationRole.CONTEXT),  # kullanıcı geri kaydırdı
        _obs("view_product_c", index=5, role=ObservationRole.CONTEXT),
        _obs("view_cart", index=6, role=ObservationRole.CONTEXT),
        _obs("add_to_cart", index=7, effect=ObservationEffect.SELECT),
        _obs(
            "checkout_result",
            index=8,
            role=ObservationRole.OUTCOME,
            effect=ObservationEffect.SUBMIT,
            status=ObservationStatus.SUCCESS,
        ),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, _CONFIG)

    assert len(series) == 1
    assert len(series[0].raw_observations) == 9
    # context adımları normalize edilmiş projeksiyonda korunur (silinmez, yalnızca role=noise
    # elenir) -- bu yüzden normalized_steps ham dizininin tamamını (9 adım) içermeli.
    assert len(series[0].normalized_steps) == 9
    assert series[0].final_status == ObservationStatus.SUCCESS


def test_long_session_with_many_completions_splits_cleanly_without_error():
    # Kullanıcı tek bir uzun session'da 25 farklı ürünü sırayla inceleyip her birini ayrı
    # ayrı satın alıyor. Amaç, çok sayıda ardışık tamamlanma noktasının (25 kez) doğru ve
    # hatasız bölünebildiğini, hiçbir occurrence'ın kaybolmadığını doğrulamaktır.
    observations = []
    index = 0
    for product in range(25):
        observations.append(_obs(f"view_product_{product}", index=index, role=ObservationRole.CONTEXT))
        index += 1
        observations.append(_obs("add_to_cart", index=index, effect=ObservationEffect.SELECT))
        index += 1
        observations.append(
            _obs(
                "checkout_result",
                index=index,
                role=ObservationRole.OUTCOME,
                effect=ObservationEffect.SUBMIT,
                status=ObservationStatus.SUCCESS,
            )
        )
        index += 1

    series = extract_series(observations, OrderingConfidence.HIGH, _CONFIG)

    assert len(series) == 25
    assert sum(len(s.raw_observations) for s in series) == 75
    assert all(not s.is_empty for s in series)
    assert all(s.final_status == ObservationStatus.SUCCESS for s in series)
    # her occurrence'ın kendi 3 adımı (view, add_to_cart, checkout) doğru gruplanmış olmalı
    assert all(len(s.raw_observations) == 3 for s in series)


def test_two_unrelated_behaviors_without_completion_signal_merge_into_one_series():
    # Belgelenmiş bilinçli MVP sınırlaması (docs/architecture.md, "Bilinen sınırlamalar"):
    # kullanıcı aynı session içinde, hiçbir tamamlanma sinyali üretmeden konu değiştirirse
    # (ör. ayarları inceleyip sonra ürün kataloğuna geçerse), bu iki bağımsız davranış tek bir
    # O-Series'te birleşik kalır. Bu test bunun ÇÖKMEDEN ve deterministik biçimde
    # gerçekleştiğini doğrular.
    observations = [
        _obs("open_settings", index=0),
        _obs("open_notifications", index=1),
        _obs("toggle_email_notifications", index=2, effect=ObservationEffect.SELECT),
        # -- kullanıcı konuyu değiştiriyor, breaksEpisode yok, tamamlanma sinyali yok --
        _obs("open_catalog", index=3),
        _obs("view_product_x", index=4, role=ObservationRole.CONTEXT),
        _obs("view_product_y", index=5, role=ObservationRole.CONTEXT),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, _CONFIG)

    assert len(series) == 1
    assert len(series[0].normalized_steps) == 6
    assert series[0].symbols[0] == ("open_settings", "route")
    assert series[0].symbols[-1] == ("view_product_y", "route")


def test_merged_two_task_series_does_not_corrupt_matching_against_a_clean_family():
    # Yukarıdaki sınırlamanın alt akışa etkisini ölçer: "temiz" (yalnızca tek davranış içeren)
    # occurrence'lardan kurulmuş bir family'ye karşı, iki işin birleştiği "kirli" bir
    # occurrence sunulduğunda motor çökmemeli ve geçerli bir FamilyMatchDecision döndürmelidir
    # (MATCH/VARIANT_MATCH/AMBIGUOUS/NO_MATCH -- hangisi olursa olsun, sistemin güvenli
    # davranışı bunlardan biri döndürmesidir).
    clean_symbols = (
        ("open_settings", "route"),
        ("open_notifications", "route"),
        ("toggle_email_notifications", "select"),
    )
    family = seed_family("fam1", "proj", "subj", "seed", clean_symbols, _BASE_TIME, _CONFIG)
    for i in range(4):
        decision = match_series(clean_symbols, [family], {}, _CONFIG)
        assert decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH)
        accept_series(family, f"clean{i}", clean_symbols, _BASE_TIME, _CONFIG)

    merged_symbols = (
        ("open_settings", "route"),
        ("open_notifications", "route"),
        ("toggle_email_notifications", "select"),
        ("open_catalog", "route"),
        ("view_product_x", "route"),
        ("view_product_y", "route"),
    )
    decision = match_series(merged_symbols, [family], {}, _CONFIG)

    assert decision.outcome in (
        FamilyMatchOutcome.MATCH,
        FamilyMatchOutcome.VARIANT_MATCH,
        FamilyMatchOutcome.AMBIGUOUS,
        FamilyMatchOutcome.NO_MATCH,
    )
    assert 0.0 <= decision.best_similarity <= 1.0
    assert 0.0 <= decision.core_coverage <= 1.0
