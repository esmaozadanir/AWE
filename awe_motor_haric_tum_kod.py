# =============================================================================
# AWE — src/awe altındaki TÜM kodun (motor katmanları dahil) tek dosyada
# birleştirilmiş hali.
#
# Bu dosya ÇALIŞTIRILABİLİR DEĞİLDİR — sadece okuma/inceleme/paylaşım amaçlıdır.
# Her bölüm, gerçek repodaki dosya yolunu başlıkta taşır. Dosya sırası:
# önce motor DIŞI katmanlar (domain, adapter, ordering, series, persistence,
# services, api, config, testing), sonunda motor katmanları (families, habit,
# planner, risk, benefit, selection, lifecycle).
# =============================================================================


# =============================================================================
# FILE: src/awe/domain/__init__.py
# =============================================================================
"""AWE Core domain modelleri.

Bu paket, hiçbir uygulamaya özel iş kavramı (order, course, lesson, product vb.) içermez.
Adapter/Mapping ve proje konfigürasyonu bunun dışındadır. `tests/scenarios/
test_domain_universality.py` bu kısıtı otomatik olarak denetler.
"""


# =============================================================================
# FILE: src/awe/domain/enums.py
# =============================================================================
"""AWE Core'un paylaştığı, uygulamadan bağımsız sabit kelime dağarcığı.

Buradaki değerler AWE Core'un kendi canonical sözleşmesidir (spesifikasyon bölüm 16-27).
Müşteriye özel iş isimleri (örn. "purchase", "lesson_complete") bu modülde bulunmaz;
onlar yalnızca Adapter/Mapping ve proje konfigürasyonu seviyesinde ortaya çıkar.
"""

from __future__ import annotations

from enum import StrEnum


class ObservationSource(StrEnum):
    CLIENT = "client"
    SERVER = "server"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ObservationRole(StrEnum):
    CONTEXT = "context"
    ACTION = "action"
    OUTCOME = "outcome"
    NOISE = "noise"


class ObservationEffect(StrEnum):
    VIEW = "view"
    ROUTE = "route"
    OPEN_MODAL = "open_modal"
    CLOSE_MODAL = "close_modal"
    QUERY = "query"
    SELECT = "select"
    INPUT = "input"
    CONTROL = "control"
    CREATE = "create"
    PREPARE = "prepare"
    """Eski sözlükten kalan, PREFILL anchor seçiminde hâlâ kullanılan hazırlık eylemi."""
    UPDATE = "update"
    SUBMIT = "submit"
    DELETE = "delete"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SHARE = "share"
    EXTERNAL = "external"
    NAVIGATE_BACK = "navigate_back"
    """Geri navigasyon (bölüm 40-41'deki 'back' örneğinin canonical karşılığı). Uygulamadan
    bağımsız, evrensel bir UI birincil eylemi olduğu için spesifikasyonun bölüm 19'da izin
    verdiği şekilde temel sözlüğe eklenmiştir; detour normalizasyonu (bölüm 41) bu değeri
    tetikleyici olarak kullanır — kaldırılırsa geri-basma normalizasyonunun tetiklenecek bir
    sinyali kalmaz, bu yüzden yeni sözlüğe ek olarak korunur."""
    NONE = "none"
    UNKNOWN = "unknown"


class ObservationTrigger(StrEnum):
    BUTTON = "button"
    KEYBOARD = "keyboard"
    VOICE = "voice"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    DRAG = "drag"
    SCROLL = "scroll"
    HOVER = "hover"
    FOCUS = "focus"
    HARDWARE = "hardware"
    BIOMETRIC = "biometric"
    DEEPLINK = "deeplink"
    NOTIFICATION = "notification"
    SHORTCUT = "shortcut"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"
    LIFECYCLE = "lifecycle"
    SENSOR = "sensor"
    API = "api"
    WEBHOOK = "webhook"
    ADMIN = "admin"
    SYSTEM = "system"
    """Eski, genel "sistem" tetikleyicisi. Yeni sınıflandırma bunun yerine automatic/scheduled/
    lifecycle/sensor gibi daha ayrıntılı değerleri kullanır; bu değer yalnızca geriye dönük
    uyumluluk için korunur ve sınıflandırma gruplarının hiçbirine dahil değildir (bkz.
    `awe.adapter.classification`)."""
    UNKNOWN = "unknown"


class EventClassification(StrEnum):
    """Ham event'in temiz action akışındaki rolü (bkz. `awe.adapter.classification`).

    `ObservationRole`'dan bağımsızdır: yalnızca `trigger`/`effect`/`status` üçlüsünden
    yapısal olarak türetilir, hiçbir role alanına veya role tahminine dayanmaz."""

    ACTION = "action"
    CONTEXT = "context"
    IGNORE = "ignore"


class ObservationStatus(StrEnum):
    SUCCESS = "success"
    FAIL = "fail"
    CANCEL = "cancel"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class OrderingConfidence(StrEnum):
    """Session içi sıralamanın gerçek temporal sıraya güven derecesi (bölüm 33)."""

    HIGH = "high"
    LOW = "low"


class FamilyMatchOutcome(StrEnum):
    MATCH = "match"
    VARIANT_MATCH = "variant_match"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


class FieldState(StrEnum):
    """Bir PREFILL binding'inin family seviyesindeki kararlılığı (bölüm 75). UNKNOWN != VARIABLE."""

    STABLE = "stable"
    VARIABLE = "variable"
    UNKNOWN = "unknown"


class PlanType(StrEnum):
    NAVIGATE = "navigate"
    PREFILL = "prefill"


class RiskDecisionType(StrEnum):
    ALLOW = "allow"
    ALLOW_WITH_REVIEW = "allow_with_review"
    REDUCE_BINDINGS = "reduce_bindings"
    DOWNGRADE_TO_NAVIGATE = "downgrade_to_navigate"
    BLOCK = "block"


class EffectPolicy(StrEnum):
    """Proje konfigürasyonunun bir `ObservationEffect` için tanımladığı güvenlik sınıfı."""

    SAFE = "safe"
    REVIEW = "review"
    BLOCKED = "blocked"


class LivenessState(StrEnum):
    LIVE = "live"
    WATCH = "watch"
    STALE = "stale"


class HabitDecision(StrEnum):
    PASS = "pass"
    PENDING_EVIDENCE = "pending_evidence"
    NOT_HABIT = "not_habit"


class SuggestionState(StrEnum):
    PENDING_EVIDENCE = "pending_evidence"
    ELIGIBLE = "eligible"
    ACTIVE = "active"
    STALE = "stale"
    DISMISSED = "dismissed"
    INVALIDATED = "invalidated"


class ReasonCode(StrEnum):
    INSUFFICIENT_OCCURRENCES = "insufficient_occurrences"
    INSUFFICIENT_DISTINCT_SESSIONS = "insufficient_distinct_sessions"
    INSUFFICIENT_DISTINCT_DAYS = "insufficient_distinct_days"
    ONE_DAY_BURST = "one_day_burst"
    STALE_BEHAVIOR = "stale_behavior"
    AMBIGUOUS_FAMILY = "ambiguous_family"
    LOW_COHESION = "low_cohesion"
    UNSTABLE_TARGET = "unstable_target"
    UNKNOWN_TARGET = "unknown_target"
    LOW_BINDING_COVERAGE = "low_binding_coverage"
    RECENT_PARAMETER_DRIFT = "recent_parameter_drift"
    RESOLVER_UNSUPPORTED = "resolver_unsupported"
    RUNTIME_VALIDATION_FAILED = "runtime_validation_failed"
    REVIEW_REQUIRED = "review_required"
    PREFILL_REDUCED = "prefill_reduced"
    PREFILL_DOWNGRADED = "prefill_downgraded"
    EXECUTE_BLOCKED = "execute_blocked"
    BENEFIT_TOO_LOW = "benefit_too_low"
    DUPLICATE_PLAN = "duplicate_plan"
    DOMINATED_PLAN = "dominated_plan"
    NO_PLAN_CANDIDATE = "no_plan_candidate"


# =============================================================================
# FILE: src/awe/domain/observation.py
# =============================================================================
"""Canonical Observation modeli (spesifikasyon bölüm 30).

Observation, müşteriye özel raw event'in Adapter tarafından üretilen, uygulamadan bağımsız
karşılığıdır. Aşağı katmanların hiçbiri bir daha müşterinin ham telemetry formatını görmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)


@dataclass(frozen=True, slots=True)
class ObservationQuality:
    """Adapter'ın canonicalization sırasında ürettiği veri kalitesi kanıtı."""

    has_screen: bool
    has_widget: bool
    has_session_id: bool
    is_synthetic_session: bool = False
    mapping_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Observation:
    event_id: str
    project_id: str
    subject_id: str
    session_id: str
    timestamp: datetime

    source: ObservationSource

    action: str
    role: ObservationRole
    effect: ObservationEffect
    trigger: ObservationTrigger

    screen: str | None
    widget: str | None

    target: str | None
    """Hedef referansı (ör. tıklanan öğenin id'si). `None` iki durumu birden temsil eder:
    mapping target'ı hiç izlemiyor ya da bu event için raw değer boş — ikisi de aşağı
    katmanlar için "bilinen, kararlı bir hedef yok" anlamına gelir. Boş string (`""`),
    mapping target'ı izliyor ama bu event'in AÇIKÇA hedefi olmadığını (ör. "logout")
    `None`'dan ayırt etmek için kullanılır (bkz. `awe.planner.state_reconstruction`)."""
    parameters: dict[str, str] = field(default_factory=dict)

    status: ObservationStatus = ObservationStatus.UNKNOWN
    breaks_episode: bool = False

    app_version: str | None = None
    mapping_version: str = "unversioned"

    quality: ObservationQuality = field(
        default_factory=lambda: ObservationQuality(
            has_screen=False, has_widget=False, has_session_id=False
        )
    )


# =============================================================================
# FILE: src/awe/domain/tokens.py
# =============================================================================
"""Karşılaştırma için canonical davranış sembolü ve adım modeli.

Tasarım kararı (bkz. IMPLEMENTATION_PLAN.md 2.3): karşılaştırma sembolü yalnızca
`(action, effect)` ikilisidir. `screen` ve `widget` sembolün bir parçası değil,
ayrıştırıcı ağırlıklandırmaya tabi bağlamsal kanıttır — bu sayede widget rename veya
ortak başlangıç ekranı gibi durumlar Family kimliğini kırmaz (bölüm 22-24, 115).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ObservationEffect, ObservationStatus

Symbol = tuple[str, str]
"""(action, effect) — Family karşılaştırmasının atomik birimi."""


@dataclass(frozen=True, slots=True)
class BehaviorToken:
    action: str
    effect: ObservationEffect

    @property
    def symbol(self) -> Symbol:
        return (self.action, self.effect.value)


@dataclass(frozen=True, slots=True)
class BehaviorStep:
    """Normalize edilmiş dizideki tek bir adım: karşılaştırma sembolü + bağlamsal kanıt."""

    token: BehaviorToken
    screen: str | None
    widget: str | None
    status: ObservationStatus
    observation_index: int
    """Bu adımın ait olduğu ham Observation'ın occurrence içindeki sırası (izlenebilirlik)."""

    @property
    def symbol(self) -> Symbol:
        return self.token.symbol


# =============================================================================
# FILE: src/awe/domain/series.py
# =============================================================================
"""O-Series modeli: tek session içerisindeki bir behavior attempt/occurrence (bölüm 35)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import ObservationStatus, ObservationTrigger, OrderingConfidence
from awe.domain.observation import Observation
from awe.domain.tokens import BehaviorStep, Symbol


@dataclass(frozen=True, slots=True)
class RetryEvidence:
    symbol: Symbol
    failed_attempts: int
    """Aynı sembolün normalize dizide tek adıma sıkıştırılmadan önceki başarısız deneme sayısı."""


@dataclass(frozen=True, slots=True)
class OSeries:
    series_id: str
    project_id: str
    subject_id: str
    session_id: str

    started_at: datetime
    ended_at: datetime
    ordering_confidence: OrderingConfidence

    raw_observations: tuple[Observation, ...]
    """Ham Observation dizisi — normalizasyon bu kanıtı yok etmez (bölüm 36)."""

    normalized_steps: tuple[BehaviorStep, ...]
    """Family karşılaştırması için üretilen, detour/retry sıkıştırılmış projeksiyon."""

    retries: tuple[RetryEvidence, ...]
    detour_observation_count: int
    ended_by_breaks_episode: bool

    entry_trigger: ObservationTrigger
    entry_screen: str | None

    has_shortcut_trigger: bool
    """Bu occurrence bir shortcut tetiklemesiyle mi başladı (bölüm 68)."""

    final_status: ObservationStatus

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(step.symbol for step in self.normalized_steps)

    @property
    def is_empty(self) -> bool:
        return len(self.normalized_steps) == 0


# =============================================================================
# FILE: src/awe/domain/family.py
# =============================================================================
"""Behavior Family modeli: farklı sessionlardaki O-Series'lerin toplandığı davranış ailesi.

