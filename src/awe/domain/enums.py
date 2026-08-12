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
