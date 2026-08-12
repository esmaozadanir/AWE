"""AWE Core'un paylaştığı, uygulamadan bağımsız sabit kelime dağarcığı.

Buradaki değerler AWE Core'un canonical sözleşmesidir (bkz. AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md,
bölüm 4). Müşteriye özel iş isimleri bu modülde bulunmaz; onlar yalnızca Adapter/Mapping ve proje
konfigürasyonu seviyesinde ortaya çıkar.
"""

from __future__ import annotations

from enum import StrEnum


class ObservationSource(StrEnum):
    CLIENT = "client"
    SERVER = "server"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ObservationTrigger(StrEnum):
    BUTTON = "button"
    KEYBOARD = "keyboard"
    VOICE = "voice"
    LONG_PRESS = "long_press"
    HARDWARE = "hardware"
    BIOMETRIC = "biometric"
    SWIPE = "swipe"
    DRAG = "drag"
    NAVIGATION = "navigation"
    NOTIFICATION = "notification"
    DEEPLINK = "deeplink"
    AUTOMATIC = "automatic"
    SHORTCUT = "shortcut"
    """Tasarım belgesinde yok; kasıtlı ek. Bir occurrence'ın bir kısayol tetiklemesiyle mi
    başladığını işaretlemenin tek yolu budur — bu olmadan Habit Evaluator, kısayolun kendi
    kullanımını organik tekrar kanıtı olarak sayabilir (kendini besleyen döngü riski).
    Sınıflandırma kurallarını etkilemez; yalnızca `has_shortcut_trigger` gibi kontaminasyon
    denetimlerinde kullanılır (bkz. `awe.habit.assessment`)."""
    UNKNOWN = "unknown"


class ObservationEffect(StrEnum):
    SUBMIT = "submit"
    CREATE = "create"
    DELETE = "delete"
    CONFIRM = "confirm"
    UPDATE = "update"
    TOGGLE = "toggle"
    ROUTE = "route"
    REQUEST = "request"
    OPEN = "open"
    DOWNLOAD = "download"
    INPUT = "input"
    SELECT = "select"
    FILTER = "filter"
    SORT = "sort"
    FOCUS = "focus"
    VIEW = "view"
    NONE = "none"
    UNKNOWN = "unknown"


class ObservationStatus(StrEnum):
    SUCCESS = "success"
    FAIL = "fail"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


class EventClassification(StrEnum):
    """Ham event'in temiz action akışındaki rolü (bkz. `awe.adapter.classification`).

    Kalıcı bir Observation alanı değildir; ihtiyaç anında `classify_event()` ile hesaplanır.
    Hiçbir zaman `action`/`screen` gibi müşteriye özel string'lere bakılmaz."""

    ACTION = "action"
    CONTEXT = "context"
    IGNORE = "ignore"


class OrderingConfidence(StrEnum):
    """Session içi sıralamanın gerçek temporal sıraya güven derecesi."""

    HIGH = "high"
    LOW = "low"


class TargetVariantKind(StrEnum):
    """Bir Exact Base Family occurrence'ının target fingerprint sınıfı (Target Resolver)."""

    NO_EXPLICIT_TARGET = "no_explicit_target"
    FIXED_TARGET = "fixed_target"
    VARIABLE_TARGET = "variable_target"
    UNKNOWN_TARGET = "unknown_target"


class ScreenEvidenceState(StrEnum):
    """Anchor sonrası gözlenen ekranın session'lar arası tutarlılığı (Screen Transition Evidence)."""

    STABLE = "stable"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient"


class HabitDecision(StrEnum):
    HABIT_DETECTED = "habit_detected"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AnchorStrength(StrEnum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class AnchorStatus(StrEnum):
    RESOLVED = "resolved"
    ATTEMPT_ONLY = "attempt_only"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class PlanMode(StrEnum):
    NAVIGATE = "navigate"
    PREFILL = "prefill"


class IntentState(StrEnum):
    READY = "ready"
    UNSUPPORTED = "unsupported"


class AutomaticAction(StrEnum):
    """Sabit tek değer — EXECUTE modu olmadığı için her zaman NONE (bölüm 6.12)."""

    NONE = "none"


class FinalActionOwner(StrEnum):
    """Sabit tek değer — son işlem her zaman kullanıcıda kalır (bölüm 6.12)."""

    USER = "user"


class EffectPolicy(StrEnum):
    """Proje konfigürasyonunun bir `ObservationEffect` için tanımladığı güvenlik sınıfı."""

    SAFE = "safe"
    SENSITIVE = "sensitive"
    BLOCKED = "blocked"


class RiskDecision(StrEnum):
    """Selector'ın tek baktığı kapı değeri; kanıt vektörü ayrıca `RiskEvidence`'ta taşınır."""

    ALLOW = "allow"
    BLOCK = "block"


class ExecutionExposure(StrEnum):
    """EXECUTE modu olmadığı için MVP'de her zaman NONE — Risk vektöründe açıkça belgelenir."""

    NONE = "none"


class BenefitLevel(StrEnum):
    NEGATIVE = "negative"
    NONE = "none"
    LIMITED = "limited"
    CLEAR = "clear"


class SelectionOutcome(StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"
    DEDUPED = "deduped"


class EpisodeCandidateKind(StrEnum):
    """Bir Episode Candidate'in nasıl üretildiği (bölüm 6.4) — yalnızca açıklanabilirlik amaçlı."""

    FULL_CHUNK = "full_chunk"
    COMMON_RUN = "common_run"


class SuggestionState(StrEnum):
    PENDING_EVIDENCE = "pending_evidence"
    ACTIVE = "active"
    STALE = "stale"
    DISMISSED = "dismissed"
    INVALIDATED = "invalidated"


class ReasonCode(StrEnum):
    INSUFFICIENT_OCCURRENCES = "insufficient_occurrences"
    INSUFFICIENT_DISTINCT_SESSIONS = "insufficient_distinct_sessions"
    INSUFFICIENT_DISTINCT_DAYS = "insufficient_distinct_days"
    STALE_BEHAVIOR = "stale_behavior"
    ATTEMPT_ONLY = "attempt_only"
    AMBIGUOUS_ANCHOR = "ambiguous_anchor"
    UNKNOWN_TARGET_BLOCKS_ANCHOR = "unknown_target_blocks_anchor"
    UNSUPPORTED_COMPOUND_TARGET = "unsupported_compound_target"
    UNREPRESENTED_INTERMEDIATE_ACTION = "unrepresented_intermediate_action"
    DESTINATION_UNRESOLVED = "destination_unresolved"
    EXECUTE_BLOCKED_EFFECT = "execute_blocked_effect"
    UNKNOWN_EFFECT = "unknown_effect"
    CRITICAL_QUALITY_FLAG = "critical_quality_flag"
    UNKNOWN_ANCHOR_STATUS = "unknown_anchor_status"
    MIXED_OBSERVED_OUTCOMES = "mixed_observed_outcomes"
    RESOLVER_UNSUPPORTED = "resolver_unsupported"
    BENEFIT_TOO_LOW = "benefit_too_low"
    DUPLICATE_PLAN = "duplicate_plan"
    DOMINATED_PLAN = "dominated_plan"
    NO_PLAN_CANDIDATE = "no_plan_candidate"
    CONFLICTING_EVENT_ID = "conflicting_event_id"
    AMBIGUOUS_TIMESTAMP_ORDER = "ambiguous_timestamp_order"
