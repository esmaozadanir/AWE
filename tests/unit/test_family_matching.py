from datetime import UTC, datetime

from awe.config import default_engine_config
from awe.domain.enums import FamilyMatchOutcome, ObservationEffect
from awe.families import accept_series, compute_discriminative_weights, match_series, seed_family

_CONFIG = default_engine_config().family
_NOW = datetime(2026, 8, 1, tzinfo=UTC)


def _symbol(action_key: str, effect: ObservationEffect = ObservationEffect.ROUTE) -> tuple[str, str]:
    return (action_key, effect.value)


def test_optional_middle_step_still_matches_same_family():
    seq = (_symbol("A"), _symbol("B"), _symbol("C"))
    family = seed_family("fam1", "proj", "subj", "seed", seq, _NOW, _CONFIG)

    decision = match_series((_symbol("A"), _symbol("X"), _symbol("B"), _symbol("C")), [family], {}, _CONFIG)

    assert decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH)
    assert decision.family_id == "fam1"


def test_same_prefix_with_different_continuation_is_not_matched():
    seq = (_symbol("A"), _symbol("B"), _symbol("C"), _symbol("D"))
    family = seed_family("fam1", "proj", "subj", "seed", seq, _NOW, _CONFIG)

    decision = match_series((_symbol("A"), _symbol("B"), _symbol("E"), _symbol("F")), [family], {}, _CONFIG)

    assert decision.outcome == FamilyMatchOutcome.NO_MATCH


def test_same_terminal_action_does_not_force_family_merge():
    seq = (_symbol("A"), _symbol("B"), _symbol("C"), _symbol("REVIEW"))
    family = seed_family("fam1", "proj", "subj", "seed", seq, _NOW, _CONFIG)

    decision = match_series(
        (_symbol("X"), _symbol("Y"), _symbol("Z"), _symbol("REVIEW")), [family], {}, _CONFIG
    )

    assert decision.outcome == FamilyMatchOutcome.NO_MATCH


def test_short_fragment_shared_by_two_families_is_ambiguous_not_forced_into_either():
    seq_a = (_symbol("A"), _symbol("B"), _symbol("C"), _symbol("D"))
    seq_b = (_symbol("X"), _symbol("B"), _symbol("C"), _symbol("Y"))
    family_a = seed_family("fam1", "proj", "subj", "seed-a", seq_a, _NOW, _CONFIG)
    family_b = seed_family("fam2", "proj", "subj", "seed-b", seq_b, _NOW, _CONFIG)

    decision = match_series((_symbol("B"), _symbol("C")), [family_a, family_b], {}, _CONFIG)

    assert decision.outcome == FamilyMatchOutcome.AMBIGUOUS
    assert set(decision.ambiguous_family_ids) == {"fam1", "fam2"}


def test_widget_rename_across_versions_does_not_split_family():
    # Sembol yalnızca (action_key, effect); widget hiç dahil değil, bu yüzden widget adı
    # değişse bile aynı davranış aynı family'ye eşleşmeye devam eder (bölüm 24, 50).
    sequence = (_symbol("open_settings"), _symbol("open_security"))
    family = seed_family("fam1", "proj", "subj", "seed", sequence, _NOW, _CONFIG)

    decision = match_series(sequence, [family], {}, _CONFIG)

    assert decision.outcome == FamilyMatchOutcome.MATCH


def test_chaining_sequence_does_not_collapse_into_a_single_family():
    sequences = [
        (_symbol("A"), _symbol("B"), _symbol("C"), _symbol("D")),
        (_symbol("A"), _symbol("B"), _symbol("X"), _symbol("C"), _symbol("D")),
        (_symbol("X"), _symbol("C"), _symbol("D")),
        (_symbol("X"), _symbol("Y"), _symbol("D")),
        (_symbol("X"), _symbol("Y"), _symbol("Z")),
    ]
    weights = compute_discriminative_weights(sequences, _CONFIG.min_series_for_weighting)

    families = []
    next_id = 0
    for index, sequence in enumerate(sequences):
        decision = match_series(sequence, families, weights, _CONFIG)
        if decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH):
            family = next(f for f in families if f.family_id == decision.family_id)
            accept_series(family, f"s{index}", sequence, _NOW, _CONFIG)
        else:
            next_id += 1
            families.append(seed_family(f"fam{next_id}", "proj", "subj", f"s{index}", sequence, _NOW, _CONFIG))

    assert len(families) == 4, "tek bir sürüklenen dev family oluşmamalı (bölüm 58)"


def test_common_startup_symbol_does_not_merge_unrelated_families():
    sequences = [
        (_symbol("start"), _symbol("A"), _symbol("B"), _symbol("C")),
        (_symbol("start"), _symbol("X"), _symbol("Y"), _symbol("Z")),
        (_symbol("start"), _symbol("M"), _symbol("N"), _symbol("K")),
    ]
    weights = compute_discriminative_weights(sequences, _CONFIG.min_series_for_weighting)

    families = []
    next_id = 0
    for index, sequence in enumerate(sequences):
        decision = match_series(sequence, families, weights, _CONFIG)
        if decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH):
            family = next(f for f in families if f.family_id == decision.family_id)
            accept_series(family, f"s{index}", sequence, _NOW, _CONFIG)
        else:
            next_id += 1
            families.append(seed_family(f"fam{next_id}", "proj", "subj", f"s{index}", sequence, _NOW, _CONFIG))

    assert len(families) == 3, "ortak başlangıç sembolü farklı davranışları birleştirmemeli (bölüm 115)"
