"""Bölüm 123: property-based invariant testleri — Behavior Family."""

from __future__ import annotations

import string
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from awe.config import default_engine_config
from awe.domain.enums import FamilyMatchOutcome, ObservationEffect
from awe.families import accept_series, compute_discriminative_weights, match_series, seed_family
from tests.support.builders import StepSpec, make_series_from_steps

_CONFIG = default_engine_config().family
_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_ACTION_ALPHABET = st.text(alphabet=string.ascii_uppercase, min_size=1, max_size=3)


def _symbol(action_key: str) -> tuple[str, str]:
    return (action_key, ObservationEffect.ROUTE.value)


@given(
    target_refs=st.lists(
        st.text(alphabet=string.digits, min_size=1, max_size=6), min_size=1, max_size=6
    )
)
@settings(max_examples=40)
def test_target_ref_variation_never_splits_a_structurally_identical_family(target_refs):
    steps_per_occurrence = [
        [
            StepSpec(action_key="open_form", effect=ObservationEffect.ROUTE),
            StepSpec(
                action_key="select_item",
                effect=ObservationEffect.SELECT,
                target=ref,
            ),
        ]
        for ref in target_refs
    ]

    family = None
    for index, steps in enumerate(steps_per_occurrence):
        series = make_series_from_steps(f"sess{index}", _NOW, steps, series_suffix=str(index))
        if family is None:
            family = seed_family("fam1", "proj", "subj", series.series_id, series.symbols, _NOW, _CONFIG)
        else:
            decision = match_series(series.symbols, [family], {}, _CONFIG)
            assert decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH)
            accept_series(family, series.series_id, series.symbols, _NOW, _CONFIG)

    assert family is not None
    assert len(family.representative_variants) == 1
    assert family.representative_variants[0].support == len(target_refs)


@given(widgets=st.lists(st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=8), min_size=1, max_size=6))
@settings(max_examples=40)
def test_widget_rename_never_splits_a_family_when_action_and_effect_are_stable(widgets):
    # Eşleştirme, `min_symbols_to_seed_family` altındaki tek-sembollük dizileri kasıtlı olarak
    # AMBIGUOUS/NO_MATCH bırakır (bölüm 59 ruhu); bu yüzden en az iki adımlık gerçekçi bir
    # occurrence kullanılır, yalnızca ikinci adımın widget'ı değişir.
    steps_per_occurrence = [
        [
            StepSpec(action_key="open_settings", effect=ObservationEffect.ROUTE),
            StepSpec(action_key="open_security", effect=ObservationEffect.ROUTE, widget=widget),
        ]
        for widget in widgets
    ]

    family = None
    for index, steps in enumerate(steps_per_occurrence):
        series = make_series_from_steps(f"sess{index}", _NOW, steps, series_suffix=str(index))
        if family is None:
            family = seed_family("fam1", "proj", "subj", series.series_id, series.symbols, _NOW, _CONFIG)
        else:
            decision = match_series(series.symbols, [family], {}, _CONFIG)
            assert decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH)
            accept_series(family, series.series_id, series.symbols, _NOW, _CONFIG)

    assert family is not None
    assert len(family.representative_variants) == 1


@given(
    suffix_groups=st.lists(
        st.lists(_ACTION_ALPHABET, min_size=2, max_size=4, unique=True),
        min_size=2,
        max_size=5,
        unique_by=lambda group: tuple(group),
    )
)
@settings(max_examples=30)
def test_common_startup_symbol_never_merges_distinct_behaviors(suffix_groups):
    # Bölüm 115'in kastettiği senaryo, ortak bir başlangıçtan sonra GERÇEKTEN BAĞIMSIZ
    # devam eden suffix'lerdir (START→A→B→C / START→X→Y→Z gibi — hiçbir ortak devam
    # sembolü yok). Ham Hypothesis çıktısında iki farklı grup şans eseri aynı sembolü
    # (ör. her ikisi de "AA" içerebilir) ya da birbirinin alt dizisini paylaşabilir; bu
    # durumlar "opsiyonel son adım" (bölüm 114) gibi FARKLI, birleşmesi meşru senaryolara
    # karışır. Her grubun sembollerini kendi grup indeksiyle etiketleyerek gruplar arasında
    # kazara örtüşmeyi yapısal olarak imkansız kılıyoruz; iç yapının çeşitliliği
    # (uzunluk, sıralama) Hypothesis'ten olduğu gibi korunur.
    tagged_groups = [
        [f"g{group_index}_{symbol}" for symbol in group] for group_index, group in enumerate(suffix_groups)
    ]

    sequences = [tuple([_symbol("start"), *[_symbol(s) for s in suffixes]]) for suffixes in tagged_groups]
    weights = compute_discriminative_weights(sequences, _CONFIG.min_series_for_weighting)

    families = []
    next_id = 0
    for index, sequence in enumerate(sequences):
        decision = match_series(sequence, families, weights, _CONFIG)
        if decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH):
            family = next(f for f in families if f.family_id == decision.family_id)
            accept_series(family, f"s{index}", sequence, _NOW, _CONFIG)
        elif decision.outcome == FamilyMatchOutcome.NO_MATCH:
            next_id += 1
            families.append(seed_family(f"fam{next_id}", "proj", "subj", f"s{index}", sequence, _NOW, _CONFIG))
        # AMBIGUOUS: iki farklı davranış arasında gerçekten ayırt edilemez kalmış olabilir
        # (kısa/örtüşen suffix'ler); bu durumda ne yanlış merge ne de sahte split sayılır.

    assert len(families) <= len(sequences)
    for family in families:
        assert family.total_support >= 1
    # Ortak "start" öneki, yapısal olarak farklı davranışların tek bir dev family'de
    # toplanmasına asla yol açmamalı (bölüm 115, property invariant #8).
    if len(sequences) >= 2:
        assert not (len(families) == 1 and families[0].total_support == len(sequences))