Yapı, tek bir exact sequence yerine sınırlı sayıda temsilci variant ve bunlar üzerinden
türetilen core/optional ilişki tablosu üzerine kuruludur (bölüm 51, IMPLEMENTATION_PLAN.md 2.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import FamilyMatchOutcome
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class FamilyVariant:
    symbols: tuple[Symbol, ...]
    support: int
    """Bu tam normalize diziye sahip üye O-Series sayısı (exact variant compression, bölüm 47)."""
    last_observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CoreRelationship:
    predecessor: Symbol
    successor: Symbol
    coverage: float
    """Bu ardışık çiftin temsilci variant'lar içindeki kapsama oranı."""
    is_core: bool


@dataclass
class BehaviorFamily:
    family_id: str
    project_id: str
    subject_id: str

    representative_variants: list[FamilyVariant] = field(default_factory=list)
    relationships: list[CoreRelationship] = field(default_factory=list)
    cohesion: float = 1.0

    member_series_ids: list[str] = field(default_factory=list)
    ambiguous_series_ids: list[str] = field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def core_symbols_in_order(self) -> list[Symbol]:
        """Core ilişkilerden türetilen, açıklanabilirlik amaçlı yaklaşık ana sıra."""
        core = [r for r in self.relationships if r.is_core]
        if not core:
            return list(self.representative_variants[0].symbols) if self.representative_variants else []
        ordered: list[Symbol] = []
        successors = {r.predecessor: r.successor for r in core}
        starts = {r.predecessor for r in core} - {r.successor for r in core}
        current: Symbol | None = next(iter(starts), core[0].predecessor)
        seen: set[Symbol] = set()
        while current is not None and current not in seen:
            ordered.append(current)
            seen.add(current)
            current = successors.get(current)
        return ordered

    @property
    def total_support(self) -> int:
        return sum(v.support for v in self.representative_variants)


@dataclass(frozen=True, slots=True)
class FamilyMatchDecision:
    outcome: FamilyMatchOutcome
    family_id: str | None
    best_similarity: float
    core_coverage: float
    ambiguous_family_ids: tuple[str, ...] = ()


# =============================================================================
# FILE: src/awe/domain/habit.py
# =============================================================================
"""Habit katmanının kanıt ve karar modelleri (bölüm 61-67)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import HabitDecision, LivenessState, ReasonCode


@dataclass(frozen=True, slots=True)
class HabitEvidence:
    organic_occurrences: int
    distinct_sessions: int
    distinct_days: int

    first_seen_at: datetime
    last_seen_at: datetime
    active_span_days: int

    top_day_share: float
    top_session_share: float

    median_gap_days: float | None
    """Ardışık aktif günler arası medyan boşluk. <3 farklı gün varsa None (bölüm 66)."""

    regularity: float | None
    """0-1 arası düzenlilik kanıtı. Anlamlı örneklem yoksa None — asla 1.0'a düşürülmez."""

    staleness_ratio: float | None
    liveness: LivenessState

    shortcut_utility_occurrences: int
    """trigger=shortcut olan occurrence sayısı — organic_occurrences'a dahil değildir (bölüm 68)."""

    support_score: float
    """Doygunlaşan (saturating) support skoru — hard gate değil, açıklanabilirlik/sıralama içindir."""

    habit_strength: float
    """support_score, regularity ve liveness'i birleştiren, yalnızca gate geçildikten sonra
    anlamlı olan soft skor. Hiçbir hard gate kararını değiştirmez."""


@dataclass(frozen=True, slots=True)
class HabitAssessment:
    family_id: str
    decision: HabitDecision
    evidence: HabitEvidence | None
    reason_codes: tuple[ReasonCode, ...] = ()


# =============================================================================
# FILE: src/awe/domain/plan.py
# =============================================================================
"""Shortcut Planner çıktı modelleri: ShortcutAnchor, FieldBinding, PlanCandidate.

`destination` kavramı yoktur (bölüm 3.5, 70). Anchor bir index değil, family core sırası
içindeki yapısal bir sembol referansıdır (bölüm 71); her occurrence'ta kendi normalize
dizisi içinde sembol eşleştirmesiyle çözülür.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import FieldState, PlanType
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class ShortcutAnchor:
    symbol: Symbol
    screen: str | None
    core_position: int
    """Family core sırasındaki konum — yalnızca açıklanabilirlik/loglama amaçlıdır, occurrence
    çözümlemesi bu index'e değil `symbol` eşleşmesine dayanır."""


@dataclass(frozen=True, slots=True)
class FieldBinding:
    """Anchor öncesi state'te gözlenen bir alanın (target ya da parametre) kararlılığı."""

    field_name: str
    state: FieldState
    dominant_value: str | None
    dominance: float
    coverage: float
    sample_size: int
    recent_dominance: float | None
    """Son-K pencere içindeki dominance — concept drift kanıtı (bölüm 77). Yetersiz veri varsa None."""


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    plan_id: str
    family_id: str
    plan_type: PlanType
    anchor: ShortcutAnchor
    bindings: tuple[FieldBinding, ...]
    target_binding: FieldBinding | None
    supporting_occurrences: int


# =============================================================================
# FILE: src/awe/domain/risk.py
# =============================================================================
"""Risk katmanının kanıt ve karar modelleri (bölüm 79-83)."""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import EffectPolicy, ReasonCode, RiskDecisionType


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    effect_policy: EffectPolicy
    anchor_coverage: float
    state_confidence: float

    target_dominance: float | None
    target_coverage: float | None
    binding_dominance: float | None
    binding_coverage: float | None

    sample_size: int
    recent_drift: bool

    completion_rate: float
    failure_rate: float
    cancel_rate: float

    resolver_supported: bool
    requires_review: bool
    runtime_validation_passed: bool | None

    data_quality_score: float
    family_ambiguous: bool
    family_cohesion: float


@dataclass(frozen=True, slots=True)
class RiskDecisionResult:
    plan_id: str
    decision: RiskDecisionType
    evidence: RiskEvidence
    reason_codes: tuple[ReasonCode, ...]
    reduced_bindings: tuple[str, ...] = ()


# =============================================================================
# FILE: src/awe/domain/benefit.py
# =============================================================================
"""Benefit katmanının kanıt modeli (bölüm 84-89)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenefitEvidence:
    plan_id: str
    median_saved_actions: float
    p25_saved_actions: float
    p75_saved_actions: float
    benefit_coverage: float
    sample_size: int
    meets_minimum: bool


# =============================================================================
# FILE: src/awe/domain/suggestion.py
# =============================================================================
"""Final Selection çıktısı ve lifecycle modeli (bölüm 91-95)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import ReasonCode, SuggestionState


@dataclass
class Suggestion:
    suggestion_id: str
    project_id: str
    subject_id: str
    family_id: str

    primary_plan_id: str
    fallback_plan_ids: tuple[str, ...]

    state: SuggestionState
    reason_codes: tuple[ReasonCode, ...] = field(default_factory=tuple)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismiss_cooldown_until: datetime | None = None


# =============================================================================
# FILE: src/awe/adapter/__init__.py
# =============================================================================
from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.adapter.observation_builder import AdapterValidationError, build_observation

__all__ = [
    "AdapterMapping",
    "FieldRule",
    "TargetRule",
    "AdapterValidationError",
    "build_observation",
]


# =============================================================================
# FILE: src/awe/adapter/mapping.py
# =============================================================================
"""Adapter mapping sözleşmesi: müşteriye özel raw event alanlarının canonical alanlara
deklaratif olarak eşlenmesi (bölüm 31-32).

AWE Core, bu modülü kullanarak hiçbir müşteriye özel Python kodu yazmadan farklı raw
telemetry formatlarını canonical Observation'a çevirir. Yeni bir müşteri entegrasyonu,
yeni kod değil yeni bir `AdapterMapping` konfigürasyonu demektir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def resolve_path(raw: dict[str, Any], path: str) -> Any:
    """Nokta ayraçlı bir path ile iç içe sözlükten değer okur (ör. 'data.screen')."""

    current: Any = raw
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


@dataclass(frozen=True, slots=True)
class FieldRule:
    """Bir canonical alanın raw veriden nasıl türetileceğini tanımlar.

    `path` verilmemişse alan her zaman `default` değerini alır. `value_map` verilmişse
    okunan ham değer önce oradan geçirilir; eşleşme yoksa `default`'a düşer — engine hiçbir
    zaman bilinmeyen bir ham değeri kendi kendine yorumlamaz.
    """

    path: str | None = None
    value_map: dict[str, str] = field(default_factory=dict)
    default: str = "unknown"

    def resolve(self, raw: dict[str, Any]) -> str:
        if self.path is None:
            return self.default
        raw_value = resolve_path(raw, self.path)
        if raw_value is None:
            return self.default
        raw_value = str(raw_value)
        if self.value_map:
            return self.value_map.get(raw_value, self.default)
        return raw_value


@dataclass(frozen=True, slots=True)
class TargetRule:
    ref_path: str | None = None


@dataclass(frozen=True, slots=True)
class AdapterMapping:
    mapping_version: str

    event_id_path: str
    project_id_path: str
    subject_id_path: str
    session_id_path: str
    timestamp_path: str
    action_key_path: str
    action_key_value_map: dict[str, str] = field(default_factory=dict)
    """Ham action string'ini normalize etmek için opsiyonel eşleme (bölüm 31: action normalization).
    Eşleşme yoksa ham değer aynen action_key olarak kullanılır — engine action_key'in kendi
    business anlamını tahmin etmez (bölüm 17)."""

    screen_path: str | None = None
    widget_path: str | None = None
    app_version_path: str | None = None
    duration_ms_path: str | None = None

    source: FieldRule = field(default_factory=lambda: FieldRule(default="client"))
    role: FieldRule = field(default_factory=lambda: FieldRule(default="action"))
    effect: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    trigger: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    status: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))

    target: TargetRule = field(default_factory=TargetRule)

    parameter_fields: dict[str, str] = field(default_factory=dict)
    """canonical parametre adı -> raw path. Metadata'dan yalnızca burada açıkça
    whitelist'lenen alanlar okunur (bölüm 29)."""

    breaks_episode_path: str | None = None
    breaks_episode_action_keys: frozenset[str] = frozenset()

    assume_timezone: str = "UTC"
    """Ham timestamp naive geldiğinde varsayılan olarak atanacak timezone."""


# =============================================================================
# FILE: src/awe/adapter/observation_builder.py
# =============================================================================
"""Raw event → canonical Observation dönüşümü.

AWE Core, bu modülden sonra hiçbir yerde müşterinin ham telemetry alan adlarını görmez
(bölüm 31: "AWE Core müşterinin özel telemetry formatını bilmemelidir").
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from awe.adapter.mapping import AdapterMapping, resolve_path
from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)
from awe.domain.observation import Observation, ObservationQuality


class AdapterValidationError(ValueError):
    """Raw event, mapping ile zorunlu alanları üretemeyecek kadar eksik/bozuk."""


def _require_str(raw: dict, path: str, *, field_name: str) -> str:
    value = resolve_path(raw, path)
    if value is None or str(value).strip() == "":
        raise AdapterValidationError(f"required field '{field_name}' missing at path '{path}'")
    return str(value).strip()


def _parse_timestamp(raw_value: str, mapping: AdapterMapping, warnings: list[str]) -> datetime:
    normalized = raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AdapterValidationError(f"unparseable timestamp: {raw_value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(mapping.assume_timezone))
        warnings.append(f"naive_timestamp_assumed_{mapping.assume_timezone}")
    return parsed.astimezone(UTC)


def _resolve_target(raw: dict, mapping: AdapterMapping) -> str | None:
    """Mapping target'ı hiç izlemiyorsa `None` (bilinmiyor), izliyor ama bu event'in raw
    değeri boşsa `""` (açıkça hedef yok), aksi halde ref string'i döner (bkz.
    `Observation.target` docstring'i)."""

    if mapping.target.ref_path is None:
        return None
    ref_value = resolve_path(raw, mapping.target.ref_path)
    return str(ref_value) if ref_value is not None else ""


def _resolve_action(raw: dict, mapping: AdapterMapping) -> str:
    raw_value = _require_str(raw, mapping.action_key_path, field_name="action")
    return mapping.action_key_value_map.get(raw_value, raw_value)


def _resolve_field_rule(
    raw: dict, rule_name: str, mapping: AdapterMapping, enum_type: type[StrEnum], warnings: list[str]
) -> str:
    rule = getattr(mapping, rule_name)
    raw_value = resolve_path(raw, rule.path) if rule.path else None
    if raw_value is None:
        return rule.default
    raw_value = str(raw_value).strip().lower()
    if rule.value_map:
        if raw_value in rule.value_map:
            return rule.value_map[raw_value]
        warnings.append(f"unmapped_{rule_name}_raw_value:{raw_value}")
        return rule.default
    if raw_value in {member.value for member in enum_type}:
        return raw_value
    warnings.append(f"unmapped_{rule_name}_raw_value:{raw_value}")
    return rule.default


def build_observation(raw: dict, mapping: AdapterMapping) -> Observation:
    warnings: list[str] = []

    event_id = _require_str(raw, mapping.event_id_path, field_name="event_id")
    project_id = _require_str(raw, mapping.project_id_path, field_name="project_id")
    subject_id = _require_str(raw, mapping.subject_id_path, field_name="subject_id")

    session_id = resolve_path(raw, mapping.session_id_path)
    has_session_id = session_id is not None and str(session_id).strip() != ""
    session_id = str(session_id).strip() if has_session_id else f"synthetic:{event_id}"

    raw_timestamp = _require_str(raw, mapping.timestamp_path, field_name="timestamp")
    timestamp = _parse_timestamp(raw_timestamp, mapping, warnings)

    action = _resolve_action(raw, mapping)

    source = ObservationSource(_resolve_field_rule(raw, "source", mapping, ObservationSource, warnings))
    role = ObservationRole(_resolve_field_rule(raw, "role", mapping, ObservationRole, warnings))
    effect = ObservationEffect(_resolve_field_rule(raw, "effect", mapping, ObservationEffect, warnings))
    trigger = ObservationTrigger(
        _resolve_field_rule(raw, "trigger", mapping, ObservationTrigger, warnings)
    )
    status = ObservationStatus(_resolve_field_rule(raw, "status", mapping, ObservationStatus, warnings))

    screen = resolve_path(raw, mapping.screen_path) if mapping.screen_path else None
    screen = str(screen).strip() if screen is not None else None
    widget = resolve_path(raw, mapping.widget_path) if mapping.widget_path else None
    widget = str(widget).strip() if widget is not None else None

    target = _resolve_target(raw, mapping)

    parameters: dict[str, str] = {}
    for canonical_name, path in mapping.parameter_fields.items():
        value = resolve_path(raw, path)
        if value is not None:
            parameters[canonical_name] = str(value)

    breaks_episode = False
    if mapping.breaks_episode_path is not None:
        breaks_episode = bool(resolve_path(raw, mapping.breaks_episode_path))
    if action in mapping.breaks_episode_action_keys:
        breaks_episode = True

    app_version = resolve_path(raw, mapping.app_version_path) if mapping.app_version_path else None
    app_version = str(app_version) if app_version is not None else None

    quality = ObservationQuality(
        has_screen=screen is not None,
        has_widget=widget is not None,
        has_session_id=has_session_id,
        is_synthetic_session=not has_session_id,
        mapping_warnings=tuple(warnings),
    )

    return Observation(
        event_id=event_id,
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        timestamp=timestamp,
        source=source,
        action=action,
        role=role,
        effect=effect,
        trigger=trigger,
        screen=screen,
        widget=widget,
        target=target,
        parameters=parameters,
        status=status,
        breaks_episode=breaks_episode,
        app_version=app_version,
        mapping_version=mapping.mapping_version,
        quality=quality,
    )


# =============================================================================
# FILE: src/awe/adapter/classification.py
# =============================================================================
"""Canonical Observation'dan ACTION/CONTEXT/IGNORE sınıflandırması.

Sınıflandırma yalnızca `trigger`, `effect` ve `status` üçlüsünden yapısal olarak türetilir.
`role` alanına, role tahminine ya da müşteriye özel `action`/`screen`/`widget` string'lerine
hiçbir zaman bakılmaz — aksi halde motor belirli bir uygulamaya özel davranmaya başlar
(bölüm 1). Sonuç kalıcı bir Observation alanı değildir; ihtiyaç anında hesaplanan bir
değerdir (bkz. `EventClassification`).
"""

from __future__ import annotations

from awe.domain.enums import EventClassification, ObservationEffect, ObservationStatus, ObservationTrigger
from awe.domain.observation import Observation

USER_TRIGGERS = frozenset(
    {
        ObservationTrigger.BUTTON,
        ObservationTrigger.KEYBOARD,
        ObservationTrigger.VOICE,
        ObservationTrigger.LONG_PRESS,
        ObservationTrigger.HARDWARE,
        ObservationTrigger.BIOMETRIC,
        ObservationTrigger.DEEPLINK,
        ObservationTrigger.NOTIFICATION,
    }
)

GESTURE_TRIGGERS = frozenset({ObservationTrigger.SWIPE, ObservationTrigger.DRAG})

PASSIVE_TRIGGERS = frozenset({ObservationTrigger.SCROLL, ObservationTrigger.HOVER, ObservationTrigger.FOCUS})

SYSTEM_TRIGGERS = frozenset(
    {
        ObservationTrigger.AUTOMATIC,
        ObservationTrigger.SCHEDULED,
        ObservationTrigger.LIFECYCLE,
        ObservationTrigger.SENSOR,
    }
)

NON_USER_TRIGGERS = frozenset(
    {
        ObservationTrigger.API,
        ObservationTrigger.WEBHOOK,
        ObservationTrigger.ADMIN,
        ObservationTrigger.SHORTCUT,
        ObservationTrigger.UNKNOWN,
    }
)

CONTEXT_EFFECTS = frozenset(
    {
        ObservationEffect.VIEW,
        ObservationEffect.ROUTE,
        ObservationEffect.OPEN_MODAL,
        ObservationEffect.CLOSE_MODAL,
    }
)

EMPTY_EFFECTS = frozenset({ObservationEffect.NONE, ObservationEffect.UNKNOWN})


def classify_event(observation: Observation) -> EventClassification:
    if observation.status != ObservationStatus.SUCCESS:
        return EventClassification.IGNORE

    if observation.effect in EMPTY_EFFECTS:
        return EventClassification.IGNORE

    # Saf view hiçbir zaman action adımı değildir.
    if observation.effect == ObservationEffect.VIEW:
        if observation.trigger in USER_TRIGGERS or observation.trigger in SYSTEM_TRIGGERS:
            return EventClassification.CONTEXT
        return EventClassification.IGNORE

    if observation.trigger in USER_TRIGGERS:
        return EventClassification.ACTION

    # Swipe/drag, view dışındaki bilinen bir sonuç doğuruyorsa action'dır.
    if observation.trigger in GESTURE_TRIGGERS:
        return EventClassification.ACTION

    # Scroll/hover/focus dizeye girmez.
    if observation.trigger in PASSIVE_TRIGGERS:
        return EventClassification.IGNORE

    # Sistem tarafından açılan ekran/modal yalnızca context'tir.
    if observation.trigger in SYSTEM_TRIGGERS:
        if observation.effect in {
            ObservationEffect.ROUTE,
            ObservationEffect.OPEN_MODAL,
            ObservationEffect.CLOSE_MODAL,
        }:
            return EventClassification.CONTEXT
        return EventClassification.IGNORE

    # api/webhook/admin/shortcut/unknown/system(legacy) — hiçbiri yukarıdaki gruplara
    # girmeyen tetikleyiciler de dahil (NON_USER_TRIGGERS + gruplanmamış legacy değerler).
    return EventClassification.IGNORE


# =============================================================================
# FILE: src/awe/ordering/__init__.py
# =============================================================================
from awe.ordering.order_session import group_by_session, order_session

__all__ = ["group_by_session", "order_session"]


# =============================================================================
# FILE: src/awe/ordering/order_session.py
# =============================================================================
"""Session içi deterministik Observation sıralaması (bölüm 33-34)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from awe.domain.enums import OrderingConfidence
from awe.domain.observation import Observation


def group_by_session(observations: Iterable[Observation]) -> dict[str, list[Observation]]:
    """Tek bir project_id + subject_id kapsamındaki Observation'ları session_id'ye böler.

    Çağıran taraf, girdi observation'ların tek bir proje ve subject'e ait olduğunu garanti
    etmelidir; bu fonksiyon projectId/subjectId izolasyonunu tekrar doğrulamaz.
    """

    groups: dict[str, list[Observation]] = defaultdict(list)
    for obs in observations:
        groups[obs.session_id].append(obs)
    return dict(groups)


def order_session(observations: Sequence[Observation]) -> tuple[list[Observation], OrderingConfidence]:
    """Bir session'ın observation'larını deterministik sıraya sokar.

    Sıralama yalnızca timestamp + event_id (tie-break) kullanır; girdi batch sırasından
    bağımsız olarak her zaman aynı sonucu üretir. Motor hiçbir zaman kaynaktan bir sıra
    numarası (sequenceNo) istemez ya da uydurmaz — aynı timestamp'e sahip iki observation'ın
    gerçek temporal sırası bilinmiyorsa bunu `OrderingConfidence.LOW` ile açıkça işaretleriz,
    event_id'ye göre yapılan tie-break sahte bir kesinlik iddiası değildir, yalnızca
    deterministik (her çalıştırmada aynı) bir sonuç garantisidir (bölüm 33).
    """

    if not observations:
        return [], OrderingConfidence.HIGH

    ordered = sorted(observations, key=lambda o: (o.timestamp, o.event_id))
    has_ambiguous_tie = any(
        ordered[i].timestamp == ordered[i + 1].timestamp for i in range(len(ordered) - 1)
    )
    confidence = OrderingConfidence.LOW if has_ambiguous_tie else OrderingConfidence.HIGH
    return ordered, confidence


# =============================================================================
# FILE: src/awe/series/__init__.py
# =============================================================================
from awe.series.extraction import extract_series
from awe.series.normalization import NormalizationResult, normalize_steps

__all__ = ["extract_series", "normalize_steps", "NormalizationResult"]


# =============================================================================
# FILE: src/awe/series/extraction.py
# =============================================================================
"""O-Series Extraction: session event stream → behavior attempt (occurrence) dizisi (bölüm 35).

Bu katman Habit hesaplamaz, Family clustering yapmaz, Risk/Benefit değerlendirmez — yalnızca
bir session'ın ham Observation akışını anlamlı occurrence sınırlarına böler.

Sınır kuralları:

* `breaksEpisode=true` — kesin, hard boundary (bölüm 39).
* Başarılı tamamlanma — `role=outcome` ya da `effect in {submit, confirm}` olan bir adımın
  `status=success` olması, doğal bir occurrence sonu sayılır. Bu, canonical `role`/`effect`/
  `status` sözlüğüne dayanan yapısal bir kuraldır; herhangi bir business action string'ine
  bakmaz.

Bu iki sınırın dışında kalan tek-session içi çoklu bağımsız davranış (tamamlanma sinyali
üretmeden konu değiştirme) MVP kapsamında ayrıştırılmaz; bu bilinçli bir sınırlamadır ve
`docs/architecture.md` içinde gerekçelendirilmiştir.

Bir occurrence bloğu belirlendikten sonra, o blok içinde karşılaştırma sembollerine hangi
adımların gireceği `classify_event` (ACTION/CONTEXT/IGNORE) ile belirlenir: yalnızca
ACTION'a sınıflanan adımlar normalize edilmiş projeksiyona girer; CONTEXT/IGNORE adımları
`raw_observations`'ta (audit amaçlı) kalmaya devam eder ama sembol dizisine hiç girmez.
"""

from __future__ import annotations

from awe.adapter.classification import classify_event
from awe.config.engine_config import FamilyConfig
from awe.domain.enums import (
    EventClassification,
    ObservationEffect,
    ObservationRole,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.domain.observation import Observation
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken
from awe.series.normalization import normalize_steps

_COMPLETION_EFFECTS = (ObservationEffect.SUBMIT, ObservationEffect.CONFIRM)


def _split_on_breaks_episode(observations: list[Observation]) -> list[list[Observation]]:
    blocks: list[list[Observation]] = []
    current: list[Observation] = []
    for obs in observations:
        current.append(obs)
        if obs.breaks_episode:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _is_completion(obs: Observation) -> bool:
    if obs.status != ObservationStatus.SUCCESS:
        return False
    return obs.role == ObservationRole.OUTCOME or obs.effect in _COMPLETION_EFFECTS


def _split_on_completion(observations: list[Observation]) -> list[list[Observation]]:
    blocks: list[list[Observation]] = []
    current: list[Observation] = []
    for obs in observations:
        current.append(obs)
        if _is_completion(obs):
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _to_behavior_step(obs: Observation, index: int) -> BehaviorStep:
    return BehaviorStep(
        token=BehaviorToken(action=obs.action, effect=obs.effect),
        screen=obs.screen,
        widget=obs.widget,
        status=obs.status,
        observation_index=index,
    )


def _build_series(
    block: list[Observation], ordering_confidence: OrderingConfidence, config: FamilyConfig
) -> OSeries:
    raw_steps = [
        _to_behavior_step(obs, idx)
        for idx, obs in enumerate(block)
        if classify_event(obs) == EventClassification.ACTION
    ]
    normalization = normalize_steps(raw_steps, config.detour_max_length)

    first, last = block[0], block[-1]
    series_id = f"{first.session_id}#{first.event_id}"

    return OSeries(
        series_id=series_id,
        project_id=first.project_id,
        subject_id=first.subject_id,
        session_id=first.session_id,
        started_at=first.timestamp,
        ended_at=last.timestamp,
        ordering_confidence=ordering_confidence,
        raw_observations=tuple(block),
        normalized_steps=tuple(normalization.steps),
        retries=tuple(normalization.retries),
        detour_observation_count=normalization.detour_step_count,
        ended_by_breaks_episode=last.breaks_episode,
        entry_trigger=first.trigger,
        entry_screen=first.screen,
        has_shortcut_trigger=any(o.trigger == ObservationTrigger.SHORTCUT for o in block),
        final_status=last.status,
    )


def extract_series(
    ordered_session_observations: list[Observation],
    ordering_confidence: OrderingConfidence,
    config: FamilyConfig,
) -> list[OSeries]:
    if not ordered_session_observations:
        return []

    series: list[OSeries] = []
    for episode_block in _split_on_breaks_episode(ordered_session_observations):
        for completion_block in _split_on_completion(episode_block):
            series.append(_build_series(completion_block, ordering_confidence, config))
    return series


# =============================================================================
# FILE: src/awe/series/normalization.py
# =============================================================================
"""Raw adım dizisinden karşılaştırma projeksiyonu: retry ve bounded detour normalizasyonu.

İki farklı örüntü kasıtlı olarak birbirinden ayrılır:

* **Retry** — aynı sembol ardışık tekrar ediyor ve önceki deneme `fail`/`cancel` durumunda
  (bölüm 42). Tek adıma sıkıştırılır, retry sayısı ayrıca tutulur.
* **Detour** — açık bir `navigate_back` sinyalinden sonra önceki bir sembole dönülüyor
  (bölüm 41). Yalnızca `effect=navigate_back` gözlenmişse tetiklenir; aksi halde tekrarlayan
  bir sembol otomatik olarak detour sayılmaz, çünkü bu gerçek bir loop olabilir (bölüm 114).
  Bu, action string'ine bakarak "back" tahmini yapmak yerine (yasak, bölüm 1) canonical
  `effect` sözlüğüne dayanan açık bir yapısal karardır.

Her iki örüntü de ham kanıtı silmez; yalnızca Family karşılaştırması için kullanılan
projeksiyonu etkiler (bölüm 36).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ObservationEffect, ObservationStatus
from awe.domain.series import RetryEvidence
from awe.domain.tokens import BehaviorStep

_RETRYABLE_STATUSES = (ObservationStatus.FAIL, ObservationStatus.CANCEL)


@dataclass(slots=True)
class NormalizationResult:
    steps: list[BehaviorStep]
    retries: list[RetryEvidence]
    detour_step_count: int


def normalize_steps(raw_steps: list[BehaviorStep], detour_max_length: int) -> NormalizationResult:
    result: list[BehaviorStep] = []
    retries: list[RetryEvidence] = []
    detour_step_count = 0
    pending_return_merge = False
    consecutive_back_pops = 0

    for step in raw_steps:
        if result and result[-1].symbol == step.symbol and result[-1].status in _RETRYABLE_STATUSES:
            if retries and retries[-1].symbol == step.symbol:
                retries[-1] = RetryEvidence(
                    symbol=step.symbol, failed_attempts=retries[-1].failed_attempts + 1
                )
            else:
                retries.append(RetryEvidence(symbol=step.symbol, failed_attempts=1))
            result[-1] = step
            pending_return_merge = False
            consecutive_back_pops = 0
            continue

        if step.token.effect == ObservationEffect.NAVIGATE_BACK:
            if result and consecutive_back_pops < detour_max_length:
                result.pop()
                detour_step_count += 1
                consecutive_back_pops += 1
                pending_return_merge = True
            else:
                # Yığın zaten boş (geri gidilecek kayıtlı bir adım kalmamış) ya da bounded
                # sınır aşılmış: `back` kendi başına anlamlı bir davranış adımı değildir,
                # bu yüzden literal bir sembol olarak eklenmez — sessizce yutulur. Aksi halde
                # art arda gelen fazla "back" basışları normalize edilmiş diziye yapay
                # "back" sembolleri olarak sızar (bölüm 41: detour normalizasyonu bounded
                # olmalı, ama ham kanıtı uydurma sembollerle kirletmemeli).
                detour_step_count += 1
                pending_return_merge = False
            continue

        if pending_return_merge and result and result[-1].symbol == step.symbol:
            detour_step_count += 1
            pending_return_merge = False
            continue

        result.append(step)
        pending_return_merge = False
        consecutive_back_pops = 0

    return NormalizationResult(steps=result, retries=retries, detour_step_count=detour_step_count)


# =============================================================================
# FILE: src/awe/persistence/__init__.py
# =============================================================================
from awe.persistence.database import create_database_engine, create_session_factory, session_scope
from awe.persistence.models import Base

__all__ = ["Base", "create_database_engine", "create_session_factory", "session_scope"]


# =============================================================================
# FILE: src/awe/persistence/database.py
# =============================================================================
"""Veritabanı engine/session kurulumu."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# FILE: src/awe/persistence/types.py
# =============================================================================
"""SQLite, `DateTime(timezone=True)` sütunlarında dahi timezone bilgisini kalıcı olarak
saklamaz; okuma sırasında naive bir datetime döner. Bu, aware/naive datetime karışmasına yol
açar (bölüm 15'in açıkça yasakladığı durum). `UTCDateTime`, hem yazarken UTC'ye normalize eder
hem de okurken eksik tzinfo'yu UTC olarak geri tamamlar — böylece PostgreSQL'de zaten doğru
davranan kod SQLite'ta da sessizce bozulmaz.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime kabul edilmez; UTC'ye normalize edilmiş bir değer bekleniyor")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


# =============================================================================
# FILE: src/awe/persistence/models.py
# =============================================================================
"""SQLAlchemy şema tanımları (bölüm 96).

Yalnızca portable tipler kullanılır (`String`, `Integer`, `Float`, `Boolean`,
`UTCDateTime`, `JSON`) — SQLite ve PostgreSQL arasında taşınabilirlik için
Postgres'e özgü tipler (`ARRAY`, `JSONB` vb.) kullanılmaz.

Normalize edilmiş O-Series adımları ayrı bir tabloda tutulmaz: bunlar `observations` tablosundan
(seri'ye ait ham kayıtlardan) deterministik biçimde yeniden hesaplanır — bu, normalizasyon
mantığının iki yerde bakımsız kalmasını önler ve tek doğruluk kaynağını (raw observation)
korur.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from awe.persistence.types import UTCDateTime


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "event_id", name="uq_events_project_event"),)


class ObservationRecord(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    effect: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)

    screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    widget: Mapped[str | None] = mapped_column(String(256), nullable=True)

    target: Mapped[str | None] = mapped_column(String(256), nullable=True)

    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    breaks_episode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)

    quality_has_screen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_has_widget: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_has_session_id: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quality_is_synthetic_session: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_mapping_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "event_id", name="uq_observations_project_event"),
        Index("ix_observations_subject_scope", "project_id", "subject_id", "session_id"),
        Index("ix_observations_series", "series_id"),
    )


class SeriesRecord(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(256), nullable=False)

    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ordering_confidence: Mapped[str] = mapped_column(String(16), nullable=False)

    ended_by_breaks_episode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entry_trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    has_shortcut_trigger: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    final_status: Mapped[str] = mapped_column(String(32), nullable=False)

    family_id: Mapped[int | None] = mapped_column(ForeignKey("families.id"), nullable=True)
    ambiguous_family_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (Index("ix_series_subject_scope", "project_id", "subject_id"),)


class FamilyRecord(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)

    representative_variants: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    relationships: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cohesion: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (Index("ix_families_subject_scope", "project_id", "subject_id"),)


class HabitEvaluationRecord(Base):
    __tablename__ = "habit_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False, unique=True)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class PlanCandidateRecord(Base):
    __tablename__ = "plan_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)

    plan_type: Mapped[str] = mapped_column(String(16), nullable=False)
    anchor: Mapped[dict] = mapped_column(JSON, nullable=False)
    bindings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    target_binding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supporting_occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    risk_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reduced_bindings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    benefit_median: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_p25: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_p75: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benefit_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    benefit_meets_minimum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (Index("ix_plan_candidates_family", "family_id"),)


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suggestion_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False, unique=True)

    primary_plan_id: Mapped[int] = mapped_column(ForeignKey("plan_candidates.id"), nullable=False)
    fallback_plan_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    dismiss_cooldown_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (Index("ix_suggestions_subject_scope", "project_id", "subject_id"),)


# =============================================================================
# FILE: src/awe/persistence/serialization.py
# =============================================================================
"""Domain modelleri ile JSON-uyumlu sözlükler arasında dönüşüm.

Bu modül yalnızca veri şekli dönüşümü yapar; hiçbir iş kuralı içermez.
"""

from __future__ import annotations

from datetime import datetime

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import (
    EffectPolicy,
    FieldState,
    HabitDecision,
    LivenessState,
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    PlanType,
    ReasonCode,
    RiskDecisionType,
)
from awe.domain.family import CoreRelationship, FamilyVariant
from awe.domain.habit import HabitEvidence
from awe.domain.observation import Observation, ObservationQuality
from awe.domain.plan import FieldBinding, PlanCandidate, ShortcutAnchor
from awe.domain.risk import RiskEvidence
from awe.persistence.models import ObservationRecord


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def observation_to_record(observation: Observation) -> ObservationRecord:
    return ObservationRecord(
        project_id=observation.project_id,
        subject_id=observation.subject_id,
        session_id=observation.session_id,
        event_id=observation.event_id,
        timestamp=observation.timestamp,
        source=observation.source.value,
        action=observation.action,
        role=observation.role.value,
        effect=observation.effect.value,
        trigger=observation.trigger.value,
        screen=observation.screen,
        widget=observation.widget,
        target=observation.target,
        parameters=dict(observation.parameters),
        status=observation.status.value,
        breaks_episode=observation.breaks_episode,
        app_version=observation.app_version,
        mapping_version=observation.mapping_version,
        quality_has_screen=observation.quality.has_screen,
        quality_has_widget=observation.quality.has_widget,
        quality_has_session_id=observation.quality.has_session_id,
        quality_is_synthetic_session=observation.quality.is_synthetic_session,
        quality_mapping_warnings=list(observation.quality.mapping_warnings),
    )


def record_to_observation(record: ObservationRecord) -> Observation:
    return Observation(
        event_id=record.event_id,
        project_id=record.project_id,
        subject_id=record.subject_id,
        session_id=record.session_id,
        timestamp=record.timestamp,
        source=ObservationSource(record.source),
        action=record.action,
        role=ObservationRole(record.role),
        effect=ObservationEffect(record.effect),
        trigger=ObservationTrigger(record.trigger),
        screen=record.screen,
        widget=record.widget,
        target=record.target,
        parameters=dict(record.parameters),
        status=ObservationStatus(record.status),
        breaks_episode=record.breaks_episode,
        app_version=record.app_version,
        mapping_version=record.mapping_version,
        quality=ObservationQuality(
            has_screen=record.quality_has_screen,
            has_widget=record.quality_has_widget,
            has_session_id=record.quality_has_session_id,
            is_synthetic_session=record.quality_is_synthetic_session,
            mapping_warnings=tuple(record.quality_mapping_warnings),
        ),
    )


def variant_to_dict(variant: FamilyVariant) -> dict:
    return {
        "symbols": [list(symbol) for symbol in variant.symbols],
        "support": variant.support,
        "last_observed_at": _iso(variant.last_observed_at),
    }


def dict_to_variant(data: dict) -> FamilyVariant:
    return FamilyVariant(
        symbols=tuple(tuple(symbol) for symbol in data["symbols"]),
        support=data["support"],
        last_observed_at=_parse_iso(data.get("last_observed_at")),
    )


def relationship_to_dict(relationship: CoreRelationship) -> dict:
    return {
        "predecessor": list(relationship.predecessor),
        "successor": list(relationship.successor),
        "coverage": relationship.coverage,
        "is_core": relationship.is_core,
    }


def dict_to_relationship(data: dict) -> CoreRelationship:
    return CoreRelationship(
        predecessor=tuple(data["predecessor"]),
        successor=tuple(data["successor"]),
        coverage=data["coverage"],
        is_core=data["is_core"],
    )


def binding_to_dict(binding: FieldBinding) -> dict:
    return {
        "field_name": binding.field_name,
        "state": binding.state.value,
        "dominant_value": binding.dominant_value,
        "dominance": binding.dominance,
        "coverage": binding.coverage,
        "sample_size": binding.sample_size,
        "recent_dominance": binding.recent_dominance,
    }


def dict_to_binding(data: dict) -> FieldBinding:
    return FieldBinding(
        field_name=data["field_name"],
        state=FieldState(data["state"]),
        dominant_value=data["dominant_value"],
        dominance=data["dominance"],
        coverage=data["coverage"],
        sample_size=data["sample_size"],
        recent_dominance=data["recent_dominance"],
    )


def anchor_to_dict(anchor: ShortcutAnchor) -> dict:
    return {"symbol": list(anchor.symbol), "screen": anchor.screen, "core_position": anchor.core_position}


def dict_to_anchor(data: dict) -> ShortcutAnchor:
    return ShortcutAnchor(
        symbol=tuple(data["symbol"]), screen=data["screen"], core_position=data["core_position"]
    )


def plan_candidate_to_dict(candidate: PlanCandidate) -> dict:
    return {
        "plan_id": candidate.plan_id,
        "family_id": candidate.family_id,
        "plan_type": candidate.plan_type.value,
        "anchor": anchor_to_dict(candidate.anchor),
        "bindings": [binding_to_dict(b) for b in candidate.bindings],
        "target_binding": binding_to_dict(candidate.target_binding) if candidate.target_binding else None,
        "supporting_occurrences": candidate.supporting_occurrences,
    }


def dict_to_plan_candidate(data: dict) -> PlanCandidate:
    return PlanCandidate(
        plan_id=data["plan_id"],
        family_id=data["family_id"],
        plan_type=PlanType(data["plan_type"]),
        anchor=dict_to_anchor(data["anchor"]),
        bindings=tuple(dict_to_binding(b) for b in data["bindings"]),
        target_binding=dict_to_binding(data["target_binding"]) if data["target_binding"] else None,
        supporting_occurrences=data["supporting_occurrences"],
    )


def risk_evidence_to_dict(evidence: RiskEvidence) -> dict:
    return {
        "effect_policy": evidence.effect_policy.value,
        "anchor_coverage": evidence.anchor_coverage,
        "state_confidence": evidence.state_confidence,
        "target_dominance": evidence.target_dominance,
        "target_coverage": evidence.target_coverage,
        "binding_dominance": evidence.binding_dominance,
        "binding_coverage": evidence.binding_coverage,
        "sample_size": evidence.sample_size,
        "recent_drift": evidence.recent_drift,
        "completion_rate": evidence.completion_rate,
        "failure_rate": evidence.failure_rate,
        "cancel_rate": evidence.cancel_rate,
        "resolver_supported": evidence.resolver_supported,
        "requires_review": evidence.requires_review,
        "runtime_validation_passed": evidence.runtime_validation_passed,
        "data_quality_score": evidence.data_quality_score,
        "family_ambiguous": evidence.family_ambiguous,
        "family_cohesion": evidence.family_cohesion,
    }


def dict_to_risk_evidence(data: dict) -> RiskEvidence:
    return RiskEvidence(
        effect_policy=EffectPolicy(data["effect_policy"]),
        anchor_coverage=data["anchor_coverage"],
        state_confidence=data["state_confidence"],
        target_dominance=data["target_dominance"],
        target_coverage=data["target_coverage"],
        binding_dominance=data["binding_dominance"],
        binding_coverage=data["binding_coverage"],
        sample_size=data["sample_size"],
        recent_drift=data["recent_drift"],
        completion_rate=data["completion_rate"],
        failure_rate=data["failure_rate"],
        cancel_rate=data["cancel_rate"],
        resolver_supported=data["resolver_supported"],
        requires_review=data["requires_review"],
        runtime_validation_passed=data["runtime_validation_passed"],
        data_quality_score=data["data_quality_score"],
        family_ambiguous=data["family_ambiguous"],
        family_cohesion=data["family_cohesion"],
    )


def reason_codes_to_list(codes: tuple[ReasonCode, ...]) -> list[str]:
    return [code.value for code in codes]


def list_to_reason_codes(values: list[str]) -> tuple[ReasonCode, ...]:
    return tuple(ReasonCode(value) for value in values)


def habit_evidence_to_dict(evidence: HabitEvidence) -> dict:
    return {
        "organic_occurrences": evidence.organic_occurrences,
        "distinct_sessions": evidence.distinct_sessions,
        "distinct_days": evidence.distinct_days,
        "first_seen_at": _iso(evidence.first_seen_at),
        "last_seen_at": _iso(evidence.last_seen_at),
        "active_span_days": evidence.active_span_days,
        "top_day_share": evidence.top_day_share,
        "top_session_share": evidence.top_session_share,
        "median_gap_days": evidence.median_gap_days,
        "regularity": evidence.regularity,
        "staleness_ratio": evidence.staleness_ratio,
        "liveness": evidence.liveness.value,
        "shortcut_utility_occurrences": evidence.shortcut_utility_occurrences,
        "support_score": evidence.support_score,
        "habit_strength": evidence.habit_strength,
    }


def dict_to_habit_evidence(data: dict) -> HabitEvidence:
    return HabitEvidence(
        organic_occurrences=data["organic_occurrences"],
        distinct_sessions=data["distinct_sessions"],
        distinct_days=data["distinct_days"],
        first_seen_at=datetime.fromisoformat(data["first_seen_at"]),
        last_seen_at=datetime.fromisoformat(data["last_seen_at"]),
        active_span_days=data["active_span_days"],
        top_day_share=data["top_day_share"],
        top_session_share=data["top_session_share"],
        median_gap_days=data["median_gap_days"],
        regularity=data["regularity"],
        staleness_ratio=data["staleness_ratio"],
        liveness=LivenessState(data["liveness"]),
        shortcut_utility_occurrences=data["shortcut_utility_occurrences"],
        support_score=data["support_score"],
        habit_strength=data["habit_strength"],
    )


def habit_decision_to_str(decision: HabitDecision) -> str:
    return decision.value


def str_to_habit_decision(value: str) -> HabitDecision:
    return HabitDecision(value)


def risk_decision_to_str(decision: RiskDecisionType) -> str:
    return decision.value


def str_to_risk_decision(value: str) -> RiskDecisionType:
    return RiskDecisionType(value)


def benefit_to_columns(benefit: BenefitEvidence) -> dict:
    return {
        "benefit_median": benefit.median_saved_actions,
        "benefit_p25": benefit.p25_saved_actions,
        "benefit_p75": benefit.p75_saved_actions,
        "benefit_coverage": benefit.benefit_coverage,
        "benefit_sample_size": benefit.sample_size,
        "benefit_meets_minimum": benefit.meets_minimum,
    }


def columns_to_benefit(plan_id: str, record) -> BenefitEvidence:
    return BenefitEvidence(
        plan_id=plan_id,
        median_saved_actions=record.benefit_median,
        p25_saved_actions=record.benefit_p25,
        p75_saved_actions=record.benefit_p75,
        benefit_coverage=record.benefit_coverage,
        sample_size=record.benefit_sample_size,
        meets_minimum=record.benefit_meets_minimum,
    )


# =============================================================================
# FILE: src/awe/persistence/repository.py
# =============================================================================
"""Analiz pipeline'ının ihtiyaç duyduğu okuma/yazma işlemleri.

Bu katman iş kuralı içermez; yalnızca domain nesneleri ile veritabanı satırları arasında
köprü kurar. Var olan family/series kimlikleri asla yeniden numaralandırılmaz — yalnızca
işlenmemiş (henüz bir seriye atanmamış) observation'lar üzerinden artımlı olarak genişletilir
(`docs/architecture.md`, "artımlı analiz" bölümü).

NOT: Bu dosya "motor hariç" bütünün bir parçası olarak dahil edilmiştir, ama
`fetch_families`/`create_family`/`update_family`/`upsert_habit_evaluation`/
`replace_plan_candidates`/`fetch_suggestion`/`upsert_suggestion` gibi fonksiyonlar
family/habit/plan/suggestion tablolarını okuyup yazar; bu kayıtların ANLAMINI üreten
families/habit/planner/risk/benefit/selection/lifecycle paketleri bu pakette DEĞİLDİR.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from awe.adapter.classification import classify_event
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import EventClassification, ObservationStatus, ObservationTrigger, OrderingConfidence
from awe.domain.family import BehaviorFamily
from awe.domain.habit import HabitAssessment
from awe.domain.observation import Observation
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskDecisionResult
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken
from awe.persistence.models import (
    EventRecord,
    FamilyRecord,
    HabitEvaluationRecord,
    ObservationRecord,
    PlanCandidateRecord,
    SeriesRecord,
    SuggestionRecord,
)
from awe.persistence.serialization import (
    binding_to_dict,
    dict_to_relationship,
    dict_to_variant,
    habit_evidence_to_dict,
    observation_to_record,
    record_to_observation,
    relationship_to_dict,
    risk_evidence_to_dict,
    variant_to_dict,
)
from awe.series.normalization import normalize_steps


def event_exists(session: Session, project_id: str, event_id: str) -> bool:
    stmt = select(EventRecord.id).where(EventRecord.project_id == project_id, EventRecord.event_id == event_id)
    return session.execute(stmt).first() is not None


def insert_event(
    session: Session, project_id: str, event_id: str, subject_id: str, received_at: datetime, raw_payload: dict
) -> None:
    session.add(
        EventRecord(
            project_id=project_id,
            event_id=event_id,
            subject_id=subject_id,
            received_at=received_at,
            raw_payload=raw_payload,
        )
    )


def insert_observation(session: Session, observation: Observation) -> None:
    session.add(observation_to_record(observation))


def fetch_unprocessed_observations(
    session: Session, project_id: str, subject_id: str
) -> tuple[list[Observation], dict[str, int]]:
    stmt = select(ObservationRecord).where(
        ObservationRecord.project_id == project_id,
        ObservationRecord.subject_id == subject_id,
        ObservationRecord.series_id.is_(None),
    )
    records = session.execute(stmt).scalars().all()
    observations = [record_to_observation(r) for r in records]
    db_id_by_event_id = {r.event_id: r.id for r in records}
    return observations, db_id_by_event_id


def fetch_families(session: Session, project_id: str, subject_id: str) -> list[tuple[int, BehaviorFamily]]:
    stmt = select(FamilyRecord).where(
        FamilyRecord.project_id == project_id, FamilyRecord.subject_id == subject_id
    )
    records = session.execute(stmt).scalars().all()
    result = []
    for record in records:
        family = BehaviorFamily(
            family_id=record.family_key,
            project_id=record.project_id,
            subject_id=record.subject_id,
            representative_variants=[dict_to_variant(v) for v in record.representative_variants],
            relationships=[dict_to_relationship(r) for r in record.relationships],
            cohesion=record.cohesion,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        result.append((record.id, family))
    return result


def create_family(
    session: Session, project_id: str, subject_id: str, family: BehaviorFamily, now: datetime
) -> int:
    record = FamilyRecord(
        family_key=family.family_id,
        project_id=project_id,
        subject_id=subject_id,
        representative_variants=[variant_to_dict(v) for v in family.representative_variants],
        relationships=[relationship_to_dict(r) for r in family.relationships],
        cohesion=family.cohesion,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record.id


def update_family(session: Session, family_db_id: int, family: BehaviorFamily, now: datetime) -> None:
    record = session.get(FamilyRecord, family_db_id)
    assert record is not None
    record.representative_variants = [variant_to_dict(v) for v in family.representative_variants]
    record.relationships = [relationship_to_dict(r) for r in family.relationships]
    record.cohesion = family.cohesion
    record.updated_at = now


def create_series(
    session: Session,
    series: OSeries,
    family_db_id: int | None,
    ambiguous_family_db_ids: list[int],
    db_id_by_event_id: dict[str, int],
) -> int:
    record = SeriesRecord(
        series_key=series.series_id,
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        started_at=series.started_at,
        ended_at=series.ended_at,
        ordering_confidence=series.ordering_confidence.value,
        ended_by_breaks_episode=series.ended_by_breaks_episode,
        entry_trigger=series.entry_trigger.value,
        entry_screen=series.entry_screen,
        has_shortcut_trigger=series.has_shortcut_trigger,
        final_status=series.final_status.value,
        family_id=family_db_id,
        ambiguous_family_ids=ambiguous_family_db_ids,
    )
    session.add(record)
    session.flush()

    for obs in series.raw_observations:
        db_id = db_id_by_event_id.get(obs.event_id)
        if db_id is not None:
            obs_record = session.get(ObservationRecord, db_id)
            if obs_record is not None:
                obs_record.series_id = record.id

    return record.id


def fetch_member_series(session: Session, family_db_id: int, detour_max_length: int) -> list[OSeries]:
    stmt = select(SeriesRecord).where(SeriesRecord.family_id == family_db_id).order_by(SeriesRecord.started_at)
    series_records = session.execute(stmt).scalars().all()

    result: list[OSeries] = []
    for series_record in series_records:
        obs_stmt = (
            select(ObservationRecord)
            .where(ObservationRecord.series_id == series_record.id)
            .order_by(ObservationRecord.timestamp)
        )
        observation_records = session.execute(obs_stmt).scalars().all()
        result.append(_rebuild_series(series_record, observation_records, detour_max_length))
    return result


def _rebuild_series(
    series_record: SeriesRecord, observation_records: Sequence[ObservationRecord], detour_max_length: int
) -> OSeries:
    observations = [record_to_observation(r) for r in observation_records]
    raw_steps = []
    for index, obs in enumerate(observations):
        if classify_event(obs) != EventClassification.ACTION:
            continue
        raw_steps.append(
            BehaviorStep(
                token=BehaviorToken(action=obs.action, effect=obs.effect),
                screen=obs.screen,
                widget=obs.widget,
                status=obs.status,
                observation_index=index,
            )
        )
    normalization = normalize_steps(raw_steps, detour_max_length)

    return OSeries(
        series_id=series_record.series_key,
        project_id=series_record.project_id,
        subject_id=series_record.subject_id,
        session_id=series_record.session_id,
        started_at=series_record.started_at,
        ended_at=series_record.ended_at,
        ordering_confidence=OrderingConfidence(series_record.ordering_confidence),
        raw_observations=tuple(observations),
        normalized_steps=tuple(normalization.steps),
        retries=tuple(normalization.retries),
        detour_observation_count=normalization.detour_step_count,
        ended_by_breaks_episode=series_record.ended_by_breaks_episode,
        entry_trigger=ObservationTrigger(series_record.entry_trigger),
        entry_screen=series_record.entry_screen,
        has_shortcut_trigger=series_record.has_shortcut_trigger,
        final_status=ObservationStatus(series_record.final_status),
    )


def upsert_habit_evaluation(session: Session, family_db_id: int, assessment: HabitAssessment, now: datetime) -> None:
    stmt = select(HabitEvaluationRecord).where(HabitEvaluationRecord.family_id == family_db_id)
    record = session.execute(stmt).scalar_one_or_none()
    evidence_dict = habit_evidence_to_dict(assessment.evidence) if assessment.evidence else None
    reason_codes = [c.value for c in assessment.reason_codes]
    if record is None:
        record = HabitEvaluationRecord(
            family_id=family_db_id,
            decision=assessment.decision.value,
            reason_codes=reason_codes,
            evidence=evidence_dict,
            evaluated_at=now,
        )
        session.add(record)
    else:
        record.decision = assessment.decision.value
        record.reason_codes = reason_codes
        record.evidence = evidence_dict
        record.evaluated_at = now


def replace_plan_candidates(
    session: Session,
    family_db_id: int,
    evaluated: list[tuple[PlanCandidate, RiskDecisionResult, BenefitEvidence]],
    now: datetime,
) -> dict[str, int]:
    session.query(PlanCandidateRecord).filter(PlanCandidateRecord.family_id == family_db_id).delete()
    session.flush()

    db_id_by_plan_id: dict[str, int] = {}
    for candidate, risk, benefit in evaluated:
        record = PlanCandidateRecord(
            plan_key=f"{candidate.plan_id}-{uuid.uuid4().hex[:8]}",
            family_id=family_db_id,
            plan_type=candidate.plan_type.value,
            anchor={
                "symbol": list(candidate.anchor.symbol),
                "screen": candidate.anchor.screen,
                "core_position": candidate.anchor.core_position,
            },
            bindings=[binding_to_dict(b) for b in candidate.bindings],
            target_binding=binding_to_dict(candidate.target_binding) if candidate.target_binding else None,
            supporting_occurrences=candidate.supporting_occurrences,
            risk_decision=risk.decision.value,
            risk_reason_codes=[c.value for c in risk.reason_codes],
            risk_evidence=risk_evidence_to_dict(risk.evidence),
            reduced_bindings=list(risk.reduced_bindings),
            benefit_median=benefit.median_saved_actions,
            benefit_p25=benefit.p25_saved_actions,
            benefit_p75=benefit.p75_saved_actions,
            benefit_coverage=benefit.benefit_coverage,
            benefit_sample_size=benefit.sample_size,
            benefit_meets_minimum=benefit.meets_minimum,
            evaluated_at=now,
        )
        session.add(record)
        session.flush()
        db_id_by_plan_id[candidate.plan_id] = record.id
    return db_id_by_plan_id


def fetch_plan_candidate(session: Session, plan_db_id: int) -> PlanCandidateRecord | None:
    return session.get(PlanCandidateRecord, plan_db_id)


def fetch_suggestion(session: Session, family_db_id: int) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.family_id == family_db_id)
    return session.execute(stmt).scalar_one_or_none()


def fetch_suggestion_by_key(session: Session, suggestion_key: str) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.suggestion_key == suggestion_key)
    return session.execute(stmt).scalar_one_or_none()


def upsert_suggestion(
    session: Session,
    project_id: str,
    subject_id: str,
    family_db_id: int,
    primary_plan_db_id: int,
    fallback_plan_db_ids: list[int],
    state: str,
    reason_codes: list[str],
    now: datetime,
    dismissed_at: datetime | None,
    dismiss_cooldown_until: datetime | None,
) -> SuggestionRecord:
    existing = fetch_suggestion(session, family_db_id)
    if existing is None:
        record = SuggestionRecord(
            suggestion_key=f"sugg-{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            subject_id=subject_id,
            family_id=family_db_id,
            primary_plan_id=primary_plan_db_id,
            fallback_plan_ids=fallback_plan_db_ids,
            state=state,
            reason_codes=reason_codes,
            created_at=now,
            updated_at=now,
            dismissed_at=dismissed_at,
            dismiss_cooldown_until=dismiss_cooldown_until,
        )
        session.add(record)
        session.flush()
        return record

    existing.primary_plan_id = primary_plan_db_id
    existing.fallback_plan_ids = fallback_plan_db_ids
    existing.state = state
    existing.reason_codes = reason_codes
    existing.updated_at = now
    existing.dismissed_at = dismissed_at
    existing.dismiss_cooldown_until = dismiss_cooldown_until
    return existing


def list_suggestions(
    session: Session, project_id: str, subject_id: str, states: set[str]
) -> list[SuggestionRecord]:
    stmt = select(SuggestionRecord).where(
        SuggestionRecord.project_id == project_id,
        SuggestionRecord.subject_id == subject_id,
        SuggestionRecord.state.in_(states),
    )
    return list(session.execute(stmt).scalars().all())


# =============================================================================
# FILE: src/awe/services/__init__.py
# =============================================================================
from awe.services.analysis import AnalysisSummary, FamilyAnalysisSummary, analyze_subject
from awe.services.ingestion import IngestOutcome, ingest_batch, ingest_event
from awe.services.suggestions import (
    PlanView,
    SuggestionView,
    dismiss_suggestion,
    list_subject_suggestions,
)

__all__ = [
    "analyze_subject",
    "AnalysisSummary",
    "FamilyAnalysisSummary",
    "ingest_event",
    "ingest_batch",
    "IngestOutcome",
    "list_subject_suggestions",
    "dismiss_suggestion",
    "SuggestionView",
    "PlanView",
]


# =============================================================================
# FILE: src/awe/services/ingestion.py
# =============================================================================
"""Raw event ingestion: idempotent kabul ve canonical Observation üretimi (bölüm 11, 97)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.adapter import AdapterValidationError, build_observation
from awe.config import ProjectConfig, log_event
from awe.persistence.repository import event_exists, insert_event, insert_observation


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    accepted: bool
    duplicate: bool
    event_id: str | None = None
    error: str | None = None


def ingest_event(
    session: Session, project_config: ProjectConfig, url_project_id: str, raw_event: dict, now: datetime
) -> IngestOutcome:
    try:
        observation = build_observation(raw_event, project_config.mapping)
    except AdapterValidationError as exc:
        return IngestOutcome(accepted=False, duplicate=False, error=str(exc))

    if observation.project_id != url_project_id:
        return IngestOutcome(
            accepted=False,
            duplicate=False,
            error=f"payload project_id '{observation.project_id}' does not match '{url_project_id}'",
        )

    if event_exists(session, observation.project_id, observation.event_id):
        return IngestOutcome(accepted=True, duplicate=True, event_id=observation.event_id)

    insert_event(session, observation.project_id, observation.event_id, observation.subject_id, now, raw_event)
    insert_observation(session, observation)
    log_event(
        "event_ingested",
        project_id=observation.project_id,
        subject_id=observation.subject_id,
        action=observation.action,
    )
    return IngestOutcome(accepted=True, duplicate=False, event_id=observation.event_id)


def ingest_batch(
    session: Session, project_config: ProjectConfig, url_project_id: str, raw_events: list[dict], now: datetime
) -> list[IngestOutcome]:
    return [ingest_event(session, project_config, url_project_id, raw_event, now) for raw_event in raw_events]


# =============================================================================
# FILE: src/awe/services/analysis.py
# =============================================================================
# NOT: Bu dosya motor paketlerinden (families, habit, planner, risk, benefit,
# selection, lifecycle) DOĞRUDAN import eder — orkestrasyon/bağlama koduDUR,
# motorun kendisi değildir. İçe aktardığı motor paketlerinin karşılıkları bu
# birleştirilmiş dosyada YOKTUR; bu yüzden bu bölüm tek başına çalıştırılamaz.
"""Subject analizi: pipeline'ın tamamını (ordering → ... → final selection) uçtan uca bağlar.

Her analiz isteği, o subject'in yalnızca HENÜZ bir O-Series'e atanmamış observation'larını
işler ve bunları mevcut, kimliği sabit family'lere ekler ya da yeni family tohumlar (bkz.
`awe.persistence.repository` modül dokümantasyonu — "artımlı analiz"). Habit/Planner/Risk/
Benefit/Selection katmanları ise her çalıştırmada dokunulan family'ler için baştan hesaplanır;
bu katmanların girdisi (bir family'nin üye occurrence sayısı) sınırlı olduğu için bu maliyetli
değildir ve artımlı-durum tutarlılığı hatalarından kaçınır (`docs/architecture.md`).

`analyze_subject`, üç doğal faza ayrılmıştır: yeni occurrence'ları mevcut/yeni family'lere
yerleştirme (`_match_new_series_into_families`), dokunulan her family için Habit → Planner →
Risk → Benefit → Selection zincirini çalıştırma (`_evaluate_families`) ve son olarak lifecycle
kararlarını kalıcı hale getirme (`_persist_lifecycle_decisions`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.benefit import evaluate_benefit  # motor paketi -- bu pakette yok
from awe.config import EngineConfig, ProjectConfig, log_event
from awe.domain.enums import FamilyMatchOutcome, HabitDecision, SuggestionState
from awe.domain.family import BehaviorFamily
from awe.domain.habit import HabitAssessment
from awe.domain.series import OSeries
from awe.families import (  # motor paketi -- bu pakette yok
    accept_series,
    compute_discriminative_weights,
    match_series,
    seed_family,
)
from awe.habit import evaluate_habit  # motor paketi -- bu pakette yok
from awe.lifecycle import next_state_for_reanalysis  # motor paketi -- bu pakette yok
from awe.ordering import group_by_session, order_session
from awe.persistence.repository import (
    create_family,
    create_series,
    fetch_families,
    fetch_member_series,
    fetch_suggestion,
    fetch_unprocessed_observations,
    replace_plan_candidates,
    update_family,
    upsert_habit_evaluation,
    upsert_suggestion,
)
from awe.persistence.serialization import reason_codes_to_list
from awe.planner import build_plan_candidates  # motor paketi -- bu pakette yok
from awe.risk import ResolverContract, evaluate_risk  # motor paketi -- bu pakette yok
from awe.selection import (  # motor paketi -- bu pakette yok
    EvaluatedCandidate,
    FamilyPlan,
    FamilySelection,
    dedupe_across_families,
    select_family_plan,
)
from awe.series import extract_series


@dataclass(frozen=True, slots=True)
class FamilyAnalysisSummary:
    family_key: str
    habit_decision: HabitDecision
    suggestion_state: SuggestionState | None


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    project_id: str
    subject_id: str
    new_series_count: int
    families: list[FamilyAnalysisSummary]


@dataclass(frozen=True, slots=True)
class _FamilyEvaluation:
    family: BehaviorFamily
    assessment: HabitAssessment
    selection: FamilySelection | None
    db_id_by_plan_id: dict[str, int]


def _extract_new_series(
    session: Session, project_id: str, subject_id: str, engine_config: EngineConfig
) -> tuple[list[OSeries], dict[str, int]]:
    observations, db_id_by_event_id = fetch_unprocessed_observations(session, project_id, subject_id)
    new_series: list[OSeries] = []
    for _session_id, session_observations in group_by_session(observations).items():
        ordered, confidence = order_session(session_observations)
        new_series.extend(extract_series(ordered, confidence, engine_config.family))
    return new_series, db_id_by_event_id


def _match_new_series_into_families(
    session: Session,
    project_id: str,
    subject_id: str,
    now: datetime,
    engine_config: EngineConfig,
    new_series: list[OSeries],
    db_id_by_event_id: dict[str, int],
    weights: dict,
    family_by_key: dict[str, tuple[int, BehaviorFamily]],
    member_series_cache: dict[int, list[OSeries]],
) -> None:
    """Her yeni O-Series'i mevcut bir family'ye ekler ya da yeni bir family tohumlar.

    `family_by_key` ve `member_series_cache` yerinde (in-place) güncellenir.
    """

    families_list = [family for _, family in family_by_key.values()]
    unseeded_counter = 0

    for series in new_series:
        if series.is_empty:
            create_series(session, series, None, [], db_id_by_event_id)
            continue

        decision = match_series(series.symbols, families_list, weights, engine_config.family)

        if decision.outcome in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH):
            assert decision.family_id is not None
            db_id, family = family_by_key[decision.family_id]
            accept_series(family, series.series_id, series.symbols, series.started_at, engine_config.family)
            update_family(session, db_id, family, now)
            create_series(session, series, db_id, [], db_id_by_event_id)
            member_series_cache[db_id].append(series)
            log_event(
                "family_matched",
                project_id=project_id,
                subject_id=subject_id,
                family_key=family.family_id,
                outcome=decision.outcome.value,
            )
        elif decision.outcome == FamilyMatchOutcome.AMBIGUOUS:
            ambiguous_db_ids = [family_by_key[fid][0] for fid in decision.ambiguous_family_ids]
            create_series(session, series, None, ambiguous_db_ids, db_id_by_event_id)
            log_event(
                "series_ambiguous",
                project_id=project_id,
                subject_id=subject_id,
                candidate_family_keys=list(decision.ambiguous_family_ids),
            )
        else:
            unseeded_counter += 1
            placeholder_id = f"pending-{unseeded_counter}"
            new_family = seed_family(
                placeholder_id,
                project_id,
                subject_id,
                series.series_id,
                series.symbols,
                series.started_at,
                engine_config.family,
            )
            db_id = create_family(session, project_id, subject_id, new_family, now)
            family_by_key[new_family.family_id] = (db_id, new_family)
            families_list.append(new_family)
            create_series(session, series, db_id, [], db_id_by_event_id)
            member_series_cache[db_id] = [series]
            log_event(
                "family_created", project_id=project_id, subject_id=subject_id, family_key=new_family.family_id
            )


def _evaluate_families(
    session: Session,
    project_id: str,
    subject_id: str,
    now: datetime,
    engine_config: EngineConfig,
    resolver: ResolverContract,
    family_by_key: dict[str, tuple[int, BehaviorFamily]],
    member_series_cache: dict[int, list[OSeries]],
) -> dict[int, _FamilyEvaluation]:
    """Her family için Habit → Planner → Risk → Benefit → Selection zincirini çalıştırır."""

    family_selections: dict[int, _FamilyEvaluation] = {}

    for db_id, family in family_by_key.values():
        members = member_series_cache.get(db_id) or fetch_member_series(
            session, db_id, engine_config.family.detour_max_length
        )
        assessment = evaluate_habit(family.family_id, members, now, engine_config.timezone, engine_config.habit)
        upsert_habit_evaluation(session, db_id, assessment, now)

        selection: FamilySelection | None = None
        db_id_by_plan_id: dict[str, int] = {}

        if assessment.decision == HabitDecision.PASS:
            log_event("habit_passed", project_id=project_id, subject_id=subject_id, family_key=family.family_id)
            candidates = build_plan_candidates(family, members, engine_config.planner, engine_config.risk)
            evaluated = []
            for candidate in candidates:
                risk_result = evaluate_risk(
                    candidate, family, members, resolver, engine_config.planner, engine_config.risk
                )
                log_fields = {"project_id": project_id, "subject_id": subject_id, "plan_id": candidate.plan_id}
                if risk_result.decision.value == "block":
                    log_event("risk_blocked", **log_fields)
                if risk_result.reduced_bindings:
                    log_event("binding_reduced", **log_fields)
                if risk_result.decision.value == "downgrade_to_navigate":
                    log_event("plan_downgraded", **log_fields)
                benefit_result = evaluate_benefit(candidate, members, engine_config.benefit)
                if not benefit_result.meets_minimum:
                    log_event("benefit_rejected", **log_fields)
                evaluated.append((candidate, risk_result, benefit_result))
            db_id_by_plan_id = replace_plan_candidates(session, db_id, evaluated, now)
            log_event(
                "plan_generated",
                project_id=project_id,
                subject_id=subject_id,
                family_key=family.family_id,
                count=len(candidates),
            )

            selection_input = [EvaluatedCandidate(candidate=c, risk=r, benefit=b) for c, r, b in evaluated]
            selection = select_family_plan(selection_input)
        else:
            log_event(
                "habit_pending",
                project_id=project_id,
                subject_id=subject_id,
                family_key=family.family_id,
                decision=assessment.decision.value,
            )
            replace_plan_candidates(session, db_id, [], now)

        family_selections[db_id] = _FamilyEvaluation(family, assessment, selection, db_id_by_plan_id)

    return family_selections


def _resolve_cross_family_duplicates(family_selections: dict[int, _FamilyEvaluation]) -> frozenset[str]:
    plans = [
        FamilyPlan(family_id=str(db_id), selection=evaluation.selection)
        for db_id, evaluation in family_selections.items()
        if evaluation.selection is not None
    ]
    _, duplicate_ids = dedupe_across_families(plans)
    return duplicate_ids


def _persist_lifecycle_decisions(
    session: Session,
    project_id: str,
    subject_id: str,
    now: datetime,
    family_selections: dict[int, _FamilyEvaluation],
) -> list[FamilyAnalysisSummary]:
    """Her family için nihai suggestion state'ini hesaplar ve kalıcı hale getirir."""

    duplicate_plan_ids = _resolve_cross_family_duplicates(family_selections)
    summaries: list[FamilyAnalysisSummary] = []

    for db_id, evaluation in family_selections.items():
        family, assessment, selection, db_id_by_plan_id = (
            evaluation.family,
            evaluation.assessment,
            evaluation.selection,
            evaluation.db_id_by_plan_id,
        )
        existing_suggestion = fetch_suggestion(session, db_id)
        liveness = assessment.evidence.liveness if assessment.evidence else None

        is_duplicate = selection is not None and selection.primary.candidate.plan_id in duplicate_plan_ids
        has_eligible_plan = selection is not None and not is_duplicate

        previous_state = SuggestionState(existing_suggestion.state) if existing_suggestion else None
        next_state = next_state_for_reanalysis(
            previous_state,
            existing_suggestion.dismiss_cooldown_until if existing_suggestion else None,
            assessment.decision,
            has_eligible_plan,
            liveness,
            now,
        )

        reason_codes: list[str] = []
        if selection is not None:
            reason_codes = reason_codes_to_list(selection.primary.risk.reason_codes)
        if is_duplicate:
            reason_codes = [*reason_codes, "duplicate_plan"]
        if assessment.reason_codes:
            reason_codes = [*reason_codes, *reason_codes_to_list(assessment.reason_codes)]

        if selection is not None and not is_duplicate:
            primary_db_id = db_id_by_plan_id[selection.primary.candidate.plan_id]
            fallback_db_ids = [db_id_by_plan_id[pid] for pid in selection.fallback_plan_ids]
        elif existing_suggestion is not None:
            primary_db_id = existing_suggestion.primary_plan_id
            fallback_db_ids = existing_suggestion.fallback_plan_ids
        else:
            summaries.append(FamilyAnalysisSummary(family.family_id, assessment.decision, None))
            continue

        stays_dismissed = next_state == SuggestionState.DISMISSED and existing_suggestion is not None
        dismissed_at = existing_suggestion.dismissed_at if stays_dismissed and existing_suggestion else None
        cooldown_until = (
            existing_suggestion.dismiss_cooldown_until if stays_dismissed and existing_suggestion else None
        )

        upsert_suggestion(
            session,
            project_id,
            subject_id,
            db_id,
            primary_db_id,
            fallback_db_ids,
            next_state.value,
            reason_codes,
            now,
            dismissed_at,
            cooldown_until,
        )
        if next_state in (SuggestionState.ACTIVE, SuggestionState.ELIGIBLE):
            log_event(
                "suggestion_eligible", project_id=project_id, subject_id=subject_id, family_key=family.family_id
            )

        summaries.append(FamilyAnalysisSummary(family.family_id, assessment.decision, next_state))

    return summaries


def analyze_subject(
    session: Session,
    project_config: ProjectConfig,
    project_id: str,
    subject_id: str,
    resolver: ResolverContract,
    now: datetime,
) -> AnalysisSummary:
    engine_config = project_config.engine
    log_event("analysis_started", project_id=project_id, subject_id=subject_id)

    new_series, db_id_by_event_id = _extract_new_series(session, project_id, subject_id, engine_config)
    log_event("series_extracted", project_id=project_id, subject_id=subject_id, count=len(new_series))

    existing = fetch_families(session, project_id, subject_id)
    family_by_key = {family.family_id: (db_id, family) for db_id, family in existing}

    member_series_cache: dict[int, list[OSeries]] = {}
    weighting_corpus: list[tuple] = []
    for db_id, _family in existing:
        members = fetch_member_series(session, db_id, engine_config.family.detour_max_length)
        member_series_cache[db_id] = members
        weighting_corpus.extend(s.symbols for s in members)
    weighting_corpus.extend(s.symbols for s in new_series)
    weights = compute_discriminative_weights(
        weighting_corpus, engine_config.family.min_series_for_weighting, engine_config.family.min_symbol_weight
    )

    _match_new_series_into_families(
        session,
        project_id,
        subject_id,
        now,
        engine_config,
        new_series,
        db_id_by_event_id,
        weights,
        family_by_key,
        member_series_cache,
    )

    family_selections = _evaluate_families(
        session, project_id, subject_id, now, engine_config, resolver, family_by_key, member_series_cache
    )
    summaries = _persist_lifecycle_decisions(session, project_id, subject_id, now, family_selections)

    return AnalysisSummary(
        project_id=project_id, subject_id=subject_id, new_series_count=len(new_series), families=summaries
    )


# =============================================================================
# FILE: src/awe/services/suggestions.py
# =============================================================================
"""Subject'e ait suggestion'ların dışa sunulacak görünümü ve dismiss akışı (bölüm 97)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.config.engine_config import LifecycleConfig
from awe.lifecycle import dismiss as dismiss_lifecycle  # motor paketi -- bu pakette yok
from awe.persistence.models import PlanCandidateRecord, SuggestionRecord
from awe.persistence.repository import (
    fetch_plan_candidate,
    fetch_suggestion_by_key,
    list_suggestions,
)

_VISIBLE_STATES = {"active", "stale", "eligible"}


@dataclass(frozen=True, slots=True)
class PlanView:
    plan_id: str
    plan_type: str
    """Kullanıcıya sunulacak fiili tip: Risk tarafından DOWNGRADE_TO_NAVIGATE kararı verilmiş
    bir PREFILL adayı burada 'navigate' olarak görünür ve binding'leri taşınmaz."""
    anchor_symbol: list[str]
    anchor_screen: str | None
    bindings: list[dict]
    target_binding: dict | None
    risk_decision: str
    benefit_median_saved_actions: float


@dataclass(frozen=True, slots=True)
class SuggestionView:
    suggestion_key: str
    project_id: str
    subject_id: str
    state: str
    reason_codes: list[str]
    primary_plan: PlanView
    fallback_plans: list[PlanView]
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


def _to_plan_view(record: PlanCandidateRecord) -> PlanView:
    effective_type = "navigate" if record.risk_decision == "downgrade_to_navigate" else record.plan_type
    bindings = record.bindings if effective_type == "prefill" else []
    return PlanView(
        plan_id=record.plan_key,
        plan_type=effective_type,
        anchor_symbol=record.anchor["symbol"],
        anchor_screen=record.anchor["screen"],
        bindings=bindings,
        target_binding=record.target_binding,
        risk_decision=record.risk_decision,
        benefit_median_saved_actions=record.benefit_median,
    )


def _to_suggestion_view(session: Session, record: SuggestionRecord) -> SuggestionView:
    primary = fetch_plan_candidate(session, record.primary_plan_id)
    assert primary is not None
    fallback_records = [fetch_plan_candidate(session, pid) for pid in record.fallback_plan_ids]
    return SuggestionView(
        suggestion_key=record.suggestion_key,
        project_id=record.project_id,
        subject_id=record.subject_id,
        state=record.state,
        reason_codes=record.reason_codes,
        primary_plan=_to_plan_view(primary),
        fallback_plans=[_to_plan_view(p) for p in fallback_records if p is not None],
        created_at=record.created_at,
        updated_at=record.updated_at,
        dismissed_at=record.dismissed_at,
    )


def list_subject_suggestions(session: Session, project_id: str, subject_id: str) -> list[SuggestionView]:
    records = list_suggestions(session, project_id, subject_id, states=_VISIBLE_STATES)
    return [_to_suggestion_view(session, record) for record in records]


def dismiss_suggestion(
    session: Session, project_id: str, subject_id: str, suggestion_key: str, now: datetime, config: LifecycleConfig
) -> SuggestionView | None:
    record = fetch_suggestion_by_key(session, suggestion_key)
    if record is None or record.project_id != project_id or record.subject_id != subject_id:
        return None

    state, cooldown_until = dismiss_lifecycle(now, config)
    record.state = state.value
    record.dismissed_at = now
    record.dismiss_cooldown_until = cooldown_until
    record.updated_at = now
    session.flush()
    return _to_suggestion_view(session, record)


# =============================================================================
# FILE: src/awe/api/__init__.py   (boş dosya)
# =============================================================================


# =============================================================================
# FILE: src/awe/api/main.py
# =============================================================================
"""FastAPI uygulama giriş noktası.

Çalıştırma: `uvicorn awe.api.main:app --reload` (önce `alembic upgrade head` gerekir).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from awe.api.routes_events import router as events_router
from awe.api.routes_suggestions import router as suggestions_router
from awe.config import ProjectRegistry, configure_logging, get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.project_registry = ProjectRegistry(settings.project_config_dir)
    yield


app = FastAPI(
    title="Adaptive Workflow Engine",
    description="Event log tabanlı habit-to-shortcut öneri motoru.",
    version="0.1.0",
    lifespan=_lifespan,
)
app.include_router(events_router)
app.include_router(suggestions_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


# =============================================================================
# FILE: src/awe/api/dependencies.py
# =============================================================================
"""FastAPI bağımlılık enjeksiyonu: veritabanı session'ı ve proje konfigürasyonu."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from awe.config import ProjectConfig, ProjectNotFoundError, ProjectRegistry, Settings, get_settings
from awe.persistence import create_database_engine, create_session_factory


@lru_cache
def _session_factory_for(database_url: str) -> sessionmaker[Session]:
    engine = create_database_engine(database_url)
    return create_session_factory(engine)


def get_db_session(request: Request) -> Iterator[Session]:
    settings: Settings = request.app.state.settings
    factory = _session_factory_for(settings.database_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_project_registry(request: Request) -> ProjectRegistry:
    return request.app.state.project_registry


def get_project_config(
    project_id: str, registry: ProjectRegistry = Depends(get_project_registry)
) -> ProjectConfig:
    try:
        return registry.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"unknown project_id '{project_id}'") from exc


__all__ = ["get_db_session", "get_project_registry", "get_project_config", "get_settings"]


# =============================================================================
# FILE: src/awe/api/schemas.py
# =============================================================================
"""API'nin dışarıya sunduğu Pydantic request/response modelleri.

Bu modeller `awe.domain` nesnelerini birebir yansıtmaz; yalnızca dışarıya sunulması gereken
alanları taşır (ör. dahili veritabanı id'leri değil, opak `plan_key`/`suggestion_key` string'leri).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EventIngestResponse(BaseModel):
    accepted: bool
    duplicate: bool
    event_id: str | None = None
    error: str | None = None


class BatchIngestResponse(BaseModel):
    results: list[EventIngestResponse]
    accepted_count: int
    duplicate_count: int
    rejected_count: int


class FamilyAnalysisResponse(BaseModel):
    family_key: str
    habit_decision: str
    suggestion_state: str | None


class AnalysisResponse(BaseModel):
    project_id: str
    subject_id: str
    new_series_count: int
    families: list[FamilyAnalysisResponse]


class FieldBindingResponse(BaseModel):
    field_name: str
    state: str
    dominant_value: str | None
    dominance: float
    coverage: float
    sample_size: int
    recent_dominance: float | None


class PlanResponse(BaseModel):
    plan_id: str
    plan_type: str
    anchor_symbol: list[str]
    anchor_screen: str | None
    bindings: list[dict]
    target_binding: dict | None
    risk_decision: str
    benefit_median_saved_actions: float


class SuggestionResponse(BaseModel):
    suggestion_key: str
    state: str
    reason_codes: list[str]
    primary_plan: PlanResponse
    fallback_plans: list[PlanResponse]
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


class ResolverCapabilities(BaseModel):
    """İstemcinin bu analiz isteği için beyan ettiği Resolver yeteneği (bölüm 78).

    Body'de gönderilmezse proje varsayılanı (tam destek) kullanılır.
    """

    supports_navigate: bool = True
    supports_prefill: bool = True
    accepted_bindings: list[str] | None = None
    requires_review: bool = False
    supports_runtime_validation: bool = False


class AnalyzeRequest(BaseModel):
    resolver: ResolverCapabilities = Field(default_factory=ResolverCapabilities)


# =============================================================================
# FILE: src/awe/api/routes_events.py
# =============================================================================
"""Event ingestion ve subject analiz endpoint'leri (bölüm 97)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    BatchIngestResponse,
    EventIngestResponse,
    FamilyAnalysisResponse,
)
from awe.config import ProjectConfig
from awe.risk import ResolverContract  # motor paketi -- bu pakette yok
from awe.services import IngestOutcome, analyze_subject, ingest_batch, ingest_event

router = APIRouter(prefix="/projects/{project_id}", tags=["events"])


def _ingest_response(outcome: IngestOutcome) -> EventIngestResponse:
    return EventIngestResponse(
        accepted=outcome.accepted, duplicate=outcome.duplicate, event_id=outcome.event_id, error=outcome.error
    )


@router.post("/events", response_model=EventIngestResponse)
def post_event(
    project_id: str,
    raw_event: dict,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> EventIngestResponse:
    outcome = ingest_event(session, project_config, project_id, raw_event, datetime.now(UTC))
    return _ingest_response(outcome)


@router.post("/events/batch", response_model=BatchIngestResponse)
def post_event_batch(
    project_id: str,
    raw_events: list[dict],
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> BatchIngestResponse:
    outcomes = ingest_batch(session, project_config, project_id, raw_events, datetime.now(UTC))
    return BatchIngestResponse(
        results=[_ingest_response(o) for o in outcomes],
        accepted_count=sum(1 for o in outcomes if o.accepted and not o.duplicate),
        duplicate_count=sum(1 for o in outcomes if o.duplicate),
        rejected_count=sum(1 for o in outcomes if not o.accepted),
    )


def _resolver_from_request(request: AnalyzeRequest) -> ResolverContract:
    capabilities = request.resolver
    accepted = frozenset(capabilities.accepted_bindings) if capabilities.accepted_bindings is not None else None
    return ResolverContract(
        supports_navigate=capabilities.supports_navigate,
        supports_prefill=capabilities.supports_prefill,
        accepted_bindings=accepted,
        requires_review=capabilities.requires_review,
        supports_runtime_validation=capabilities.supports_runtime_validation,
    )


@router.post("/subjects/{subject_id}/analyze", response_model=AnalysisResponse)
def post_analyze_subject(
    project_id: str,
    subject_id: str,
    request: AnalyzeRequest = AnalyzeRequest(),
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> AnalysisResponse:
    resolver = _resolver_from_request(request)
    summary = analyze_subject(session, project_config, project_id, subject_id, resolver, datetime.now(UTC))
    return AnalysisResponse(
        project_id=summary.project_id,
        subject_id=summary.subject_id,
        new_series_count=summary.new_series_count,
        families=[
            FamilyAnalysisResponse(
                family_key=f.family_key,
                habit_decision=f.habit_decision.value,
                suggestion_state=f.suggestion_state.value if f.suggestion_state else None,
            )
            for f in summary.families
        ],
    )


# =============================================================================
# FILE: src/awe/api/routes_suggestions.py
# =============================================================================
"""Suggestion listeleme ve dismiss endpoint'leri (bölüm 97)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import PlanResponse, SuggestionResponse
from awe.config import ProjectConfig
from awe.services import PlanView, SuggestionView, dismiss_suggestion, list_subject_suggestions

router = APIRouter(prefix="/projects/{project_id}/subjects/{subject_id}", tags=["suggestions"])


def _plan_response(plan: PlanView) -> PlanResponse:
    return PlanResponse(
        plan_id=plan.plan_id,
        plan_type=plan.plan_type,
        anchor_symbol=list(plan.anchor_symbol),
        anchor_screen=plan.anchor_screen,
        bindings=plan.bindings,
        target_binding=plan.target_binding,
        risk_decision=plan.risk_decision,
        benefit_median_saved_actions=plan.benefit_median_saved_actions,
    )


def _suggestion_response(view: SuggestionView) -> SuggestionResponse:
    return SuggestionResponse(
        suggestion_key=view.suggestion_key,
        state=view.state,
        reason_codes=view.reason_codes,
        primary_plan=_plan_response(view.primary_plan),
        fallback_plans=[_plan_response(p) for p in view.fallback_plans],
        created_at=view.created_at,
        updated_at=view.updated_at,
        dismissed_at=view.dismissed_at,
    )


@router.get("/suggestions", response_model=list[SuggestionResponse])
def get_suggestions(
    project_id: str,
    subject_id: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> list[SuggestionResponse]:
    views = list_subject_suggestions(session, project_id, subject_id)
    return [_suggestion_response(v) for v in views]


@router.post("/suggestions/{suggestion_key}/dismiss", response_model=SuggestionResponse)
def post_dismiss_suggestion(
    project_id: str,
    subject_id: str,
    suggestion_key: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> SuggestionResponse:
    view = dismiss_suggestion(
        session, project_id, subject_id, suggestion_key, datetime.now(UTC), project_config.engine.lifecycle
    )
    if view is None:
        raise HTTPException(status_code=404, detail=f"unknown suggestion_key '{suggestion_key}'")
    return _suggestion_response(view)


# =============================================================================
# FILE: src/awe/config/__init__.py
# =============================================================================
from awe.config.engine_config import (
    BenefitConfig,
    EngineConfig,
    FamilyConfig,
    HabitConfig,
    LifecycleConfig,
    PlannerConfig,
    RiskConfig,
    default_engine_config,
)
from awe.config.logging_config import configure_logging, log_event
from awe.config.project_config import ProjectConfig, ProjectNotFoundError, ProjectRegistry
from awe.config.settings import Settings, get_settings

__all__ = [
    "EngineConfig",
    "FamilyConfig",
    "HabitConfig",
    "PlannerConfig",
    "RiskConfig",
    "BenefitConfig",
    "LifecycleConfig",
    "default_engine_config",
    "configure_logging",
    "log_event",
    "ProjectConfig",
    "ProjectRegistry",
    "ProjectNotFoundError",
    "Settings",
    "get_settings",
]


# =============================================================================
# FILE: src/awe/config/settings.py
# =============================================================================
"""Süreç genelindeki ortam ayarları (veritabanı bağlantısı, log seviyesi vb.)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AWE_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./awe_dev.db"
    log_level: str = "INFO"
    project_config_dir: str = "./config_examples"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# =============================================================================
# FILE: src/awe/config/logging_config.py
# =============================================================================
"""Yapılandırılmış (structured) log kurulumu (bölüm 132).

Motor, her pipeline adımında `awe.engine` logger'ı üzerinden tek satırlık JSON olay kayıtları
üretir (`analysis_started`, `family_matched`, `risk_blocked` vb.). Hiçbir kayıt kullanıcı
parametre değeri (target ref, prefill değeri) içermez — yalnızca sayaçlar, kimlikler ve karar
sonuçları taşınır.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


_ENGINE_LOGGER = logging.getLogger("awe.engine")


def log_event(event: str, **fields: object) -> None:
    _ENGINE_LOGGER.info(event, extra={"awe_event": event, **fields})


# =============================================================================
# FILE: src/awe/config/engine_config.py
# =============================================================================
# NOT: Bu dosyanın ÇOĞU içeriği motor katmanlarının (Family/Habit/Planner/Risk/
# Benefit/Lifecycle) eşik/konfigürasyon şemasıdır. Algoritmaların KENDİSİ
# (families/, habit/, planner/, risk/, benefit/, lifecycle/ paketleri) burada
# değildir; bu yalnızca o algoritmaların okuduğu sayısal eşik tanımlarıdır.
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


# =============================================================================
# FILE: src/awe/config/project_config.py
# =============================================================================
"""Proje bazlı konfigürasyon: hangi Adapter mapping'i, hangi timezone, hangi eşik override'ları.

MVP kapsamında bölüm 97'nin API listesinde bir config-upload endpoint'i bulunmuyor; bu yüzden
proje konfigürasyonları `config_examples/` altında dosya tabanlı olarak tutulur ve
`ProjectRegistry` tarafından yüklenir (IMPLEMENTATION_PLAN.md bölüm 8). Gerçek bir çok-kiracılı
sistemde bu, `_build_mapping`/`_build_engine_overrides` değiştirilerek bir config-upload
API'sine bağlanabilir; bu genişletme noktası bilinçli bir MVP sınırlamasıdır.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig, default_engine_config


class ProjectNotFoundError(KeyError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectConfig:
    project_id: str
    display_name: str
    mapping: AdapterMapping
    engine: EngineConfig


def _build_field_rule(data: dict[str, Any] | None) -> FieldRule:
    data = data or {}
    return FieldRule(
        path=data.get("path"),
        value_map=data.get("value_map", {}),
        default=data.get("default", "unknown"),
    )


def _build_mapping(data: dict[str, Any]) -> AdapterMapping:
    target_data = data.get("target", {})
    return AdapterMapping(
        mapping_version=data["mapping_version"],
        event_id_path=data["event_id_path"],
        project_id_path=data["project_id_path"],
        subject_id_path=data["subject_id_path"],
        session_id_path=data["session_id_path"],
        timestamp_path=data["timestamp_path"],
        action_key_path=data["action_key_path"],
        action_key_value_map=data.get("action_key_value_map", {}),
        screen_path=data.get("screen_path"),
        widget_path=data.get("widget_path"),
        app_version_path=data.get("app_version_path"),
        duration_ms_path=data.get("duration_ms_path"),
        source=_build_field_rule(data.get("source")),
        role=_build_field_rule(data.get("role")),
        effect=_build_field_rule(data.get("effect")),
        trigger=_build_field_rule(data.get("trigger")),
        status=_build_field_rule(data.get("status")),
        target=TargetRule(ref_path=target_data.get("ref_path")),
        parameter_fields=data.get("parameter_fields", {}),
        breaks_episode_path=data.get("breaks_episode_path"),
        breaks_episode_action_keys=frozenset(data.get("breaks_episode_action_keys", [])),
        assume_timezone=data.get("assume_timezone", "UTC"),
    )


def _build_engine_overrides(data: dict[str, Any] | None, timezone: str) -> EngineConfig:
    base = default_engine_config()
    if not data:
        return dataclasses.replace(base, timezone=timezone)

    section_names = ("family", "habit", "planner", "risk", "benefit", "lifecycle")
    updated_sections: dict[str, Any] = {}
    for section_name in section_names:
        overrides = data.get(section_name)
        if overrides:
            current = getattr(base, section_name)
            updated_sections[section_name] = dataclasses.replace(current, **overrides)
    return dataclasses.replace(base, timezone=timezone, **updated_sections)


def load_project_config(path: Path) -> ProjectConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    timezone = data.get("timezone", "UTC")
    return ProjectConfig(
        project_id=data["project_id"],
        display_name=data.get("display_name", data["project_id"]),
        mapping=_build_mapping(data["mapping"]),
        engine=_build_engine_overrides(data.get("engine_overrides"), timezone),
    )


class ProjectRegistry:
    """`config_examples/` altındaki proje YAML dosyalarını yükler ve önbelleğe alır."""

    def __init__(self, config_dir: str | Path) -> None:
        self._config_dir = Path(config_dir)
        self._cache: dict[str, ProjectConfig] = {}

    def get(self, project_id: str) -> ProjectConfig:
        if project_id in self._cache:
            return self._cache[project_id]
        candidate = self._config_dir / f"{project_id}.yaml"
        if not candidate.exists():
            raise ProjectNotFoundError(project_id)
        config = load_project_config(candidate)
        if config.project_id != project_id:
            raise ValueError(
                f"config file '{candidate}' declares project_id '{config.project_id}', "
                f"expected '{project_id}'"
            )
        self._cache[project_id] = config
        return config

    def known_project_ids(self) -> list[str]:
        return sorted(p.stem for p in self._config_dir.glob("*.yaml"))


# =============================================================================
# FILE: src/awe/testing/__init__.py
# =============================================================================
from awe.testing.generators import (
    PROFILE_NAMES,
    GeneratedSubject,
    MultiHabitSubject,
    generate_multi_habit_subject,
    generate_subject,
)

__all__ = [
    "GeneratedSubject",
    "generate_subject",
    "PROFILE_NAMES",
    "MultiHabitSubject",
    "generate_multi_habit_subject",
]


# =============================================================================
# FILE: src/awe/testing/generators.py
# =============================================================================
"""Deterministik sentetik event log üretici (bölüm 125).

Her profil, gerçek bir kullanıcı davranış deseni için (günlük, haftalık, burst, gürültülü,
vb.) ground-truth bir Habit beklentisiyle birlikte ham event üretir. Üretilen event'ler,
`config_examples/` altındaki proje konfigürasyonlarının paylaştığı canonical-benzeri mapping
şekliyle (eventId/projectId/subjectId/... alan adları) uyumludur; bu yüzden aynı üretici tüm
domain projelerinde kullanılabilir.

Bu modül yalnızca test/evaluation amaçlıdır; üretim koduna (adapter, engine) bağımlılığı yoktur.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from awe.domain.enums import HabitDecision

_STANDARD_FLOW: list[tuple[str, str]] = [
    ("open_dashboard", "route"),
    ("open_detail", "route"),
    ("select_option", "select"),
    ("confirm_action", "confirm"),
]
_SHORT_FLOW: list[tuple[str, str]] = [("quick_open", "route"), ("quick_action", "select")]
_LONG_FLOW: list[tuple[str, str]] = [
    ("open_dashboard", "route"),
    ("open_category", "route"),
    ("open_item", "route"),
    ("fill_field_a", "input"),
    ("fill_field_b", "input"),
    ("review_summary", "select"),
    ("confirm_action", "confirm"),
]


def _raw_event(
    project_id: str,
    subject_id: str,
    session_id: str,
    event_id: str,
    timestamp: datetime,
    action_key: str,
    effect: str,
    *,
    role: str = "action",
    trigger: str = "button",
    screen: str = "app",
    widget: str | None = None,
    target: dict | None = None,
    status: str = "success",
    breaks_episode: bool = False,
) -> dict:
    return {
        "eventId": event_id,
        "projectId": project_id,
        "subjectId": subject_id,
        "sessionId": session_id,
        "timestamp": timestamp.isoformat(),
        "source": "client",
        "actionKey": action_key,
        "role": role,
        "effect": effect,
        "trigger": trigger,
        "screen": screen,
        "widget": widget,
        "target": target,
        "status": status,
        "breaksEpisode": breaks_episode,
        "metadata": {},
    }


@dataclass(frozen=True, slots=True)
class _OccurrenceSpec:
    day: int
    minute_offset: int
    session_index: int
    widget_suffix: str = "v1"
    target_ref: str | None = "item_1"
    add_noise: bool = False
    add_detour: bool = False
    add_retry: bool = False
    final_status: str = "success"
    session_prefix: str = ""
    """Aynı subject için birden fazla bağımsız Habit üretilirken (bkz.
    `generate_multi_habit_subject`), farklı bileşenlerin aynı gün/session_index kombinasyonuna
    düşüp aynı session_id'yi paylaşmasını (ve böylece olay akışlarının birbirine karışmasını)
    önlemek için kullanılır."""


def _emit_occurrence(
    project_id: str,
    subject_id: str,
    occurrence_index: int,
    base_time: datetime,
    flow: list[tuple[str, str]],
    spec: _OccurrenceSpec,
) -> list[dict]:
    session_id = f"sess-{subject_id}-{spec.session_prefix}{spec.day}-{spec.session_index}"
    events: list[dict] = []
    step = 0

    def emit(action_key: str, effect: str, **kwargs) -> None:
        nonlocal step
        event_id = f"evt-{subject_id}-{occurrence_index}-{step}"
        ts = base_time + timedelta(days=spec.day, minutes=spec.minute_offset + step)
        events.append(
            _raw_event(project_id, subject_id, session_id, event_id, ts, action_key, effect, **kwargs)
        )
        step += 1

    if spec.add_noise:
        # Uygulama yaşam-döngüsü sinyali: trigger=lifecycle + effect=update, ACTION/CONTEXT/
        # IGNORE sınıflandırmasında (bkz. awe.adapter.classification) hiçbir gruba girmediği
        # için IGNORE sayılır -- temiz action akışına hiç girmez.
        emit("app_foreground", "update", role="noise", trigger="lifecycle")

    last_index = len(flow) - 1
    for index, (action_key, effect) in enumerate(flow):
        if spec.add_detour and index == 1:
            emit("wrong_screen", "route")
            emit("back_button", "navigate_back")

        if spec.add_retry and index == last_index:
            emit(action_key, effect, status="fail")
            emit(action_key, effect, status="fail")

        widget = f"{action_key}_{spec.widget_suffix}"
        target = {"ref": spec.target_ref} if (spec.target_ref and effect == "select") else None
        status = spec.final_status if index == last_index else "success"
        emit(action_key, effect, widget=widget, target=target, status=status)

    return events


@dataclass(frozen=True, slots=True)
class GeneratedSubject:
    project_id: str
    subject_id: str
    profile: str
    events: list[dict]
    expected_habit_decision: HabitDecision
    notes: str = ""


def _day_list(profile: str, rng: random.Random) -> list[_OccurrenceSpec]:
    if profile == "daily_regular":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(30)]
    if profile == "daily_missing_days":
        days = sorted(set(range(30)) - set(rng.sample(range(30), 8)))
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in days]
    if profile == "daily_high_frequency":
        specs = []
        for day in range(20):
            for session in range(rng.randint(5, 10)):
                specs.append(_OccurrenceSpec(day=day, minute_offset=session * 15, session_index=session))
        return specs
    if profile == "weekly_regular":
        return [_OccurrenceSpec(day=w * 7, minute_offset=0, session_index=0) for w in range(8)]
    if profile == "biweekly_regular":
        return [_OccurrenceSpec(day=i * 14, minute_offset=0, session_index=0) for i in range(9)]
    if profile == "monthly_regular":
        return [_OccurrenceSpec(day=i * 30, minute_offset=0, session_index=0) for i in range(7)]
    if profile == "irregular_recurring":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in (1, 4, 11, 18, 29, 43, 55)]
    if profile == "short_frequent":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(30)]
    if profile == "long_workflow":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(0, 30, 2)]
    if profile == "one_day_burst":
        return [_OccurrenceSpec(day=5, minute_offset=s * 5, session_index=s) for s in range(35)]
    if profile == "two_day_burst":
        return [_OccurrenceSpec(day=5, minute_offset=s * 5, session_index=s) for s in range(15)] + [
            _OccurrenceSpec(day=6, minute_offset=s * 5, session_index=s) for s in range(15)
        ]
    if profile == "single_session_repeater":
        # `_STANDARD_FLOW` 4 adımlıdır; ardışık occurrence'ların adımları arasında çakışma
        # olmaması için aralık adım sayısından büyük tutulur (aksi halde iki occurrence aynı
        # dakikaya düşüp order_session'da gerçek ama gereksiz bir zaman belirsizliği yaratır).
        return [_OccurrenceSpec(day=0, minute_offset=i * 6, session_index=0) for i in range(50)]
    if profile == "stale":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(30)]
    if profile == "revived":
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(5)] + [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0) for d in range(95, 101)
        ]
    if profile == "noisy":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_noise=True) for d in range(20)
        ]
    if profile == "misclick_heavy":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_detour=(d % 2 == 0))
            for d in range(20)
        ]
    if profile == "retry_heavy":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_retry=(d % 2 == 0))
            for d in range(20)
        ]
    if profile == "widget_rename":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, widget_suffix="v1" if d < 10 else "v2")
            for d in range(20)
        ]
    if profile == "target_variable":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, target_ref=f"item_{d % 7}")
            for d in range(20)
        ]
    if profile == "parameter_drift":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, target_ref="item_1" if d < 15 else "item_9")
            for d in range(20)
        ]
    raise ValueError(f"unknown profile: {profile}")


_EXPECTED_DECISION: dict[str, HabitDecision] = {
    "daily_regular": HabitDecision.PASS,
    "daily_missing_days": HabitDecision.PASS,
    "daily_high_frequency": HabitDecision.PASS,
    "weekly_regular": HabitDecision.PASS,
    "biweekly_regular": HabitDecision.PASS,
    "monthly_regular": HabitDecision.PASS,
    "irregular_recurring": HabitDecision.PASS,
    "short_frequent": HabitDecision.PASS,
    "long_workflow": HabitDecision.PASS,
    "one_day_burst": HabitDecision.NOT_HABIT,
    "two_day_burst": HabitDecision.NOT_HABIT,
    "single_session_repeater": HabitDecision.NOT_HABIT,
    "stale": HabitDecision.PASS,
    "revived": HabitDecision.PASS,
    "noisy": HabitDecision.PASS,
    "misclick_heavy": HabitDecision.PASS,
    "retry_heavy": HabitDecision.PASS,
    "widget_rename": HabitDecision.PASS,
    "target_variable": HabitDecision.PASS,
    "parameter_drift": HabitDecision.PASS,
}

_FLOW_BY_PROFILE: dict[str, list[tuple[str, str]]] = {
    "short_frequent": _SHORT_FLOW,
    "long_workflow": _LONG_FLOW,
}

PROFILE_NAMES: tuple[str, ...] = tuple(_EXPECTED_DECISION.keys())


def generate_subject(
    profile: str,
    project_id: str,
    subject_id: str,
    seed: int,
    base_time: datetime,
) -> GeneratedSubject:
    rng = random.Random(seed)
    flow = _FLOW_BY_PROFILE.get(profile, _STANDARD_FLOW)
    specs = _day_list(profile, rng)

    events: list[dict] = []
    for occurrence_index, spec in enumerate(specs):
        events.extend(_emit_occurrence(project_id, subject_id, occurrence_index, base_time, flow, spec))

    return GeneratedSubject(
        project_id=project_id,
        subject_id=subject_id,
        profile=profile,
        events=events,
        expected_habit_decision=_EXPECTED_DECISION[profile],
    )


@dataclass(frozen=True, slots=True)
class MultiHabitSubject:
    project_id: str
    subject_id: str
    events: list[dict] = field(default_factory=list)
    component_profiles: tuple[str, ...] = ()


def generate_multi_habit_subject(
    project_id: str, subject_id: str, seed: int, base_time: datetime
) -> MultiHabitSubject:
    """Aynı kullanıcı için birbirinden bağımsız birden fazla Habit (bölüm 113)."""

    component_profiles = ("daily_regular", "weekly_regular", "monthly_regular", "irregular_recurring")
    flows = [
        [("open_a", "route"), ("open_a_detail", "route"), ("confirm_a", "confirm")],
        [("open_b", "route"), ("open_b_detail", "route"), ("confirm_b", "confirm")],
        [("open_c", "route"), ("open_c_detail", "route"), ("confirm_c", "confirm")],
        [("open_d", "route"), ("open_d_detail", "route"), ("confirm_d", "confirm")],
    ]

    rng = random.Random(seed)
    events: list[dict] = []
    for component_index, (profile, flow) in enumerate(zip(component_profiles, flows, strict=True)):
        specs = _day_list(profile, rng)
        for occurrence_index, spec in enumerate(specs):
            prefixed_spec = replace(spec, session_prefix=f"c{component_index}-")
            events.extend(
                _emit_occurrence(
                    project_id,
                    subject_id,
                    component_index * 1000 + occurrence_index,
                    base_time,
                    flow,
                    prefixed_spec,
                )
            )

    return MultiHabitSubject(
        project_id=project_id, subject_id=subject_id, events=events, component_profiles=component_profiles
    )

# =============================================================================
# ============================ MOTOR KATMANLARI ==============================
# Aşağıdaki paketler (families, habit, planner, risk, benefit, selection,
# lifecycle) gerçek davranış-analizi algoritmalarını içerir.
# =============================================================================


# =============================================================================
# FILE: src/awe/families/__init__.py
# =============================================================================
from awe.families.matching import (
    accept_series,
    compute_cohesion,
    compute_relationships,
    match_series,
    seed_family,
)
from awe.families.similarity import order_preserving_coverage, weighted_similarity
from awe.families.weighting import compute_discriminative_weights

__all__ = [
    "match_series",
    "accept_series",
    "seed_family",
    "compute_relationships",
    "compute_cohesion",
    "weighted_similarity",
    "order_preserving_coverage",
    "compute_discriminative_weights",
]


# =============================================================================
# FILE: src/awe/families/similarity.py
# =============================================================================
"""Sembol dizileri arası ayrıştırıcı-ağırlıklı benzerlik ve core-kapsama hesapları."""

from __future__ import annotations

from awe.domain.tokens import Symbol
from awe.families.weighting import weight_of


def weighted_similarity(
    left: tuple[Symbol, ...], right: tuple[Symbol, ...], weights: dict[Symbol, float]
) -> float:
    """Ağırlıklı LCS üzerinden Dice benzerlik katsayısı (0-1 arası, simetrik).

    LCS, dizide bulunmayan araya girmiş semboller (opsiyonel adım/detour artığı) varlığında
    dahi ortak yapıyı bulur — bitişiklik gerektirmez. Bu, bölüm 53'teki opsiyonel prefix/
    suffix/middle örneklerinin family kimliğini bozmamasını sağlar.
    """

    if not left or not right:
        return 0.0

    n, m = len(left), len(right)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if left[i - 1] == right[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + weight_of(left[i - 1], weights)
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    weighted_lcs = dp[n][m]
    left_weight = sum(weight_of(s, weights) for s in left)
    right_weight = sum(weight_of(s, weights) for s in right)
    total = left_weight + right_weight
    if total <= 0:
        return 0.0
    return (2 * weighted_lcs) / total


def order_preserving_coverage(symbols: tuple[Symbol, ...], pairs: set[tuple[Symbol, Symbol]]) -> float:
    """Verilen (predecessor, successor) çiftlerinin kaçının `symbols` içinde SIRAYLA (bitişik
    olması şart değil) göründüğünü ölçer. Opsiyonel ara adımlar bu kontrolü bozmaz."""

    if not pairs:
        return 1.0

    positions: dict[Symbol, list[int]] = {}
    for idx, symbol in enumerate(symbols):
        positions.setdefault(symbol, []).append(idx)

    covered = 0
    for predecessor, successor in pairs:
        pred_positions = positions.get(predecessor)
        succ_positions = positions.get(successor)
        if not pred_positions or not succ_positions:
            continue
        if pred_positions[0] < succ_positions[-1]:
            covered += 1

    return covered / len(pairs)


# =============================================================================
# FILE: src/awe/families/weighting.py
# =============================================================================
"""Ayrıştırıcı (discriminative) sembol ağırlıklandırması (bölüm 49).

Bir sembol subject'in neredeyse bütün O-Series'lerinde görülüyorsa (ör. ortak bir başlangıç
ekranı, bölüm 20/115), Family benzerlik skorunu şişirmemesi için düşük ağırlık alır. Ham IDF,
az sayıda O-Series'i olan subject'lerde anlamsız uç değerler ürettiğinden add-one smoothing
uygulanır ve örneklem `min_series_for_weighting` altındaysa uniform ağırlığa düşülür
(IMPLEMENTATION_PLAN.md 2.6).

Ağırlık asla tam sıfıra inmez (`min_weight` alt sınırı korunur). Bunun nedeni: bir subject'in
gözlenen davranışının tamamı TEK bir Habit'e aitse (yaygın durum), o Habit'in kendi çekirdek
sembolleri de "hemen her yerde görülüyor" sayılır ve ham IDF onları sıfıra çeker — bu ise nadir
görülen tek seferlik bir sapmayı (bkz. bir detour) yapay biçimde asıl çekirdekten daha
"ayırt edici" gösterip benzerlik skorunu bozar. Alt sınır bu tersine dönmeyi önler.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from awe.domain.tokens import Symbol

UNIFORM_WEIGHT = 1.0
DEFAULT_MIN_WEIGHT = 0.15


def compute_discriminative_weights(
    series_symbol_sequences: Iterable[tuple[Symbol, ...]],
    min_series_for_weighting: int,
    min_weight: float = DEFAULT_MIN_WEIGHT,
) -> dict[Symbol, float]:
    sequences = list(series_symbol_sequences)
    total_series = len(sequences)

    all_symbols: set[Symbol] = set()
    document_frequency: dict[Symbol, int] = {}
    for symbols in sequences:
        for symbol in set(symbols):
            all_symbols.add(symbol)
            document_frequency[symbol] = document_frequency.get(symbol, 0) + 1

    if total_series < min_series_for_weighting or not all_symbols:
        return {symbol: UNIFORM_WEIGHT for symbol in all_symbols}

    raw_weights = {
        symbol: -math.log((df + 1) / (total_series + 1))
        for symbol, df in document_frequency.items()
    }
    max_weight = max(raw_weights.values()) if raw_weights else 1.0
    if max_weight <= 0:
        return {symbol: UNIFORM_WEIGHT for symbol in all_symbols}
    return {symbol: max(min_weight, weight / max_weight) for symbol, weight in raw_weights.items()}


def weight_of(symbol: Symbol, weights: dict[Symbol, float]) -> float:
    return weights.get(symbol, UNIFORM_WEIGHT)


# =============================================================================
# FILE: src/awe/families/matching.py
# =============================================================================
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


# =============================================================================
# FILE: src/awe/habit/__init__.py
# =============================================================================
from awe.habit.assessment import evaluate_habit
from awe.habit.evidence import build_habit_evidence

__all__ = ["evaluate_habit", "build_habit_evidence"]


# =============================================================================
# FILE: src/awe/habit/evidence.py
# =============================================================================
"""Habit kanıtının ham O-Series üyelerinden hesaplanması (bölüm 63-67)."""

from __future__ import annotations

import statistics
from datetime import date, datetime
from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import LivenessState
from awe.domain.habit import HabitEvidence
from awe.domain.series import OSeries


def _local_date(moment: datetime, tz: ZoneInfo) -> date:
    return moment.astimezone(tz).date()


def _median_gap_days(sorted_dates: list[date]) -> float | None:
    if len(sorted_dates) < 3:
        return None
    gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
    return float(statistics.median(gaps))


def _regularity(sorted_dates: list[date], min_days: int) -> float | None:
    if len(sorted_dates) < min_days:
        return None
    gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
    mean_gap = statistics.mean(gaps)
    if mean_gap <= 0:
        return None
    coefficient_of_variation = statistics.pstdev(gaps) / mean_gap
    return 1.0 / (1.0 + coefficient_of_variation)


def _liveness(
    last_seen_at: datetime,
    now: datetime,
    median_gap_days: float | None,
    active_span_days: int,
    distinct_days: int,
    config: HabitConfig,
) -> tuple[float | None, LivenessState]:
    if median_gap_days is not None and median_gap_days > 0:
        expected_gap = median_gap_days
    elif distinct_days >= 2:
        expected_gap = active_span_days / max(distinct_days - 1, 1)
    else:
        expected_gap = None

    if expected_gap is None or expected_gap <= 0:
        return None, LivenessState.LIVE

    days_since_last = (now - last_seen_at).total_seconds() / 86400
    ratio = days_since_last / expected_gap
    if ratio <= config.liveness_watch_multiplier:
        state = LivenessState.LIVE
    elif ratio <= config.liveness_stale_multiplier:
        state = LivenessState.WATCH
    else:
        state = LivenessState.STALE
    return ratio, state


def _habit_strength(support_score: float, regularity: float | None, liveness: LivenessState) -> float:
    liveness_factor = {LivenessState.LIVE: 1.0, LivenessState.WATCH: 0.6, LivenessState.STALE: 0.3}[
        liveness
    ]
    regularity_component = regularity if regularity is not None else 0.5
    return round(support_score * 0.5 + regularity_component * 0.25 + liveness_factor * 0.25, 4)


def build_habit_evidence(
    organic_series: list[OSeries],
    shortcut_series_count: int,
    now: datetime,
    timezone_name: str,
    config: HabitConfig,
) -> HabitEvidence:
    tz = ZoneInfo(timezone_name)
    organic_count = len(organic_series)

    dates = [_local_date(s.started_at, tz) for s in organic_series]
    distinct_days_sorted = sorted(set(dates))
    distinct_days = len(distinct_days_sorted)
    distinct_sessions = len({s.session_id for s in organic_series})

    first_seen_at = min(s.started_at for s in organic_series)
    last_seen_at = max(s.started_at for s in organic_series)
    active_span_days = (distinct_days_sorted[-1] - distinct_days_sorted[0]).days + 1

    day_counts: dict[date, int] = {}
    for d in dates:
        day_counts[d] = day_counts.get(d, 0) + 1
    top_day_share = max(day_counts.values()) / organic_count

    session_counts: dict[str, int] = {}
    for s in organic_series:
        session_counts[s.session_id] = session_counts.get(s.session_id, 0) + 1
    top_session_share = max(session_counts.values()) / organic_count

    median_gap_days = _median_gap_days(distinct_days_sorted)
    regularity = _regularity(distinct_days_sorted, config.min_days_for_regularity)
    staleness_ratio, liveness = _liveness(
        last_seen_at, now, median_gap_days, active_span_days, distinct_days, config
    )

    support_score = organic_count / (organic_count + config.support_saturation_k)
    habit_strength = _habit_strength(support_score, regularity, liveness)

    return HabitEvidence(
        organic_occurrences=organic_count,
        distinct_sessions=distinct_sessions,
        distinct_days=distinct_days,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        active_span_days=active_span_days,
        top_day_share=top_day_share,
        top_session_share=top_session_share,
        median_gap_days=median_gap_days,
        regularity=regularity,
        staleness_ratio=staleness_ratio,
        liveness=liveness,
        shortcut_utility_occurrences=shortcut_series_count,
        support_score=support_score,
        habit_strength=habit_strength,
    )


# =============================================================================
# FILE: src/awe/habit/assessment.py
# =============================================================================
"""Habit hard-evidence gate'leri ve nihai karar (bölüm 61-62, IMPLEMENTATION_PLAN.md 2.2).

Gate'ler yalnızca gün/session/occurrence SAYIMINA dayanır — herhangi bir oran formülüne değil.
Bu yüzden "günde 5-10 kullanım" gibi yoğun ama gerçek Habit'ler cezalandırılmaz, buna karşın
one-day/two-day burst ve single-session repeater güvenilir biçimde reddedilir.

Bir gate'in kendi boyutu (gün ya da session sayısı) yetersizken toplam occurrence sayısı zaten
`min_occurrences` eşiğini geçmişse, bu "zamanla düzelecek eksik kanıt" değil, "davranış zaten
yoğun biçimde denendi ama yalnızca bir/iki günde/session'da yoğunlaştı" anlamına gelir — yani
NOT_HABIT olarak değerlendirilir. Occurrence sayısı da eşiğin altındaysa aile henüz genç demektir
ve PENDING_EVIDENCE ile bırakılır.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import HabitDecision, ReasonCode
from awe.domain.habit import HabitAssessment
from awe.domain.series import OSeries
from awe.habit.evidence import build_habit_evidence


def _gate_status(dimension_count: int, min_dimension: int, organic_count: int, min_occurrences: int) -> str:
    if dimension_count >= min_dimension:
        return "ok"
    if organic_count >= min_occurrences:
        return "burst_like"
    return "insufficient"


def evaluate_habit(
    family_id: str,
    member_series: list[OSeries],
    now: datetime,
    timezone_name: str,
    config: HabitConfig,
) -> HabitAssessment:
    organic_series = [s for s in member_series if not s.has_shortcut_trigger]
    shortcut_count = len(member_series) - len(organic_series)
    organic_count = len(organic_series)

    if organic_count == 0:
        return HabitAssessment(
            family_id=family_id,
            decision=HabitDecision.PENDING_EVIDENCE,
            evidence=None,
            reason_codes=(ReasonCode.INSUFFICIENT_OCCURRENCES,),
        )

    tz = ZoneInfo(timezone_name)
    distinct_sessions = len({s.session_id for s in organic_series})
    distinct_days = len({s.started_at.astimezone(tz).date() for s in organic_series})

    session_status = _gate_status(
        distinct_sessions, config.min_distinct_sessions, organic_count, config.min_occurrences
    )
    day_status = _gate_status(
        distinct_days, config.min_distinct_days, organic_count, config.min_occurrences
    )

    reason_codes: list[ReasonCode] = []
    if organic_count < config.min_occurrences:
        reason_codes.append(ReasonCode.INSUFFICIENT_OCCURRENCES)
    if session_status != "ok":
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS)
    if day_status != "ok":
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_DAYS)
        if distinct_days <= 2:
            reason_codes.append(ReasonCode.ONE_DAY_BURST)

    if reason_codes:
        decision = (
            HabitDecision.NOT_HABIT
            if "burst_like" in (session_status, day_status)
            else HabitDecision.PENDING_EVIDENCE
        )
        return HabitAssessment(
            family_id=family_id, decision=decision, evidence=None, reason_codes=tuple(reason_codes)
        )

    evidence = build_habit_evidence(organic_series, shortcut_count, now, timezone_name, config)
    stale_reason = (ReasonCode.STALE_BEHAVIOR,) if evidence.liveness.value == "stale" else ()
    return HabitAssessment(
        family_id=family_id, decision=HabitDecision.PASS, evidence=evidence, reason_codes=stale_reason
    )


# =============================================================================
# FILE: src/awe/planner/__init__.py
# =============================================================================
from awe.planner.candidates import build_plan_candidates
from awe.planner.state_reconstruction import compute_field_bindings, extract_state_before_anchor

__all__ = ["build_plan_candidates", "compute_field_bindings", "extract_state_before_anchor"]


# =============================================================================
# FILE: src/awe/planner/state_reconstruction.py
# =============================================================================
"""Anchor öncesi canonical state çıkarımı ve field binding istatistikleri (bölüm 73-77).

PREFILL, gözlenen eventleri yeniden oynatmaz (bölüm 73): burada üretilen değer yalnızca
"kullanıcı bu noktaya kadar tipik olarak hangi state'i kurmuş" sorusuna verilen istatistiksel
bir cevaptır; hiçbir eylem otomatik tetiklenmez.
"""

from __future__ import annotations

from collections import Counter

from awe.config.engine_config import PlannerConfig
from awe.domain.enums import FieldState
from awe.domain.plan import FieldBinding
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol

TARGET_FIELD_NAME = "target"
_NO_TARGET_SENTINEL = "__no_target__"


def resolve_anchor_step_index(series: OSeries, anchor_symbol: Symbol) -> int | None:
    """Anchor'ı index'e değil, sembol eşleşmesine göre çözer (bölüm 71).

    Sembol birden fazla kez görülüyorsa (loop), ilk görülme noktası "bu yapısal adıma ilk
    ulaşım" anını temsil eder ve state reconstruction için referans alınır.
    """

    for index, step in enumerate(series.normalized_steps):
        if step.symbol == anchor_symbol:
            return index
    return None


def extract_state_before_anchor(series: OSeries, anchor_symbol: Symbol) -> dict[str, str] | None:
    anchor_index = resolve_anchor_step_index(series, anchor_symbol)
    if anchor_index is None:
        return None

    state: dict[str, str] = {}
    for step in series.normalized_steps[: anchor_index + 1]:
        observation = series.raw_observations[step.observation_index]
        if observation.target:
            state[TARGET_FIELD_NAME] = observation.target
        elif observation.target == "":
            # Mapping target'ı izliyor ama bu event'in açıkça hedefi yok (ör. "logout") —
            # `None` (mapping hiç izlemiyor/bilinmiyor) durumundan ayırt edilir (bkz.
            # `Observation.target` docstring'i).
            state[TARGET_FIELD_NAME] = _NO_TARGET_SENTINEL
        for key, value in observation.parameters.items():
            state[key] = value
    return state


def compute_field_bindings(
    member_series: list[OSeries], anchor_symbol: Symbol, config: PlannerConfig
) -> tuple[FieldBinding, ...]:
    observed_states = []
    for series in member_series:
        state = extract_state_before_anchor(series, anchor_symbol)
        if state is not None:
            observed_states.append((series, state))

    total_reaching_anchor = len(observed_states)
    if total_reaching_anchor == 0:
        return ()

    field_names: set[str] = set()
    for _, state in observed_states:
        field_names.update(state.keys())

    recent_window = sorted(observed_states, key=lambda item: item[0].started_at, reverse=True)[
        : config.recent_window_size
    ]

    bindings = []
    for field_name in sorted(field_names):
        values = [state[field_name] for _, state in observed_states if field_name in state]
        sample_size = len(values)
        coverage = sample_size / total_reaching_anchor

        counts = Counter(values)
        dominant_value, dominant_count = counts.most_common(1)[0]
        dominance = dominant_count / sample_size

        recent_values = [state[field_name] for _, state in recent_window if field_name in state]
        recent_dominance = None
        if len(recent_values) >= config.min_binding_sample_size:
            recent_counts = Counter(recent_values)
            recent_dominance = recent_counts.most_common(1)[0][1] / len(recent_values)

        if coverage < config.min_coverage_for_known_state or sample_size < config.min_binding_sample_size:
            field_state = FieldState.UNKNOWN
        elif dominance >= config.stable_dominance_threshold:
            field_state = FieldState.STABLE
        else:
            field_state = FieldState.VARIABLE

        bindings.append(
            FieldBinding(
                field_name=field_name,
                state=field_state,
                dominant_value=None if dominant_value == _NO_TARGET_SENTINEL else dominant_value,
                dominance=dominance,
                coverage=coverage,
                sample_size=sample_size,
                recent_dominance=recent_dominance,
            )
        )
    return tuple(bindings)


# =============================================================================
# FILE: src/awe/planner/anchors.py
# =============================================================================
"""Family core sırasından NAVIGATE/PREFILL adayları için yapısal anchor seçimi.

`destination` kavramı yoktur (bölüm 70); anchor yalnızca family core'undaki bir sembol
referansıdır. Bir anchor, canonical `effect` politikası BLOCKED olan bir sembolde asla
oluşturulmaz — bu, Risk katmanından önce Planner seviyesinde uygulanan yapısal bir güvenlik
kısıtıdır (bölüm 80); Risk katmanı ayrıca kendi kanıt tabanlı kararını bağımsız olarak verir.
"""

from __future__ import annotations

from collections import Counter

from awe.config.engine_config import RiskConfig
from awe.domain.enums import EffectPolicy, ObservationEffect
from awe.domain.family import BehaviorFamily
from awe.domain.plan import ShortcutAnchor
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol

_NAVIGATE_EFFECTS = (ObservationEffect.ROUTE, ObservationEffect.OPEN_MODAL)
_PREFILL_EFFECTS = (
    ObservationEffect.INPUT,
    ObservationEffect.SELECT,
    ObservationEffect.PREPARE,
    ObservationEffect.UPDATE,
)
_TERMINAL_EFFECTS = (ObservationEffect.SUBMIT, ObservationEffect.CONFIRM)


def _effect_of(symbol: Symbol) -> ObservationEffect:
    return ObservationEffect(symbol[1])


def _is_anchorable(symbol: Symbol, effect_policy: dict[ObservationEffect, EffectPolicy]) -> bool:
    effect = _effect_of(symbol)
    if effect in _TERMINAL_EFFECTS:
        return False
    return effect_policy.get(effect, EffectPolicy.REVIEW) != EffectPolicy.BLOCKED


def _representative_screen(core: list[Symbol], position: int, member_series: list[OSeries]) -> str | None:
    symbol = core[position]
    screens = [
        step.screen
        for series in member_series
        for step in series.normalized_steps
        if step.symbol == symbol and step.screen is not None
    ]
    if not screens:
        return None
    return Counter(screens).most_common(1)[0][0]


def _build_anchor(core: list[Symbol], position: int, member_series: list[OSeries]) -> ShortcutAnchor:
    return ShortcutAnchor(
        symbol=core[position],
        screen=_representative_screen(core, position, member_series),
        core_position=position,
    )


def select_navigate_anchors(
    family: BehaviorFamily, member_series: list[OSeries], risk_config: RiskConfig
) -> list[ShortcutAnchor]:
    core = family.core_symbols_in_order
    positions = [
        i
        for i, symbol in enumerate(core)
        if _effect_of(symbol) in _NAVIGATE_EFFECTS and _is_anchorable(symbol, risk_config.effect_policy)
    ]
    if not positions:
        return []
    selected = {positions[0], positions[-1]}
    return [_build_anchor(core, position, member_series) for position in sorted(selected)]


def select_prefill_anchors(
    family: BehaviorFamily, member_series: list[OSeries], risk_config: RiskConfig
) -> list[ShortcutAnchor]:
    core = family.core_symbols_in_order
    anchorable = [i for i, symbol in enumerate(core) if _is_anchorable(symbol, risk_config.effect_policy)]
    if not anchorable:
        return []

    positions = {i for i in anchorable if _effect_of(core[i]) in _PREFILL_EFFECTS}
    positions.add(max(anchorable))
    return [_build_anchor(core, position, member_series) for position in sorted(positions)]


# =============================================================================
# FILE: src/awe/planner/candidates.py
# =============================================================================
"""Shortcut Planner: Habit'ten NAVIGATE/PREFILL PlanCandidate üretimi (bölüm 69-72).

Bu katman Risk veya Benefit kararı vermez; yalnızca güvenli biçimde önerilebilecek yapısal
adayları üretir. Bir Family, biri erken biri derin olmak üzere birden fazla NAVIGATE adayı ve
kısmi/derin birden fazla PREFILL adayı üretebilir — erken tek bir kazanan seçilmez (bölüm 72).
"""

from __future__ import annotations

from awe.config.engine_config import PlannerConfig, RiskConfig
from awe.domain.enums import PlanType
from awe.domain.family import BehaviorFamily
from awe.domain.plan import PlanCandidate, ShortcutAnchor
from awe.domain.series import OSeries
from awe.planner.anchors import select_navigate_anchors, select_prefill_anchors
from awe.planner.state_reconstruction import (
    TARGET_FIELD_NAME,
    compute_field_bindings,
    resolve_anchor_step_index,
)


def _plan_id(family_id: str, plan_type: PlanType, anchor: ShortcutAnchor) -> str:
    return f"{family_id}:{plan_type.value}:{anchor.core_position}"


def _build_candidate(
    family_id: str,
    plan_type: PlanType,
    anchor: ShortcutAnchor,
    member_series: list[OSeries],
    planner_config: PlannerConfig,
    include_parameter_bindings: bool,
) -> PlanCandidate | None:
    supporting_occurrences = sum(
        1 for series in member_series if resolve_anchor_step_index(series, anchor.symbol) is not None
    )
    if supporting_occurrences == 0:
        return None

    all_bindings = compute_field_bindings(member_series, anchor.symbol, planner_config)
    if include_parameter_bindings and not all_bindings:
        # PREFILL'in prefill edecek hiçbir alanı yoksa NAVIGATE'ten farksız, zayıf bir
        # kopya üretmek yerine bu adayı hiç oluşturmuyoruz.
        return None

    target_binding = next((b for b in all_bindings if b.field_name == TARGET_FIELD_NAME), None)
    parameter_bindings = tuple(b for b in all_bindings if b.field_name != TARGET_FIELD_NAME)
    if not include_parameter_bindings:
        parameter_bindings = ()

    return PlanCandidate(
        plan_id=_plan_id(family_id, plan_type, anchor),
        family_id=family_id,
        plan_type=plan_type,
        anchor=anchor,
        bindings=parameter_bindings,
        target_binding=target_binding,
        supporting_occurrences=supporting_occurrences,
    )


def build_plan_candidates(
    family: BehaviorFamily,
    member_series: list[OSeries],
    planner_config: PlannerConfig,
    risk_config: RiskConfig,
) -> list[PlanCandidate]:
    if not member_series:
        return []

    candidates: list[PlanCandidate] = []

    for anchor in select_navigate_anchors(family, member_series, risk_config):
        candidate = _build_candidate(
            family.family_id, PlanType.NAVIGATE, anchor, member_series, planner_config, False
        )
        if candidate is not None:
            candidates.append(candidate)

    for anchor in select_prefill_anchors(family, member_series, risk_config):
        candidate = _build_candidate(
            family.family_id, PlanType.PREFILL, anchor, member_series, planner_config, True
        )
        if candidate is not None:
            candidates.append(candidate)

    return candidates


# =============================================================================
# FILE: src/awe/risk/__init__.py
# =============================================================================
from awe.risk.evaluation import evaluate_risk
from awe.risk.evidence import build_risk_evidence
from awe.risk.resolver import ResolverContract

__all__ = ["evaluate_risk", "build_risk_evidence", "ResolverContract"]


# =============================================================================
# FILE: src/awe/risk/resolver.py
# =============================================================================
"""Client Resolver sözleşmesi (bölüm 78).

Backend, geçmiş loglardan istemci uygulamanın belirli bir state'e gerçekten programatik
olarak gidebileceğini bilemez. Bu minimal sözleşme, entegrasyonun neyi destekleyip
desteklemediğini açıkça beyan etmesini sağlar — ağır bir capability manifest sistemi değildir
(bölüm 3.6).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolverContract:
    supports_navigate: bool = True
    supports_prefill: bool = True
    accepted_bindings: frozenset[str] | None = None
    """None: her binding kabul edilir. Boş olmayan bir küme: yalnızca bu alan adları
    prefill edilebilir, geri kalanı REDUCE_BINDINGS ile düşürülür."""
    requires_review: bool = False
    supports_runtime_validation: bool = False

    @staticmethod
    def permissive() -> ResolverContract:
        return ResolverContract()


# =============================================================================
# FILE: src/awe/risk/evidence.py
# =============================================================================
"""PlanCandidate için Risk kanıtının toplanması (bölüm 81)."""

from __future__ import annotations

from awe.config.engine_config import PlannerConfig, RiskConfig
from awe.domain.enums import EffectPolicy, ObservationEffect, ObservationStatus, PlanType
from awe.domain.family import BehaviorFamily
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskEvidence
from awe.domain.series import OSeries
from awe.planner.state_reconstruction import resolve_anchor_step_index
from awe.risk.resolver import ResolverContract


def _drift_detected(candidate: PlanCandidate, planner_config: PlannerConfig) -> bool:
    bindings = list(candidate.bindings)
    if candidate.target_binding is not None:
        bindings.append(candidate.target_binding)
    for binding in bindings:
        if binding.recent_dominance is None:
            continue
        if binding.dominance - binding.recent_dominance >= planner_config.recent_drift_drop_threshold:
            return True
    return False


def build_risk_evidence(
    candidate: PlanCandidate,
    family: BehaviorFamily,
    member_series: list[OSeries],
    resolver: ResolverContract,
    planner_config: PlannerConfig,
    risk_config: RiskConfig,
) -> RiskEvidence:
    anchor_effect = candidate.anchor.symbol[1]
    effect_policy = risk_config.effect_policy.get(ObservationEffect(anchor_effect), EffectPolicy.REVIEW)

    total_family_occurrences = len(family.member_series_ids) or len(member_series)
    anchor_coverage = (
        candidate.supporting_occurrences / total_family_occurrences if total_family_occurrences else 0.0
    )

    coverages = [b.coverage for b in candidate.bindings]
    if candidate.target_binding is not None:
        coverages.append(candidate.target_binding.coverage)
    state_confidence = sum(coverages) / len(coverages) if coverages else 1.0

    binding_dominance = (
        sum(b.dominance for b in candidate.bindings) / len(candidate.bindings)
        if candidate.bindings
        else None
    )
    binding_coverage = (
        sum(b.coverage for b in candidate.bindings) / len(candidate.bindings)
        if candidate.bindings
        else None
    )

    reached = [
        series
        for series in member_series
        if resolve_anchor_step_index(series, candidate.anchor.symbol) is not None
    ]
    total_reached = len(reached) or 1
    completion_rate = sum(1 for s in reached if s.final_status == ObservationStatus.SUCCESS) / total_reached
    failure_rate = sum(1 for s in reached if s.final_status == ObservationStatus.FAIL) / total_reached
    cancel_rate = sum(1 for s in reached if s.final_status == ObservationStatus.CANCEL) / total_reached

    relevant_observations = [
        obs
        for series in reached
        for obs in series.raw_observations[: (resolve_anchor_step_index(series, candidate.anchor.symbol) or 0) + 1]
    ]
    data_quality_score = (
        sum(1.0 if not obs.quality.mapping_warnings else 0.5 for obs in relevant_observations)
        / len(relevant_observations)
        if relevant_observations
        else 1.0
    )

    resolver_supported = (
        resolver.supports_navigate if candidate.plan_type == PlanType.NAVIGATE else resolver.supports_prefill
    )

    return RiskEvidence(
        effect_policy=effect_policy,
        anchor_coverage=anchor_coverage,
        state_confidence=state_confidence,
        target_dominance=candidate.target_binding.dominance if candidate.target_binding else None,
        target_coverage=candidate.target_binding.coverage if candidate.target_binding else None,
        binding_dominance=binding_dominance,
        binding_coverage=binding_coverage,
        sample_size=candidate.supporting_occurrences,
        recent_drift=_drift_detected(candidate, planner_config),
        completion_rate=completion_rate,
        failure_rate=failure_rate,
        cancel_rate=cancel_rate,
        resolver_supported=resolver_supported,
        requires_review=resolver.requires_review,
        runtime_validation_passed=None,
        data_quality_score=data_quality_score,
        family_ambiguous=len(family.ambiguous_series_ids) > 0,
        family_cohesion=family.cohesion,
    )


# =============================================================================
# FILE: src/awe/risk/evaluation.py
# =============================================================================
"""Risk kararı: PlanCandidate güvenli mi (bölüm 79-83).

Karar önceliği: BLOCK > DOWNGRADE_TO_NAVIGATE > REDUCE_BINDINGS > ALLOW_WITH_REVIEW > ALLOW.
Hiçbir Benefit değeri, burada verilen BLOCK kararını geçersiz kılamaz (bölüm 90) — bu fonksiyon
Benefit'i hiç görmez, invariant çağıran katmanın Benefit'i Risk'ten sonra ve ondan bağımsız
uygulamasıyla korunur.
"""

from __future__ import annotations

import dataclasses

from awe.config.engine_config import PlannerConfig, RiskConfig
from awe.domain.enums import EffectPolicy, FieldState, PlanType, ReasonCode, RiskDecisionType
from awe.domain.family import BehaviorFamily
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskDecisionResult, RiskEvidence
from awe.domain.series import OSeries
from awe.risk.evidence import build_risk_evidence
from awe.risk.resolver import ResolverContract

_SEVERITY = {
    RiskDecisionType.ALLOW: 0,
    RiskDecisionType.ALLOW_WITH_REVIEW: 1,
    RiskDecisionType.REDUCE_BINDINGS: 2,
    RiskDecisionType.DOWNGRADE_TO_NAVIGATE: 3,
    RiskDecisionType.BLOCK: 4,
}


def _hard_block_reasons(
    evidence: RiskEvidence, runtime_validation_passed: bool | None
) -> tuple[ReasonCode, ...]:
    reasons = []
    if evidence.effect_policy == EffectPolicy.BLOCKED:
        reasons.append(ReasonCode.EXECUTE_BLOCKED)
    if not evidence.resolver_supported:
        reasons.append(ReasonCode.RESOLVER_UNSUPPORTED)
    if runtime_validation_passed is False:
        reasons.append(ReasonCode.RUNTIME_VALIDATION_FAILED)
    return tuple(reasons)


def evaluate_risk(
    candidate: PlanCandidate,
    family: BehaviorFamily,
    member_series: list[OSeries],
    resolver: ResolverContract,
    planner_config: PlannerConfig,
    risk_config: RiskConfig,
    *,
    runtime_validation_passed: bool | None = None,
) -> RiskDecisionResult:
    evidence = build_risk_evidence(candidate, family, member_series, resolver, planner_config, risk_config)
    if runtime_validation_passed is not None:
        evidence = dataclasses.replace(evidence, runtime_validation_passed=runtime_validation_passed)

    decision = RiskDecisionType.ALLOW
    reasons: list[ReasonCode] = []
    reduced_fields: list[str] = []

    def escalate(candidate_decision: RiskDecisionType, *reason_codes: ReasonCode) -> None:
        nonlocal decision
        if _SEVERITY[candidate_decision] > _SEVERITY[decision]:
            decision = candidate_decision
        reasons.extend(reason_codes)

    hard_block_reasons = _hard_block_reasons(evidence, runtime_validation_passed)
    if hard_block_reasons:
        escalate(RiskDecisionType.BLOCK, *hard_block_reasons)
        return RiskDecisionResult(
            plan_id=candidate.plan_id,
            decision=decision,
            evidence=evidence,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    if candidate.plan_type == PlanType.PREFILL:
        target = candidate.target_binding
        if target is not None and target.state != FieldState.STABLE:
            unstable_reason = (
                ReasonCode.UNKNOWN_TARGET if target.state == FieldState.UNKNOWN else ReasonCode.UNSTABLE_TARGET
            )
            escalate(RiskDecisionType.DOWNGRADE_TO_NAVIGATE, unstable_reason, ReasonCode.PREFILL_DOWNGRADED)
        else:
            # Target zaten stabil (ya da bu akışta hiç yoksa) — bu tek başına prefill'i
            # değerli kılmaya yeter (bölüm 117: "target stable + amount variable"). Yalnızca
            # ne target ne de HİÇBİR parametre stabilse prefill'in kazandıracağı bir şey
            # kalmaz ve NAVIGATE'e düşülür; aksi halde yalnızca stabil olmayan alanlar
            # düşürülür (REDUCE_BINDINGS).
            unstable = [b for b in candidate.bindings if b.state != FieldState.STABLE]
            stable = [b for b in candidate.bindings if b.state == FieldState.STABLE]
            target_is_usable = target is not None and target.state == FieldState.STABLE
            if unstable and not stable and not target_is_usable:
                escalate(
                    RiskDecisionType.DOWNGRADE_TO_NAVIGATE,
                    ReasonCode.LOW_BINDING_COVERAGE,
                    ReasonCode.PREFILL_DOWNGRADED,
                )
                reduced_fields.extend(b.field_name for b in unstable)
            elif unstable:
                escalate(
                    RiskDecisionType.REDUCE_BINDINGS,
                    ReasonCode.LOW_BINDING_COVERAGE,
                    ReasonCode.PREFILL_REDUCED,
                )
                reduced_fields.extend(b.field_name for b in unstable)

        if resolver.accepted_bindings is not None:
            rejected = [
                b.field_name for b in candidate.bindings if b.field_name not in resolver.accepted_bindings
            ]
            if rejected:
                escalate(RiskDecisionType.REDUCE_BINDINGS, ReasonCode.PREFILL_REDUCED)
                reduced_fields.extend(rejected)
    else:
        target = candidate.target_binding
        if target is not None and target.state != FieldState.STABLE:
            unstable_reason = (
                ReasonCode.UNKNOWN_TARGET if target.state == FieldState.UNKNOWN else ReasonCode.UNSTABLE_TARGET
            )
            escalate(RiskDecisionType.ALLOW_WITH_REVIEW, unstable_reason, ReasonCode.REVIEW_REQUIRED)

    if evidence.sample_size < risk_config.min_sample_size_for_confidence:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)
    if (
        evidence.failure_rate > risk_config.max_failure_rate_for_allow
        or evidence.cancel_rate > risk_config.max_cancel_rate_for_allow
    ):
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)
    if evidence.data_quality_score < risk_config.min_data_quality_for_allow:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)
    if evidence.family_ambiguous:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.AMBIGUOUS_FAMILY, ReasonCode.REVIEW_REQUIRED)
    elif evidence.family_cohesion < risk_config.min_family_cohesion_for_allow:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.LOW_COHESION, ReasonCode.REVIEW_REQUIRED)
    if resolver.requires_review:
        escalate(RiskDecisionType.ALLOW_WITH_REVIEW, ReasonCode.REVIEW_REQUIRED)

    return RiskDecisionResult(
        plan_id=candidate.plan_id,
        decision=decision,
        evidence=evidence,
        reason_codes=tuple(dict.fromkeys(reasons)),
        reduced_bindings=tuple(dict.fromkeys(reduced_fields)),
    )


# =============================================================================
# FILE: src/awe/benefit/__init__.py
# =============================================================================
from awe.benefit.evaluation import evaluate_benefit

__all__ = ["evaluate_benefit"]


# =============================================================================
# FILE: src/awe/benefit/evaluation.py
# =============================================================================
"""Benefit: shortcut kullanıcının gerçek manuel işinden ne kadarını kaldırıyor (bölüm 84-89).

Ham event sayısı değil, yalnızca `role=action` (gerçek kullanıcı eylemi) adımları sayılır
(bölüm 85). Retry ve bounded detour'lar zaten O-Series normalizasyonunda tek adıma
sıkıştırıldığı için (bölüm 87) burada ayrıca bir düzeltme yapmaya gerek yoktur — misclick ve
teknik retry'ler Benefit'i suni biçimde şişirmez.
"""

from __future__ import annotations

import statistics

from awe.config.engine_config import BenefitConfig
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import ObservationRole
from awe.domain.plan import PlanCandidate
from awe.domain.series import OSeries
from awe.planner.state_reconstruction import resolve_anchor_step_index


def _saved_user_actions(series: OSeries, anchor_symbol: tuple[str, str]) -> int | None:
    anchor_index = resolve_anchor_step_index(series, anchor_symbol)
    if anchor_index is None:
        return None
    prefix = series.normalized_steps[: anchor_index + 1]
    return sum(
        1
        for step in prefix
        if series.raw_observations[step.observation_index].role == ObservationRole.ACTION
    )


def _quartiles(values: list[int]) -> tuple[float, float, float]:
    if len(values) == 1:
        only = float(values[0])
        return only, only, only
    p25, _, p75 = statistics.quantiles(values, n=4, method="inclusive")
    return p25, statistics.median(values), p75


def evaluate_benefit(
    candidate: PlanCandidate,
    member_series: list[OSeries],
    config: BenefitConfig,
) -> BenefitEvidence:
    observed = [
        value
        for series in member_series
        if (value := _saved_user_actions(series, candidate.anchor.symbol)) is not None
    ]

    total_considered = len(member_series) or 1
    benefit_coverage = len(observed) / total_considered

    if not observed:
        return BenefitEvidence(
            plan_id=candidate.plan_id,
            median_saved_actions=0.0,
            p25_saved_actions=0.0,
            p75_saved_actions=0.0,
            benefit_coverage=0.0,
            sample_size=0,
            meets_minimum=False,
        )

    p25, median, p75 = _quartiles(observed)
    meets_minimum = median >= config.min_median_saved_actions and benefit_coverage >= config.min_benefit_coverage

    return BenefitEvidence(
        plan_id=candidate.plan_id,
        median_saved_actions=median,
        p25_saved_actions=p25,
        p75_saved_actions=p75,
        benefit_coverage=benefit_coverage,
        sample_size=len(observed),
        meets_minimum=meets_minimum,
    )


# =============================================================================
# FILE: src/awe/selection/__init__.py
# =============================================================================
from awe.selection.dedupe import FamilyPlan, dedupe_across_families
from awe.selection.family_selection import EvaluatedCandidate, FamilySelection, select_family_plan

__all__ = [
    "EvaluatedCandidate",
    "FamilySelection",
    "select_family_plan",
    "FamilyPlan",
    "dedupe_across_families",
]


# =============================================================================
# FILE: src/awe/selection/family_selection.py
# =============================================================================
"""Family içi dominance ve fallback zinciri seçimi (bölüm 91, 83).

Bu katman Habit/Risk/Benefit hesaplarını tekrar etmez; yalnızca önceki katmanlardan gelen
sonuçlar arasında birincil planı ve güvenli fallback zincirini belirler. Bir PREFILL adayı
Risk tarafından `DOWNGRADE_TO_NAVIGATE` olarak işaretlenmişse, bu seçim aşamasında fiilen bir
NAVIGATE adayı gibi değerlendirilir (bölüm 83'teki "PREFILL kaybolmasın, güvenli olana düşsün"
prensibi).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import FieldState, PlanType, RiskDecisionType
from awe.domain.plan import PlanCandidate
from awe.domain.risk import RiskDecisionResult

_SURVIVING_DECISIONS = (
    RiskDecisionType.ALLOW,
    RiskDecisionType.ALLOW_WITH_REVIEW,
    RiskDecisionType.REDUCE_BINDINGS,
    RiskDecisionType.DOWNGRADE_TO_NAVIGATE,
)


@dataclass(frozen=True, slots=True)
class EvaluatedCandidate:
    candidate: PlanCandidate
    risk: RiskDecisionResult
    benefit: BenefitEvidence


@dataclass(frozen=True, slots=True)
class FamilySelection:
    primary: EvaluatedCandidate
    fallback_plan_ids: tuple[str, ...]
    dominated_plan_ids: frozenset[str]


def _effective_navigate_position(item: EvaluatedCandidate) -> int | None:
    if item.risk.decision not in _SURVIVING_DECISIONS:
        return None
    if item.candidate.plan_type == PlanType.NAVIGATE:
        return item.candidate.anchor.core_position
    if item.risk.decision == RiskDecisionType.DOWNGRADE_TO_NAVIGATE:
        return item.candidate.anchor.core_position
    return None


def _is_true_prefill(item: EvaluatedCandidate) -> bool:
    return item.candidate.plan_type == PlanType.PREFILL and item.risk.decision in (
        RiskDecisionType.ALLOW,
        RiskDecisionType.ALLOW_WITH_REVIEW,
        RiskDecisionType.REDUCE_BINDINGS,
    )


def _prefill_richness(item: EvaluatedCandidate) -> tuple[int, int, float]:
    stable_bindings = sum(1 for b in item.candidate.bindings if b.state == FieldState.STABLE)
    return (stable_bindings, item.candidate.anchor.core_position, item.benefit.median_saved_actions)


def select_family_plan(evaluated: list[EvaluatedCandidate]) -> FamilySelection | None:
    survivors = [
        item
        for item in evaluated
        if item.risk.decision in _SURVIVING_DECISIONS and item.benefit.meets_minimum
    ]
    if not survivors:
        return None

    dominated: set[str] = set()

    navigate_pool = [item for item in survivors if _effective_navigate_position(item) is not None]
    primary_navigate: EvaluatedCandidate | None = None
    if navigate_pool:
        navigate_pool.sort(key=lambda item: _effective_navigate_position(item) or 0, reverse=True)
        primary_navigate = navigate_pool[0]
        dominated.update(item.candidate.plan_id for item in navigate_pool[1:])

    prefill_pool = [item for item in survivors if _is_true_prefill(item)]
    primary_prefill: EvaluatedCandidate | None = None
    if prefill_pool:
        prefill_pool.sort(key=_prefill_richness, reverse=True)
        primary_prefill = prefill_pool[0]
        dominated.update(item.candidate.plan_id for item in prefill_pool[1:])

    if primary_prefill is not None:
        primary = primary_prefill
        fallback = (
            (primary_navigate.candidate.plan_id,)
            if primary_navigate is not None
            and primary_navigate.candidate.plan_id != primary_prefill.candidate.plan_id
            else ()
        )
    elif primary_navigate is not None:
        primary = primary_navigate
        fallback = ()
    else:
        return None

    dominated.discard(primary.candidate.plan_id)
    for plan_id in fallback:
        dominated.discard(plan_id)

    return FamilySelection(primary=primary, fallback_plan_ids=fallback, dominated_plan_ids=frozenset(dominated))


# =============================================================================
# FILE: src/awe/selection/dedupe.py
# =============================================================================
"""Family'ler arası aynı yapısal anchor'a düşen çakışan önerilerin ayıklanması (bölüm 91)."""

from __future__ import annotations

from dataclasses import dataclass

from awe.selection.family_selection import FamilySelection


@dataclass(frozen=True, slots=True)
class FamilyPlan:
    family_id: str
    selection: FamilySelection


def _dedupe_key(plan) -> tuple:
    return (plan.anchor.symbol, plan.plan_type)


def dedupe_across_families(family_plans: list[FamilyPlan]) -> tuple[list[FamilyPlan], frozenset[str]]:
    """Aynı (anchor sembolü, plan tipi) çiftine sahip birincil planlardan yalnızca en yüksek
    Benefit'e sahip olanı tutar; geri kalanlar `DUPLICATE_PLAN` olarak dışarıda bırakılır."""

    groups: dict[tuple, list[FamilyPlan]] = {}
    for plan in family_plans:
        key = _dedupe_key(plan.selection.primary.candidate)
        groups.setdefault(key, []).append(plan)

    kept: list[FamilyPlan] = []
    duplicate_plan_ids: set[str] = set()
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue
        group.sort(key=lambda p: p.selection.primary.benefit.median_saved_actions, reverse=True)
        kept.append(group[0])
        duplicate_plan_ids.update(p.selection.primary.candidate.plan_id for p in group[1:])

    return kept, frozenset(duplicate_plan_ids)


# =============================================================================
# FILE: src/awe/lifecycle/__init__.py
# =============================================================================
from awe.lifecycle.transitions import dismiss, next_state_for_reanalysis

__all__ = ["dismiss", "next_state_for_reanalysis"]


# =============================================================================
# FILE: src/awe/lifecycle/transitions.py
# =============================================================================
"""Suggestion lifecycle geçişleri (bölüm 94).

Bir suggestion DISMISSED durumundayken cooldown süresi dolar ve davranış organik olarak
tekrar etmeye devam ederse ACTIVE'e geri döner — dismiss kalıcı bir ret değil, geçici bir
bastırmadır. Cooldown süresi dolmuş ama organik kanıt de kaybolmuşsa DISMISSED'te kalır
(kullanıcı zaten reddetmişti, yeniden canlanmak için tekrar organik kullanım gerekir).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from awe.config.engine_config import LifecycleConfig
from awe.domain.enums import HabitDecision, LivenessState, SuggestionState


def next_state_for_reanalysis(
    current_state: SuggestionState | None,
    dismiss_cooldown_until: datetime | None,
    habit_decision: HabitDecision,
    has_eligible_plan: bool,
    liveness: LivenessState | None,
    now: datetime,
) -> SuggestionState:
    if current_state == SuggestionState.DISMISSED:
        cooldown_expired = dismiss_cooldown_until is not None and now >= dismiss_cooldown_until
        if cooldown_expired and habit_decision == HabitDecision.PASS and has_eligible_plan:
            return SuggestionState.ACTIVE
        return SuggestionState.DISMISSED

    if habit_decision == HabitDecision.NOT_HABIT or not has_eligible_plan:
        return SuggestionState.INVALIDATED if current_state is not None else SuggestionState.PENDING_EVIDENCE

    if habit_decision == HabitDecision.PENDING_EVIDENCE:
        return SuggestionState.PENDING_EVIDENCE

    if liveness == LivenessState.STALE:
        return SuggestionState.STALE

    return SuggestionState.ACTIVE


def dismiss(now: datetime, config: LifecycleConfig) -> tuple[SuggestionState, datetime]:
    return SuggestionState.DISMISSED, now + timedelta(days=config.dismiss_cooldown_days)


# =============================================================================
# DOSYA SONU — src/awe altındaki TÜM paketler bu dosyada mevcuttur.
# =============================================================================
