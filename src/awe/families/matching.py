"""Behavior Family eşleştirme motoru (bölüm 45-60, IMPLEMENTATION_PLAN.md 2.1).

Bu modül üç sorumluluğu birlikte taşır: yeni bir O-Series'in mevcut family'lerden hangisine
ait olduğuna karar vermek (`match_series`), kabul edilen bir occurrence'ı family'nin temsilci
variant kümesine işlemek (`accept_series`) ve family'nin core/optional ilişki tablosuyla
cohesion'ını buna göre güncel tutmak. Core tablo her kabulden sonra ailenin BİRİKMİŞ tüm
variant'ları üzerinden yeniden hesaplanır; bu, tek bir en-yakın-komşuya göre karar vermenin
yol açacağı "chaining" sürüklenmesini engeller (bölüm 58).
"""

from __future__ import annotations

from datetime import datetime

from awe.config.engine_config import FamilyConfig
from awe.domain.enums import FamilyMatchOutcome
from awe.domain.family import BehaviorFamily, CoreRelationship, FamilyMatchDecision, FamilyVariant
from awe.domain.tokens import Symbol
from awe.families.similarity import order_preserving_coverage, weighted_similarity


def _is_order_preserving_subsequence(candidate: tuple[Symbol, ...], seed: tuple[Symbol, ...]) -> bool:
    """`candidate`, `seed`'den bazı semboller çıkarılarak (sıra korunarak) elde edilebilir mi?

    Yalnızca sembol KÜMESİ değil, göreli SIRA da korunmalıdır — aksi halde ters sıralı bir
    dizi (ör. B,A) yanlışlıkla A,B'nin bir alt dizisi sayılır (bölüm 115'in ruhu: sıra
    bilgisini yok saymak farklı davranışları birbirine karıştırabilir).
    """

    remaining = iter(seed)
    return all(symbol in remaining for symbol in candidate)


def compute_relationships(
    variants: list[FamilyVariant], core_coverage_threshold: float
) -> list[CoreRelationship]:
    if not variants:
        return []
    pair_counts: dict[tuple[Symbol, Symbol], int] = {}
    for variant in variants:
        pairs_in_variant = set(zip(variant.symbols, variant.symbols[1:], strict=False))
        for pair in pairs_in_variant:
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    total = len(variants)
    return [
        CoreRelationship(
            predecessor=pair[0],
            successor=pair[1],
            coverage=count / total,
            is_core=(count / total) >= core_coverage_threshold,
        )
        for pair, count in pair_counts.items()
    ]


def compute_cohesion(variants: list[FamilyVariant], relationships: list[CoreRelationship]) -> float:
    core_pairs = {(r.predecessor, r.successor) for r in relationships if r.is_core}
    total_support = sum(v.support for v in variants)
    if not core_pairs or total_support == 0:
        return 1.0

    weighted_sum = 0.0
    for variant in variants:
        variant_pairs = set(zip(variant.symbols, variant.symbols[1:], strict=False))
        ratio = len(variant_pairs & core_pairs) / len(core_pairs)
        weighted_sum += ratio * variant.support
    return weighted_sum / total_support


def seed_family(
    family_id: str,
    project_id: str,
    subject_id: str,
    series_id: str,
    symbols: tuple[Symbol, ...],
    observed_at: datetime,
    config: FamilyConfig,
) -> BehaviorFamily:
    family = BehaviorFamily(
        family_id=family_id,
        project_id=project_id,
        subject_id=subject_id,
        created_at=observed_at,
        updated_at=observed_at,
    )
    accept_series(family, series_id, symbols, observed_at, config)
    return family


