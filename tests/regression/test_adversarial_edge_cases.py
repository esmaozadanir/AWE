"""Adversarial review sırasında hedeflenen ek counterexample'lar (bölüm 114, 139).

Bu testler ilk implementasyon tamamlandıktan sonra, önceki senaryo/property testlerinde
doğrudan kapsanmayan uç durumları hedefler.
"""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config import default_engine_config
from awe.domain.enums import FamilyMatchOutcome, ObservationEffect
from awe.families import accept_series, compute_discriminative_weights, match_series, seed_family
from awe.ordering import order_session
from tests.support.builders import make_observation

_CONFIG = default_engine_config().family
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _symbol(action: str, effect: ObservationEffect = ObservationEffect.ROUTE) -> tuple[str, str]:
    return (action, effect.value)


def test_first_seed_outlier_does_not_prevent_later_normal_occurrences_from_joining():
    # Family, alışılmadık bir detour içeren bir occurrence ile tohumlanıyor (ilk örneklem
    # her zaman en temsili örnek olmak zorunda değildir, bölüm 51).
    outlier = (_symbol("A"), _symbol("B"), _symbol("X"), _symbol("C"), _symbol("D"))
    normal = (_symbol("A"), _symbol("B"), _symbol("C"), _symbol("D"))

    sequences = [outlier] + [normal] * 6
    weights = compute_discriminative_weights(sequences, _CONFIG.min_series_for_weighting)

    family = seed_family("fam1", "proj", "subj", "seed", outlier, _NOW, _CONFIG)
    matched = 0
    for index, sequence in enumerate(sequences[1:], start=1):
        decision = match_series(sequence, [family], weights, _CONFIG)
        if decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH):
            accept_series(family, f"s{index}", sequence, _NOW, _CONFIG)
            matched += 1

    assert matched == 6, "aykiri ilk ornek, sonraki normal occurrence'larin aile olusturmasini engellememeli"
    # A-B ve C-D her iki distinct variant'ta da (outlier + normal) gorulur, dolayisiyla core
    # olur. B-X/X-C yalnizca outlier'da, B-C yalnizca normal variant'ta gorulur (core, occurrence
    # sayisina degil DISTINCT variant sayisina gore hesaplanir, bkz. bolum 47 ve
    # `compute_relationships`) -- bu yuzden ikisi de tek basina %60 esigini gecemez ve
    # "optional" kalir. Bu, tek bir asiri aktif varyantin cekirdegi ele gecirmesini onler.
    core_pairs = {(r.predecessor, r.successor) for r in family.relationships if r.is_core}
    assert (_symbol("A"), _symbol("B")) in core_pairs
    assert (_symbol("C"), _symbol("D")) in core_pairs
    assert len(family.representative_variants) == 2
    normal_variant = next(v for v in family.representative_variants if v.symbols == normal)
    assert normal_variant.support == 6


def test_identical_timestamps_without_sequence_hint_are_still_deterministic():
    same_time = _NOW
    observations = [
        make_observation("Z", event_id="evt-z", session_id="s", timestamp=same_time),
        make_observation("A", event_id="evt-a", session_id="s", timestamp=same_time),
        make_observation("M", event_id="evt-m", session_id="s", timestamp=same_time),
    ]

    ordered_first, confidence_first = order_session(observations)
    ordered_second, confidence_second = order_session(list(reversed(observations)))

    assert [o.event_id for o in ordered_first] == [o.event_id for o in ordered_second]
    assert confidence_first.value == "low"
    assert confidence_second.value == "low"


def test_excessive_back_presses_never_leak_as_literal_symbols():
    from awe.domain.enums import ObservationStatus
    from awe.domain.tokens import BehaviorStep, BehaviorToken
    from awe.series.normalization import normalize_steps

    def step(action: str, effect: ObservationEffect, index: int) -> BehaviorStep:
        return BehaviorStep(
            token=BehaviorToken(action=action, effect=effect),
            screen=None,
            widget=None,
            status=ObservationStatus.SUCCESS,
            observation_index=index,
        )

    # A B, ardından yığın derinliğinden çok daha fazla "back" -- yığın boşaldıktan sonraki
    # fazladan back'ler bounded biçimde yutulmalı ve normalize edilmiş çıktıda asla "back"
    # adında uydurma bir sembol olarak görünmemeli (regresyon: önceden boş yığında back
    # literal bir adım olarak ekleniyordu).
    steps = [
        step("A", ObservationEffect.ROUTE, 0),
        step("B", ObservationEffect.ROUTE, 1),
    ] + [step(f"back{i}", ObservationEffect.NAVIGATE_BACK, 2 + i) for i in range(10)]

    result = normalize_steps(steps, detour_max_length=3)

    assert all(sym[1] != ObservationEffect.NAVIGATE_BACK.value for sym in (s.symbol for s in result.steps))
    assert result.detour_step_count == 10
