"""Motorun bütün eşik değerleri tek bir yerde toplanır (bölüm 98).

Varsayılan değerler `IMPLEMENTATION_PLAN.md` içerisinde gerekçelendirilmiş ve
`scripts/evaluate_engine.py` ile sentetik veri üzerinde kalibre edilmiştir (bkz.
`docs/evaluation.md`). Hiçbiri koddan rastgele seçilmiş "magic number" değildir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from awe.domain.enums import EffectPolicy, ObservationEffect


@dataclass(frozen=True, slots=True)
class FamilyConfig:
    max_representative_variants: int = 8
    """Bir family'nin tuttuğu temsilci variant sayısının üst sınırı (bölüm 47)."""

    core_coverage_threshold: float = 0.6
    """Bir ardışık sembol çiftinin 'core' sayılması için temsilci variant'lar arasındaki
    minimum kapsama oranı."""

    core_match_threshold: float = 0.7
    """Yeni bir occurrence'ın family core'unu MATCH/VARIANT_MATCH sayması için gereken
    minimum core-bigram kapsama oranı."""

    match_similarity_threshold: float = 0.82
    """Ayrıştırıcı ağırlıklı LCS benzerliğinin MATCH kararı için alt sınırı."""

    variant_similarity_threshold: float = 0.55
    """VARIANT_MATCH kararı için alt sınır (bu değerin altı NO_MATCH/AMBIGUOUS adayıdır)."""

    ambiguity_margin: float = 0.08
    """İki farklı family'nin skoru bu marj içinde birbirine yakınsa sonuç AMBIGUOUS olur."""

    detour_max_length: int = 4
    """Bounded detour normalizasyonunun izin verdiği azami adım sayısı (bölüm 41)."""

    min_series_for_weighting: int = 5
    """Subject'in ayrıştırıcı ağırlıklandırma için sahip olması gereken minimum O-Series sayısı;
    altında uniform ağırlık kullanılır (IMPLEMENTATION_PLAN.md 2.6)."""

    min_symbol_weight: float = 0.15
    """Ayrıştırıcı ağırlıklandırmanın bir sembolü düşürebileceği alt sınır. Bir sembol
    subject'in tüm O-Series'lerinde görülüyorsa ham IDF onu tamamen sıfıra çeker; bu ise az
    sayıda örnekle o sembolün gerçek family çekirdeği mi yoksa rastgele mi olduğunu ayırt
    edemeden benzerlik skorunu yapay biçimde sıfırlayabilir. Bir alt sınır, tek bir aykırı ilk
    örneğin sonraki normal occurrence'ları reddettirmesini önler (bölüm 51,
    IMPLEMENTATION_PLAN.md 2.6)."""

    min_symbols_to_seed_family: int = 2
    """Tek sembollük çok kısa dizi doğrudan yeni family tohumlamaz; PENDING_EVIDENCE kalır."""

    min_variants_for_strict_core: int = 2
    """Bir family bu sayıdan AZ temsilci variant'a sahipse (tipik olarak yalnızca ilk tohum),
    core-bigram kapsama kısıtı zorunlu tutulmaz — tek bir örnek henüz neyin gerçekten çekirdek
    neyin o örneğe özgü bir ayrıntı olduğunu kanıtlamaz (bölüm 51: "İlk occurrence seed'e aşırı
    bağımlı olma")."""


@dataclass(frozen=True, slots=True)
class HabitConfig:
    min_occurrences: int = 3
    min_distinct_sessions: int = 2
    min_distinct_days: int = 3
    """Tek başına gün/session sayımına dayanan hard gate — one-day/two-day burst ve
    single-session repeater'ı reddeder (IMPLEMENTATION_PLAN.md 2.2)."""

    support_saturation_k: float = 5.0
    """supportScore = occurrences / (occurrences + k)."""

    min_days_for_regularity: int = 4
    """Regularity'nin anlamlı sayılması için gereken minimum farklı gün sayısı (>=3 boşluk)."""

    liveness_watch_multiplier: float = 2.0
    liveness_stale_multiplier: float = 4.0
    """staleness_ratio = gün_farkı / beklenen_boşluk; WATCH ve STALE eşik çarpanları
    (IMPLEMENTATION_PLAN.md 2.4)."""


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    min_binding_sample_size: int = 3
    stable_dominance_threshold: float = 0.75
    min_coverage_for_known_state: float = 0.5
    recent_window_size: int = 10
    """Concept drift kontrolü için son-K occurrence penceresi (bölüm 77)."""
    recent_drift_drop_threshold: float = 0.3
    """recentDominance, tarihsel dominance'tan bu kadar düşükse drift kanıtı üretilir."""


DEFAULT_EFFECT_POLICY: dict[ObservationEffect, EffectPolicy] = {
    ObservationEffect.ROUTE: EffectPolicy.SAFE,
    ObservationEffect.OPEN_MODAL: EffectPolicy.SAFE,
    ObservationEffect.SELECT: EffectPolicy.SAFE,
    ObservationEffect.INPUT: EffectPolicy.SAFE,
    ObservationEffect.PREPARE: EffectPolicy.SAFE,
    ObservationEffect.UPDATE: EffectPolicy.REVIEW,
    ObservationEffect.SUBMIT: EffectPolicy.REVIEW,
    ObservationEffect.CONFIRM: EffectPolicy.BLOCKED,
    ObservationEffect.UNKNOWN: EffectPolicy.REVIEW,
}
"""Canonical effect -> güvenlik politikası (bölüm 80). Business action string'lerine değil,
yalnızca AWE Core'un kendi canonical effect sözlüğüne dayanır; proje bazında override edilebilir."""


@dataclass(frozen=True, slots=True)
class RiskConfig:
    effect_policy: dict[ObservationEffect, EffectPolicy] = field(
        default_factory=lambda: dict(DEFAULT_EFFECT_POLICY)
    )
    min_sample_size_for_confidence: int = 5
    max_failure_rate_for_allow: float = 0.4
    max_cancel_rate_for_allow: float = 0.4
    min_data_quality_for_allow: float = 0.5
    min_family_cohesion_for_allow: float = 0.5


@dataclass(frozen=True, slots=True)
class BenefitConfig:
    min_median_saved_actions: float = 2.0
    min_benefit_coverage: float = 0.5


@dataclass(frozen=True, slots=True)
class LifecycleConfig:
    dismiss_cooldown_days: int = 14
    stale_after_missed_cycles: float = 3.0
    """Bir suggestion'ın son kullanımdan bu kadar 'beklenen boşluk' katı sonra STALE'e düşmesi."""


@dataclass(frozen=True, slots=True)
class EngineConfig:
    family: FamilyConfig = field(default_factory=FamilyConfig)
    habit: HabitConfig = field(default_factory=HabitConfig)
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    benefit: BenefitConfig = field(default_factory=BenefitConfig)
    lifecycle: LifecycleConfig = field(default_factory=LifecycleConfig)
    timezone: str = "UTC"
    """Habit gün-sınırı hesapları için proje/uygulama zaman dilimi (bölüm 15)."""


def default_engine_config() -> EngineConfig:
    return EngineConfig()