def match_series(
    symbols: tuple[Symbol, ...],
    families: list[BehaviorFamily],
    weights: dict[Symbol, float],
    config: FamilyConfig,
) -> FamilyMatchDecision:
    if len(symbols) < config.min_symbols_to_seed_family:
        return FamilyMatchDecision(
            outcome=FamilyMatchOutcome.NO_MATCH, family_id=None, best_similarity=0.0, core_coverage=0.0
        )

    scored: list[tuple[BehaviorFamily, float, float, float, bool]] = []
    for family in families:
        if not family.representative_variants:
            continue
        best_similarity = max(
            weighted_similarity(symbols, variant.symbols, weights)
            for variant in family.representative_variants
        )
        core_pairs = {(r.predecessor, r.successor) for r in family.relationships if r.is_core}
        coverage = order_preserving_coverage(symbols, core_pairs)
        # Tek örneklik bir core tablosu henüz hiçbir şeyle doğrulanmamıştır; buna sıkı kapsama
        # zorunluluğu uygulamak ilk occurrence'ın atipik olduğu durumlarda (ör. bir detour
        # içeren tek seferlik bir sapma) sonraki gerçek occurrence'ları haksız yere reddeder
        # (bölüm 51). Ancak bu gevşetme yalnızca aday, tohumun sembol kümesinin bir ALT
        # KÜMESİYSE uygulanır (yeni sembol getirmiyor, yalnızca bazılarını atlıyor) — aksi
        # halde bölüm 58'deki "chaining" saldırısı yeniden açılır: aday YENİ semboller
        # getiriyorsa (X,Y,D tohumuna karşı X,Y,Z gibi) bu gerçek bir sapmadır ve sıkı kapsama
        # korunmalıdır.
        is_young_family = len(family.representative_variants) < config.min_variants_for_strict_core
        is_pure_subsequence = is_young_family and _is_order_preserving_subsequence(
            symbols, family.representative_variants[0].symbols
        )
        effective_coverage = 1.0 if is_pure_subsequence else coverage
        scored.append((family, best_similarity, coverage, effective_coverage, is_pure_subsequence))

    if not scored:
        return FamilyMatchDecision(
            outcome=FamilyMatchOutcome.NO_MATCH, family_id=None, best_similarity=0.0, core_coverage=0.0
        )

    scored.sort(key=lambda item: item[1], reverse=True)
    top_family, top_similarity, top_coverage, top_effective_coverage, top_is_pure_subsequence = scored[0]

    close_candidates = [
        item
        for item in scored
        if item[1] >= top_similarity - config.ambiguity_margin
        and item[1] >= config.variant_similarity_threshold
    ]
    if len(close_candidates) >= 2:
        return FamilyMatchDecision(
            outcome=FamilyMatchOutcome.AMBIGUOUS,
            family_id=None,
            best_similarity=top_similarity,
            core_coverage=top_coverage,
            ambiguous_family_ids=tuple(family.family_id for family, _, _, _, _ in close_candidates),
        )

    # Aynı alt-küme gerekçesiyle: adayın kendisi tohumun saf bir sıra-korur alt dizisiyse
    # (yeni sembol getirmiyor), benzerlik eşiğinde tam kararlılık bulunması beklenmez —
    # ayrıştırıcı ağırlıklandırma bu tek örnekte hangi sembollerin "gerçek çekirdek" olduğunu
    # henüz kanıtlayamamış olabilir (bölüm 51). Yalnızca son eşik karşılaştırması için
    # kullanılır; ambiguity karşılaştırması ham benzerlikle yapılmaya devam eder.
    effective_similarity = (
        max(top_similarity, config.variant_similarity_threshold) if top_is_pure_subsequence else top_similarity
    )

    if (
        effective_similarity >= config.match_similarity_threshold
        and top_effective_coverage >= config.core_match_threshold
    ):
        return FamilyMatchDecision(
            outcome=FamilyMatchOutcome.MATCH,
            family_id=top_family.family_id,
            best_similarity=top_similarity,
            core_coverage=top_coverage,
        )
    if (
        effective_similarity >= config.variant_similarity_threshold
        and top_effective_coverage >= config.core_match_threshold
    ):
        return FamilyMatchDecision(
            outcome=FamilyMatchOutcome.VARIANT_MATCH,
            family_id=top_family.family_id,
            best_similarity=top_similarity,
            core_coverage=top_coverage,
        )
    return FamilyMatchDecision(
        outcome=FamilyMatchOutcome.NO_MATCH,
        family_id=None,
        best_similarity=top_similarity,
        core_coverage=top_coverage,
    )


def _accept_symbols(
    family: BehaviorFamily, symbols: tuple[Symbol, ...], observed_at: datetime, config: FamilyConfig
) -> None:
    for index, variant in enumerate(family.representative_variants):
        if variant.symbols == symbols:
            family.representative_variants[index] = FamilyVariant(
                symbols=symbols, support=variant.support + 1, last_observed_at=observed_at
            )
            break
    else:
        family.representative_variants.append(
            FamilyVariant(symbols=symbols, support=1, last_observed_at=observed_at)
        )
        if len(family.representative_variants) > config.max_representative_variants:
            family.representative_variants.sort(key=lambda v: v.support, reverse=True)
            del family.representative_variants[config.max_representative_variants :]

    family.relationships = compute_relationships(
        family.representative_variants, config.core_coverage_threshold
    )
    family.cohesion = compute_cohesion(family.representative_variants, family.relationships)
    family.updated_at = observed_at


def accept_series(
    family: BehaviorFamily,
    series_id: str,
    symbols: tuple[Symbol, ...],
    observed_at: datetime,
    config: FamilyConfig,
) -> None:
    _accept_symbols(family, symbols, observed_at, config)
    family.member_series_ids.append(series_id)
