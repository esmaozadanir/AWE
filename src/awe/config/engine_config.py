"""Motorun bütün eşik değerleri tek bir yerde toplanır.

Belge (AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md) kasıtlı olarak çok az sayıda kesin eşik verir;
çoğu katman için yalnızca kategorik kurallar tanımlar ("Magic number kullanma" ilkesi büyük
ölçüde bu belgede de geçerlidir). Burada belgenin verdiği tek kesin sayılar (habit gate,
screen evidence min-session) sabitlenmiş; belgenin açıkça implementer kararına bıraktığı
değerler (episode max length, risk/reliability eşikleri) makul varsayılanlarla doldurulmuş
ve ayrı ayrı gerekçelendirilmiştir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from awe.domain.enums import EffectPolicy, ObservationEffect


@dataclass(frozen=True, slots=True)
class EpisodeConfig:
    min_symbols: int = 2
    """Tek sembollük bir chunk/ortak koşu bir 'davranış akışı' göstermez; aday sayılmaz."""

    max_symbols: int = 8
    """Belgenin kesinleştirmediği, açıkça implementer kararına bıraktığı azami aday uzunluğu
    (bölüm 6.4: "Eski MVP'deki max=8 korunacaksa bu ayrıca sabitlenip test edilmelidir").
    Sınırsız büyüme yerine bilinen bir öncül (8) korunmuştur."""


@dataclass(frozen=True, slots=True)
class HabitConfig:
    min_distinct_sessions: int = 3
    min_distinct_days: int = 2
    """MVP kapısı (bölüm 6.7): "distinct session >= 3 AND distinct calendar day >= 2".
    Yalnızca bu iki boyut hard gate'tir; ayrı bir minimum-occurrence eşiği yoktur — her
    distinct session zaten en az bir occurrence anlamına gelir."""


DEFAULT_EFFECT_POLICY: dict[ObservationEffect, EffectPolicy] = {
    ObservationEffect.ROUTE: EffectPolicy.SAFE,
    ObservationEffect.OPEN: EffectPolicy.SAFE,
    ObservationEffect.VIEW: EffectPolicy.SAFE,
    ObservationEffect.SELECT: EffectPolicy.SAFE,
    ObservationEffect.INPUT: EffectPolicy.SAFE,
    ObservationEffect.FILTER: EffectPolicy.SAFE,
    ObservationEffect.SORT: EffectPolicy.SAFE,
    ObservationEffect.FOCUS: EffectPolicy.SAFE,
    ObservationEffect.DOWNLOAD: EffectPolicy.SENSITIVE,
    ObservationEffect.TOGGLE: EffectPolicy.SENSITIVE,
    ObservationEffect.UPDATE: EffectPolicy.SENSITIVE,
    ObservationEffect.CREATE: EffectPolicy.SENSITIVE,
    # `request` bilinçli olarak SENSITIVE: read-only fetch mi state-changing talep mi kesin
    # ayrılamaz (bölüm 9.5) — hem action-surface Destination'a düşer hem BLOCK olmaz, yalnızca
    # review-worthy sayılır.
    ObservationEffect.REQUEST: EffectPolicy.SENSITIVE,
    ObservationEffect.SUBMIT: EffectPolicy.SENSITIVE,
    ObservationEffect.CONFIRM: EffectPolicy.SENSITIVE,
    # Bölüm 6.13: "delete bağlamı BLOCK" — tek doğrudan belirtilmiş policy kuralı.
    ObservationEffect.DELETE: EffectPolicy.BLOCKED,
    # Bölüm 6.13: "Unknown effect ... BLOCK".
    ObservationEffect.UNKNOWN: EffectPolicy.BLOCKED,
}
"""Canonical effect -> güvenlik sınıfı. Business action string'lerine değil, yalnızca AWE
Core'un kendi canonical effect sözlüğüne dayanır; proje bazında override edilebilir."""


@dataclass(frozen=True, slots=True)
class ScreenEvidenceConfig:
    min_supporting_sessions: int = 2
    """Bölüm 6.8: "En az 2 distinct session aynı exact screen'i desteklemeli"."""


@dataclass(frozen=True, slots=True)
class RiskConfig:
    effect_policy: dict[ObservationEffect, EffectPolicy] = field(
        default_factory=lambda: dict(DEFAULT_EFFECT_POLICY)
    )
    mixed_outcome_rate_threshold: float = 0.3
    """`failure_rate` veya `cancel_rate` bu eşiği geçerse `MIXED_OBSERVED_OUTCOMES` reason
    code'u eklenir (bölüm 6.13: "tek başına block nedeni değildir" — yalnızca bir reason,
    karar üzerinde otomatik escalation etkisi yoktur)."""
    min_data_quality_for_allow: float = 0.5
    """Scope içindeki adımların ne kadarının mapping_warnings taşımadığı oranı bu eşiğin
    altındaysa `CRITICAL_QUALITY_FLAG` ile BLOCK (bölüm 6.13: "kritik quality flag BLOCK")."""


@dataclass(frozen=True, slots=True)
class LifecycleConfig:
    dismiss_cooldown_days: int = 14
    stale_after_days: float = 30.0
    """Bir suggestion'ın son gözlenen occurrence'tan bu kadar gün sonra STALE'e düşmesi.
    Habit Evaluator artık bir liveness/regularity skoru üretmediği için (bölüm 6.7) lifecycle
    kendi basit eşiğini `HabitEvidence.last_seen_at` üzerinden doğrudan hesaplar."""


@dataclass(frozen=True, slots=True)
class EngineConfig:
    episode: EpisodeConfig = field(default_factory=EpisodeConfig)
    habit: HabitConfig = field(default_factory=HabitConfig)
    screen_evidence: ScreenEvidenceConfig = field(default_factory=ScreenEvidenceConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    lifecycle: LifecycleConfig = field(default_factory=LifecycleConfig)
    timezone: str = "UTC"
    """Habit gün-sınırı hesapları için proje/uygulama zaman dilimi."""


def default_engine_config() -> EngineConfig:
    return EngineConfig()
