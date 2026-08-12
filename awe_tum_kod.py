# AWE Engine -- tum src/awe kaynak kodu, tek dosyada birlestirilmis.
# Bu dosya calistirilmak icin degil, referans/inceleme icin uretilmistir.
# Gercek proje src/awe/ altinda normal Python paketi olarak yasar.
#
# AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md spesifikasyonuna gore yeniden yazilmis motor.


# ==============================================================================
# FILE: src/awe/adapter/__init__.py
# ==============================================================================
from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.adapter.observation_builder import AdapterValidationError, build_observation

__all__ = [
    "AdapterMapping",
    "FieldRule",
    "TargetRule",
    "AdapterValidationError",
    "build_observation",
]


# ==============================================================================
# FILE: src/awe/adapter/classification.py
# ==============================================================================
"""Canonical Observation'dan ACTION/CONTEXT/IGNORE sınıflandırması (bölüm 6.2).

Sınıflandırma yalnızca `trigger`, `effect` ve `source` üçlüsünden yapısal olarak türetilir.
Sonuç kalıcı bir Observation alanı değildir; ihtiyaç anında hesaplanan bir değerdir.

Bilinçli davranış değişiklikleri (önceki tasarıma göre — bkz. final rapor):
- `status` artık sınıflandırmayı hiç etkilemez ("status=fail/cancel olan kullanıcı
  ACTION'ları diziden atılmaz", bölüm 3 kural 4). Başarısız denemenin genel occurrence'ı
  `ATTEMPT_ONLY` mi `RESOLVED` mi yaptığı Anchor Resolver'ın işidir (bölüm 6.9), burada değil.
- `source != "client"` artık her zaman CONTEXT üretir. Önceki tasarımda source hiçbir zaman
  gerçek bir kullanıcı ACTION'ını dışlamak için kullanılmazdı; yeni belge (bölüm 6.2) bunun
  tersini söylüyor ve burada harfiyen uygulanmıştır.
"""

from __future__ import annotations

from awe.domain.enums import EventClassification, ObservationEffect, ObservationSource, ObservationTrigger
from awe.domain.observation import Observation

USER_TRIGGERS = frozenset(
    {
        ObservationTrigger.BUTTON,
        ObservationTrigger.KEYBOARD,
        ObservationTrigger.VOICE,
        ObservationTrigger.LONG_PRESS,
        ObservationTrigger.HARDWARE,
        ObservationTrigger.BIOMETRIC,
        ObservationTrigger.SWIPE,
        ObservationTrigger.DRAG,
        ObservationTrigger.NAVIGATION,
        ObservationTrigger.NOTIFICATION,
        ObservationTrigger.DEEPLINK,
        ObservationTrigger.SHORTCUT,
    }
)
"""Belgede tanımı verilmemiş; `classify_event` sözde kodunda yalnızca isim olarak geçer
(bölüm 6.2). Bölüm 4'ün trigger sözlüğünden `automatic` ve `unknown` çıkarılarak türetilmiştir
— geri kalan tüm tetikleyiciler kullanıcının doğrudan girdisidir. `shortcut` (bölüm 4'te
literal olarak yok, bkz. `ObservationTrigger.SHORTCUT` docstring'i) kasıtlı olarak dahildir:
bir kısayolun tetiklediği event de gerçek bir kullanıcı ACTION'ıdır, yalnızca Habit'in organik
kanıt sayımından ayrıca dışlanır (bkz. `awe.habit.assessment`)."""


def classify_event(observation: Observation) -> EventClassification:
    if observation.effect == ObservationEffect.NONE:
        return EventClassification.IGNORE

    if observation.effect == ObservationEffect.VIEW:
        return EventClassification.CONTEXT

    if observation.source != ObservationSource.CLIENT or observation.trigger == ObservationTrigger.AUTOMATIC:
        return EventClassification.CONTEXT

    if observation.trigger in USER_TRIGGERS:
        return EventClassification.ACTION

    return EventClassification.CONTEXT


# ==============================================================================
# FILE: src/awe/adapter/mapping.py
# ==============================================================================
"""Adapter mapping sözleşmesi: müşteriye özel raw event alanlarının canonical alanlara
deklaratif olarak eşlenmesi (bölüm 6.1, 8).

AWE Core, bu modülü kullanarak hiçbir müşteriye özel Python kodu yazmadan farklı raw
telemetry formatlarını canonical Observation'a çevirir. Yeni bir müşteri entegrasyonu,
yeni kod değil yeni bir `AdapterMapping` konfigürasyonu demektir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def resolve_path(raw: dict[str, Any], path: str) -> Any:
    """Nokta ayraçlı bir path ile iç içe sözlükten değer okur (ör. 'data.screen')."""

    value, _ = resolve_path_with_presence(raw, path)
    return value


def resolve_path_with_presence(raw: dict[str, Any], path: str) -> tuple[Any, bool]:
    """`resolve_path` ile aynı, ama anahtarın hiç var olmadığını (`False`) anahtarın var
    olup değerinin `null` olduğundan (`True`, değer `None`) ayırt eder. Bu ayrım yalnızca
    `target` alanı için gereklidir (bölüm 3 kural 6: `null` ≠ "alan hiç gönderilmedi")."""

    current: Any = raw
    parts = path.split(".")
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    last = parts[-1]
    if not isinstance(current, dict) or last not in current:
        return None, False
    return current[last], True


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
    """Ham action string'ini normalize etmek için opsiyonel eşleme. Eşleşme yoksa ham değer
    aynen `action` olarak kullanılır — engine action'ın kendi business anlamını tahmin etmez."""

    screen_path: str | None = None
    duration_path: str | None = None

    source: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    effect: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    trigger: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    status: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))

    target: TargetRule = field(default_factory=TargetRule)


# ==============================================================================
# FILE: src/awe/adapter/observation_builder.py
# ==============================================================================
"""Raw event dict'ini canonical Observation'a çeviren tek yer (bölüm 6.1).

Zorunlu bir alan üretilemediğinde veya timestamp naive geldiğinde event reddedilir
(`AdapterValidationError`) — bölüm 6.1: "Zorunlu alan eksikse event reject edilir. Naive
timestamp reject edilir." Eksik/geçersiz opsiyonel alanlar reddetmez; canonical `unknown`'a
düşer ve `ObservationQuality` üzerinde bir kanıt/flag bırakır. Adapter alışkanlık, anchor
veya risk kararı vermez — yalnızca canonicalization yapar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from awe.adapter.mapping import AdapterMapping, FieldRule, resolve_path, resolve_path_with_presence
from awe.domain.enums import ObservationEffect, ObservationSource, ObservationStatus, ObservationTrigger
from awe.domain.observation import Observation, ObservationQuality


class AdapterValidationError(ValueError):
    """Zorunlu bir alan üretilemediğinde veya timestamp naive geldiğinde fırlatılır."""


def _require_str(raw: dict[str, Any], path: str, *, field_name: str) -> str:
    value = resolve_path(raw, path)
    if value is None:
        raise AdapterValidationError(f"required field '{field_name}' is missing")
    text = str(value).strip()
    if not text:
        raise AdapterValidationError(f"required field '{field_name}' is empty")
    return text


def _parse_timestamp(raw: dict[str, Any], mapping: AdapterMapping) -> datetime:
    text = _require_str(raw, mapping.timestamp_path, field_name="timestamp")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AdapterValidationError(f"invalid timestamp: {text!r}") from exc
    if parsed.tzinfo is None:
        raise AdapterValidationError(f"naive timestamp not allowed: {text!r}")
    return parsed.astimezone(UTC)


def _resolve_action(raw: dict[str, Any], mapping: AdapterMapping) -> str:
    raw_action = _require_str(raw, mapping.action_key_path, field_name="action")
    return mapping.action_key_value_map.get(raw_action, raw_action)


def _resolve_field_rule(
    raw: dict[str, Any],
    rule_name: str,
    rule: FieldRule,
    enum_type: type[StrEnum],
    warnings: list[str],
) -> str:
    if rule.path is None:
        return rule.default
    raw_value = resolve_path(raw, rule.path)
    if raw_value is None:
        return rule.default
    text = str(raw_value).strip().lower()
    if rule.value_map:
        if text in rule.value_map:
            return rule.value_map[text]
        warnings.append(f"unmapped_{rule_name}_raw_value:{text}")
        return rule.default
    valid_values = {member.value for member in enum_type}
    if text in valid_values:
        return text
    warnings.append(f"unmapped_{rule_name}_raw_value:{text}")
    return rule.default


def _resolve_screen(raw: dict[str, Any], mapping: AdapterMapping) -> str | None:
    if mapping.screen_path is None:
        return None
    value = resolve_path(raw, mapping.screen_path)
    return str(value) if value is not None else None


def _resolve_target(raw: dict[str, Any], mapping: AdapterMapping) -> tuple[str | None, bool]:
    """`(target, missing_target_field)` döner. `ref_path` konfigüre edilmemişse bu bir veri
    kalitesi sorunu değildir (mapping bilinçli olarak target izlemiyor): `(None, False)`.
    `ref_path` konfigüre edilmiş ama raw payload'da anahtar hiç yoksa: `(None, True)` — "hedef
    verisi bilinmiyor" (bölüm 3 kural 6). Anahtar var ve değeri `null`: `(None, False)` —
    "açıkça hedef yok". Anahtar var ve değeri doluysa: `(str(value), False)`."""

    if mapping.target.ref_path is None:
        return None, False
    value, present = resolve_path_with_presence(raw, mapping.target.ref_path)
    if not present:
        return None, True
    if value is None:
        return None, False
    return str(value), False


def _resolve_duration_ms(raw: dict[str, Any], mapping: AdapterMapping) -> tuple[int | None, bool]:
    """`(duration_ms, invalid)` döner. Negatif veya sayısal olmayan değerler `None` yapılır
    ve `invalid=True` işaretlenir (bölüm 6.1). `duration_ms` yalnızca audit amaçlıdır."""

    if mapping.duration_path is None:
        return None, False
    value = resolve_path(raw, mapping.duration_path)
    if value is None:
        return None, False
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return None, True
    if duration < 0:
        return None, True
    return duration, False


def build_observation(raw: dict[str, Any], mapping: AdapterMapping) -> Observation:
    event_id = _require_str(raw, mapping.event_id_path, field_name="event_id")
    project_id = _require_str(raw, mapping.project_id_path, field_name="project_id")
    subject_id = _require_str(raw, mapping.subject_id_path, field_name="subject_id")
    session_id = _require_str(raw, mapping.session_id_path, field_name="session_id")
    timestamp = _parse_timestamp(raw, mapping)
    action = _resolve_action(raw, mapping)

    warnings: list[str] = []
    source = ObservationSource(_resolve_field_rule(raw, "source", mapping.source, ObservationSource, warnings))
    trigger = ObservationTrigger(
        _resolve_field_rule(raw, "trigger", mapping.trigger, ObservationTrigger, warnings)
    )
    effect = ObservationEffect(_resolve_field_rule(raw, "effect", mapping.effect, ObservationEffect, warnings))
    status = ObservationStatus(_resolve_field_rule(raw, "status", mapping.status, ObservationStatus, warnings))

    screen = _resolve_screen(raw, mapping)
    target, missing_target_field = _resolve_target(raw, mapping)
    duration_ms, invalid_duration = _resolve_duration_ms(raw, mapping)

    quality = ObservationQuality(
        has_screen=screen is not None,
        missing_target_field=missing_target_field,
        invalid_duration=invalid_duration,
        warnings=tuple(warnings),
    )

    return Observation(
        event_id=event_id,
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        timestamp=timestamp,
        action=action,
        source=source,
        trigger=trigger,
        effect=effect,
        status=status,
        screen=screen,
        target=target,
        duration_ms=duration_ms,
        mapping_version=mapping.mapping_version,
        quality=quality,
    )


# ==============================================================================
# FILE: src/awe/api/__init__.py
# ==============================================================================



# ==============================================================================
# FILE: src/awe/api/dependencies.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/api/main.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/api/routes_events.py
# ==============================================================================
"""Event ingestion ve subject analiz endpoint'leri."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import (
    AnalysisResponse,
    BatchIngestResponse,
    EventIngestResponse,
    VariantAnalysisResponse,
)
from awe.config import ProjectConfig
from awe.services import IngestOutcome, analyze_subject, ingest_batch, ingest_event

router = APIRouter(prefix="/projects/{project_id}", tags=["events"])


def _ingest_response(outcome: IngestOutcome) -> EventIngestResponse:
    return EventIngestResponse(
        accepted=outcome.accepted,
        duplicate=outcome.duplicate,
        conflict=outcome.conflict,
        event_id=outcome.event_id,
        error=outcome.error,
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


@router.post("/subjects/{subject_id}/analyze", response_model=AnalysisResponse)
def post_analyze_subject(
    project_id: str,
    subject_id: str,
    project_config: ProjectConfig = Depends(get_project_config),
    session: Session = Depends(get_db_session),
) -> AnalysisResponse:
    summary = analyze_subject(session, project_config, project_id, subject_id, datetime.now(UTC))
    return AnalysisResponse(
        project_id=summary.project_id,
        subject_id=summary.subject_id,
        series_count=summary.series_count,
        variants=[
            VariantAnalysisResponse(
                variant_key=v.variant_key,
                habit_decision=v.habit_decision.value,
                suggestion_state=v.suggestion_state.value if v.suggestion_state else None,
            )
            for v in summary.variants
        ],
    )


# ==============================================================================
# FILE: src/awe/api/routes_suggestions.py
# ==============================================================================
"""Suggestion listeleme ve dismiss endpoint'leri."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from awe.api.dependencies import get_db_session, get_project_config
from awe.api.schemas import IntentResponse, SuggestionResponse
from awe.config import ProjectConfig
from awe.services import IntentView, SuggestionView, dismiss_suggestion, list_subject_suggestions

router = APIRouter(prefix="/projects/{project_id}/subjects/{subject_id}", tags=["suggestions"])


def _intent_response(intent: IntentView) -> IntentResponse:
    return IntentResponse(
        intent_key=intent.intent_key,
        mode=intent.mode,
        destination_screen=intent.destination_screen,
        target=intent.target,
        requires_user_confirmation=intent.requires_user_confirmation,
        risk_decision=intent.risk_decision,
        benefit_saved_actions=intent.benefit_saved_actions,
        benefit_level=intent.benefit_level,
    )


def _suggestion_response(view: SuggestionView) -> SuggestionResponse:
    return SuggestionResponse(
        suggestion_key=view.suggestion_key,
        state=view.state,
        reason_codes=view.reason_codes,
        intent=_intent_response(view.intent),
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


# ==============================================================================
# FILE: src/awe/api/schemas.py
# ==============================================================================
"""API'nin dışarıya sunduğu Pydantic request/response modelleri.

Bu modeller `awe.domain` nesnelerini birebir yansıtmaz; yalnızca dışarıya sunulması gereken
alanları taşır (ör. dahili veritabanı id'leri değil, opak `intent_key`/`suggestion_key` string'leri).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventIngestResponse(BaseModel):
    accepted: bool
    duplicate: bool
    conflict: bool = False
    event_id: str | None = None
    error: str | None = None


class BatchIngestResponse(BaseModel):
    results: list[EventIngestResponse]
    accepted_count: int
    duplicate_count: int
    rejected_count: int


class VariantAnalysisResponse(BaseModel):
    variant_key: str
    habit_decision: str
    suggestion_state: str | None


class AnalysisResponse(BaseModel):
    project_id: str
    subject_id: str
    series_count: int
    variants: list[VariantAnalysisResponse]


class IntentResponse(BaseModel):
    intent_key: str
    mode: str | None
    destination_screen: str | None
    target: str | None
    requires_user_confirmation: bool
    risk_decision: str
    benefit_saved_actions: int
    benefit_level: str


class SuggestionResponse(BaseModel):
    suggestion_key: str
    state: str
    reason_codes: list[str]
    intent: IntentResponse
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


# ==============================================================================
# FILE: src/awe/benefit/__init__.py
# ==============================================================================
from awe.benefit.evaluation import evaluate_benefit

__all__ = ["evaluate_benefit"]


# ==============================================================================
# FILE: src/awe/benefit/evaluation.py
# ==============================================================================
"""Benefit Evaluator (bölüm 6.14): kısayolun kullanıcı ACTION sayısını azaltıp azaltmadığını
ölçer. Popülasyon istatistiği (medyan/p25/p75) yoktur — her Shortcut Intent kendi tek,
deterministik Benefit değerini taşır.

`planned_actions` yorumu: doğrudan-geçiş (route/open) bir anchor'da NAVIGATE'in kendisi
zaten anchor adımının karşılığıdır (kullanıcı hâlâ yapması gereken ayrı bir "son işlem"
bırakmaz) → `planned=1` (yalnızca kısayol dokunuşu). Action-surface bir anchor'da (PREFILL
dahil) motor o işlemi hiç çalıştırmaz; kullanıcı hâlâ son işlemi kendisi yapmalıdır →
`planned=2` (dokunuş + son işlem). Bölüm 6.14'ün iki örneği de (K1→K2→K3 NAVIGATE: planned=1;
open_messages→apply_filter: planned=2) bu ayrımla birebir örtüşür.
"""

from __future__ import annotations

from awe.domain.benefit import BenefitEvidence
from awe.domain.plan import ShortcutIntent
from awe.planner.anchors import ROUTE_OPEN_EFFECTS


def evaluate_benefit(intent: ShortcutIntent, scope_length: int) -> BenefitEvidence:
    is_direct_transition = intent.anchor.symbol[1] in ROUTE_OPEN_EFFECTS
    planned_actions = 1 if is_direct_transition else 2
    return BenefitEvidence(
        intent_id=intent.intent_id, observed_actions=scope_length, planned_actions=planned_actions
    )


# ==============================================================================
# FILE: src/awe/config/__init__.py
# ==============================================================================
from awe.config.engine_config import (
    EngineConfig,
    EpisodeConfig,
    HabitConfig,
    LifecycleConfig,
    RiskConfig,
    ScreenEvidenceConfig,
    default_engine_config,
)
from awe.config.logging_config import configure_logging, log_event
from awe.config.project_config import ProjectConfig, ProjectNotFoundError, ProjectRegistry
from awe.config.settings import Settings, get_settings

__all__ = [
    "EngineConfig",
    "EpisodeConfig",
    "HabitConfig",
    "ScreenEvidenceConfig",
    "RiskConfig",
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


# ==============================================================================
# FILE: src/awe/config/engine_config.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/config/logging_config.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/config/project_config.py
# ==============================================================================
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
        duration_path=data.get("duration_path"),
        source=_build_field_rule(data.get("source")),
        effect=_build_field_rule(data.get("effect")),
        trigger=_build_field_rule(data.get("trigger")),
        status=_build_field_rule(data.get("status")),
        target=TargetRule(ref_path=target_data.get("ref_path")),
    )


def _build_engine_overrides(data: dict[str, Any] | None, timezone: str) -> EngineConfig:
    base = default_engine_config()
    if not data:
        return dataclasses.replace(base, timezone=timezone)

    section_names = ("episode", "habit", "screen_evidence", "risk", "lifecycle")
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
                f"config file '{candidate}' declares project_id '{config.project_id}', expected '{project_id}'"
            )
        self._cache[project_id] = config
        return config

    def known_project_ids(self) -> list[str]:
        return sorted(p.stem for p in self._config_dir.glob("*.yaml"))


# ==============================================================================
# FILE: src/awe/config/settings.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/domain/__init__.py
# ==============================================================================
"""AWE Core domain modelleri.

Bu paket, hiçbir uygulamaya özel iş kavramı (order, course, lesson, product vb.) içermez.
Adapter/Mapping ve proje konfigürasyonu bunun dışındadır. `tests/scenarios/
test_domain_universality.py` bu kısıtı otomatik olarak denetler.
"""


# ==============================================================================
# FILE: src/awe/domain/benefit.py
# ==============================================================================
"""Benefit Evaluator'ın kanıt modeli (bölüm 6.14).

`observed_actions - planned_actions` deterministik farkıdır; eski tasarımın medyan/p25/p75
popülasyon istatistiği yoktur — her Shortcut Intent kendi tek Benefit değerini taşır.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import BenefitLevel


@dataclass(frozen=True, slots=True)
class BenefitEvidence:
    intent_id: str
    observed_actions: int
    planned_actions: int

    @property
    def saved_actions(self) -> int:
        return self.observed_actions - self.planned_actions

    @property
    def level(self) -> BenefitLevel:
        if self.saved_actions < 0:
            return BenefitLevel.NEGATIVE
        if self.saved_actions == 0:
            return BenefitLevel.NONE
        if self.saved_actions == 1:
            return BenefitLevel.LIMITED
        return BenefitLevel.CLEAR


# ==============================================================================
# FILE: src/awe/domain/enums.py
# ==============================================================================
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
    """Bir Episode Candidate'in nasıl üretildiği — yalnızca açıklanabilirlik amaçlı."""

    FULL_CHUNK = "full_chunk"
    COMMON_SUBSEQUENCE = "common_subsequence"
    """Farklı chunk'lar arasında bulunan, sıra-korumalı (mutlaka ardışık olması gerekmeyen)
    exact ortak alt dizi (bkz. `awe.episodes.candidates` modül docstring'i — bölüm 6.4'ün
    "contiguous" tanımından kasıtlı bir sapma, gerekçesi orada belgelenir)."""


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


# ==============================================================================
# FILE: src/awe/domain/episode.py
# ==============================================================================
"""Episode Candidate modeli.

Family eşleştirmesine giren aday davranış birimi. İki kaynaktan üretilir: bir OSeries'in
tamamı (`FULL_CHUNK`) ya da farklı chunk/session'lar arasında bulunan, sıra-korumalı exact
ortak alt diziler (`COMMON_SUBSEQUENCE` — bkz. `awe.episodes.candidates` modül docstring'i).
Henüz habit kararı vermez — yalnızca Exact Base Family'nin girişidir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import EpisodeCandidateKind, ObservationStatus, ObservationTrigger
from awe.domain.tokens import BehaviorStep, Symbol


@dataclass(frozen=True, slots=True)
class EpisodeCandidate:
    candidate_id: str
    project_id: str
    subject_id: str
    session_id: str
    series_id: str
    """Kaynak OSeries'in `series_id`'si — izlenebilirlik."""

    kind: EpisodeCandidateKind
    steps: tuple[BehaviorStep, ...]
    step_indices: tuple[int, ...]
    """Kaynak OSeries.steps içindeki, `steps` ile aynı sırada karşılık gelen pozisyonlar
    (izlenebilirlik). `FULL_CHUNK` için ardışıktır (`0..len-1`); `COMMON_SUBSEQUENCE` için
    sıra korunur ama ardışık olması gerekmez (araya kaynak dizide eşleşmeyen adımlar
    girebilir)."""

    observed_at: datetime
    entry_trigger: ObservationTrigger
    has_shortcut_trigger: bool
    final_status: ObservationStatus

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(step.symbol for step in self.steps)

    @property
    def targets(self) -> tuple[str | None, ...]:
        return tuple(step.target for step in self.steps)


# ==============================================================================
# FILE: src/awe/domain/family.py
# ==============================================================================
"""Exact Base Family modeli (bölüm 6.5).

Eski tasarımdan farklı olarak fuzzy/ağırlıklı benzerlik yoktur: bir family tamamen aynı
`(action, effect, screen, mapping_version)` sembol dizisini paylaşan occurrence'ların kümesidir.
`screen` artık sembolün parçası olduğundan ve tolerans olmadığından ayrı bir "variant" veya
"core ilişki" kavramına gerek yoktur — bir family zaten tek bir exact dizidir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.tokens import Symbol


@dataclass
class BaseFamily:
    family_id: str
    project_id: str
    subject_id: str
    symbols: tuple[Symbol, ...]

    occurrence_ids: list[str] = field(default_factory=list)
    """Bu exact diziye sahip `EpisodeCandidate.candidate_id` referansları."""

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def support(self) -> int:
        return len(self.occurrence_ids)


# ==============================================================================
# FILE: src/awe/domain/habit.py
# ==============================================================================
"""Habit Evaluator'ın kanıt ve karar modelleri (bölüm 6.7).

Bilinçli olarak sade: regularity/entropy/lift gibi gelişmiş istatistikler burada yoktur
("Bu katman ... MVP dışında bırakılmıştır", bölüm 6.7). Değerlendirme, Base Family değil
`TargetVariant` seviyesinde yapılır (bölüm 6.6) — farklı hedefler kanıtlarını havuzlamaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import HabitDecision, ReasonCode


@dataclass(frozen=True, slots=True)
class StatusVector:
    success: int
    fail: int
    cancel: int
    unknown: int

    @property
    def total(self) -> int:
        return self.success + self.fail + self.cancel + self.unknown


@dataclass(frozen=True, slots=True)
class HabitEvidence:
    organic_occurrences: int
    """trigger=shortcut olan occurrence'lar hariç (bölüm 6.7, kısayol kullanımı organik kanıt
    sayılmaz — bkz. `ObservationTrigger.SHORTCUT` docstring'i)."""
    distinct_sessions: int
    distinct_days: int

    first_seen_at: datetime
    last_seen_at: datetime

    status_vector: StatusVector
    """Fail/cancel occurrence'lar sayımdan çıkarılmaz (bölüm 6.7) — yalnızca burada dağılım
    olarak kayıt altına alınır."""


@dataclass(frozen=True, slots=True)
class HabitAssessment:
    variant_id: str
    """Değerlendirilen `TargetVariant.variant_id`."""
    decision: HabitDecision
    evidence: HabitEvidence | None
    reason_codes: tuple[ReasonCode, ...] = ()


# ==============================================================================
# FILE: src/awe/domain/observation.py
# ==============================================================================
"""Canonical Observation modeli (bkz. AWE_MVP_TASARIMI_BAGIMSIZ_INCELEME.md bölüm 4).

Observation, müşteriye özel raw event'in Adapter tarafından üretilen, uygulamadan bağımsız
karşılığıdır. Aşağı katmanların hiçbiri bir daha müşterinin ham telemetry formatını görmez.
`role`, `widget`, `parameters`, `breaksEpisode`, `appVersion` kasıtlı olarak yoktur: bu alanlar
eski tasarımdan kalmıştı ve yeni sözleşme onları tanımıyor (bkz. bölüm 4, 9.10 dışı bırakılan
"online state" notları hariç).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import (
    ObservationEffect,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)


@dataclass(frozen=True, slots=True)
class ObservationQuality:
    """Adapter'ın canonicalization sırasında ürettiği veri kalitesi kanıtı (bölüm 6.1).

    `session_id` burada yer almaz: zorunlu bir alandır ve eksikse/boşsa event reddedilir
    (bölüm 6.1 "Zorunlu alan eksikse event reject edilir") — sentetik session_id üretme veya
    kısmi kabul yoktur."""

    has_screen: bool
    missing_target_field: bool = False
    """Raw payload'da `target` anahtarı hiç yoktu (bölüm 6.1: "target anahtarı yoksa
    MISSING_TARGET_FIELD üretilir"). `target=None` ile karıştırılmamalı: `target=None` "açıkça
    hedef yok" anlamına gelirken bu flag "hedef verisi bilinmiyor" anlamına gelir (bölüm 3, kural 6)."""
    invalid_duration: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Observation:
    event_id: str
    project_id: str
    subject_id: str
    session_id: str
    timestamp: datetime

    action: str
    source: ObservationSource
    trigger: ObservationTrigger
    effect: ObservationEffect
    status: ObservationStatus

    screen: str | None
    target: str | None
    """Hedef referansı. `None` = raw event'te `target` alanı açıkça `null` gönderildi ("açıkça
    hedef yok", bölüm 3 kural 6). Raw payload'da `target` anahtarı hiç yoksa değer yine `None`
    olur ama `quality.missing_target_field=True` ile işaretlenir ("hedef verisi bilinmiyor") —
    aşağı katmanlar bu ayrımı `quality` üzerinden okur, `target` tek başına bunu taşıyamaz."""
    duration_ms: int | None
    """Yalnızca audit amaçlı (bölüm 6.14, 9.9) — hiçbir karar bu alana bakmaz."""

    mapping_version: str = "unversioned"

    quality: ObservationQuality = field(default_factory=lambda: ObservationQuality(has_screen=False))


# ==============================================================================
# FILE: src/awe/domain/plan.py
# ==============================================================================
"""Anchor Resolver, Scope Projector, Destination Resolver ve Shortcut Intent Builder
çıktı modelleri (bölüm 6.9-6.12).

`FieldBinding`/çoklu-parametre kavramı kasıtlı olarak yoktur: yeni sözleşmede tek bir
skaler `target` alanı vardır, "workspace_1 + report_9" gibi compound identity taşınamaz
(bölüm 6.12) — bu durumda Intent `UNSUPPORTED` olur.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    AutomaticAction,
    FinalActionOwner,
    IntentState,
    PlanMode,
    ReasonCode,
)
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class ShortcutAnchor:
    symbol: Symbol
    position: int
    """TargetVariant'ın family sembol dizisi içindeki index — yalnızca açıklanabilirlik amaçlı."""
    strength: AnchorStrength
    status: AnchorStatus
    reason_codes: tuple[ReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class Scope:
    variant_id: str
    included: tuple[Symbol, ...]
    excluded_trailing: tuple[Symbol, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.included) == 0


@dataclass(frozen=True, slots=True)
class Destination:
    screen: str | None
    resolved: bool
    reason_codes: tuple[ReasonCode, ...] = ()


@dataclass(frozen=True, slots=True)
class ShortcutIntent:
    intent_id: str
    variant_id: str
    anchor: ShortcutAnchor

    state: IntentState
    mode: PlanMode | None
    destination_screen: str | None
    target: str | None
    requires_user_confirmation: bool
    automatic_action: AutomaticAction
    final_action_owner: FinalActionOwner

    supporting_occurrences: int
    reason_codes: tuple[ReasonCode, ...] = ()


# ==============================================================================
# FILE: src/awe/domain/risk.py
# ==============================================================================
"""Risk Evaluator'ın kanıt ve karar modelleri (bölüm 6.13).

Tek bir skor değil, açıklanabilir bir vektördür. Selector yalnızca `RiskDecision` kapısına
bakar (`ALLOW`/`BLOCK`); vektörün diğer alanları açıklanabilirlik ve loglama içindir.
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import EffectPolicy, ExecutionExposure, PlanMode, ReasonCode, RiskDecision


@dataclass(frozen=True, slots=True)
class ReliabilityEvidence:
    completion_rate: float
    failure_rate: float
    cancel_rate: float
    sample_size: int


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    policy: EffectPolicy
    """Anchor'ın effect'i için proje konfigürasyonunun tanımladığı güvenlik sınıfı."""
    plan_surface: PlanMode
    execution_exposure: ExecutionExposure
    interaction_guard_intact: bool
    """`automaticAction=NONE` ve `finalActionOwner=USER` koşulları sağlanıyor mu."""
    observed_goal_sensitivity: EffectPolicy
    """Scope içindeki adımların en hassas (en kısıtlayıcı) effect policy'si — yalnızca
    Anchor'ın kendi effect'i değil, oraya varan tüm gözlenen akış dikkate alınır."""
    reliability: ReliabilityEvidence
    data_quality_ok: bool


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    intent_id: str
    decision: RiskDecision
    evidence: RiskEvidence
    reason_codes: tuple[ReasonCode, ...] = ()


# ==============================================================================
# FILE: src/awe/domain/screen_evidence.py
# ==============================================================================
"""Screen Transition Evidence modeli (bölüm 6.8).

Bir ACTION sonrasında gözlenen opaque screen anahtarının session'lar arası tutarlılığını
toplar. Nedensellik kanıtlamaz, yalnızca korelasyon gösterir (bölüm 9.2).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ScreenEvidenceState
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class ScreenTransitionEvidence:
    symbol: Symbol
    """Kanıtın toplandığı ACTION sembolü (genellikle aday Anchor)."""
    state: ScreenEvidenceState
    screen: str | None
    """`STABLE` ise session'lar arası ortak ekran; aksi halde `None`."""
    supporting_sessions: int
    conflicting_screens: tuple[str, ...] = ()


# ==============================================================================
# FILE: src/awe/domain/series.py
# ==============================================================================
"""O-Series modeli: bir session içindeki tek structural chunk (bölüm 6.3).

Eski tasarımdan farklı olarak sınır, açık bir `breaksEpisode` bayrağı veya "completion effect"
tahminiyle değil; yalnızca (a) aynı timestamp'te birden fazla ACTION gözlenip sıra üretilemediği
"ambiguity barrier" anları ve (b) `navigation`/`notification`/`deeplink` tetikleyicili bir ACTION'ın
mevcut akışın ortasında gelmesiyle çizilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from awe.domain.enums import ObservationStatus, ObservationTrigger, OrderingConfidence
from awe.domain.observation import Observation
from awe.domain.tokens import BehaviorStep, Symbol


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
    """Ham Observation dizisi (CONTEXT/IGNORE dahil) — izlenebilirlik için korunur."""

    steps: tuple[BehaviorStep, ...]
    """Yalnız ACTION-classified adımlar, event-time sırasıyla. Normalizasyon/sıkıştırma yoktur
    (bölüm 6.4: "Fuzzy merge yoktur") — retry veya geri-navigasyon tekrarları olduğu gibi kalır."""

    entry_trigger: ObservationTrigger
    entry_screen: str | None
    has_shortcut_trigger: bool
    """Bu chunk bir shortcut tetiklemesiyle mi başladı — Habit'in organic-evidence dışlaması için."""

    final_status: ObservationStatus

    cut_by_ambiguity: bool
    """Bu chunk, aynı timestamp'te birden fazla ACTION gözlendiği için burada kesildi mi
    (bölüm 6.3 ambiguity barrier). Yalnızca açıklanabilirlik/log amaçlıdır."""

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(step.symbol for step in self.steps)

    @property
    def is_empty(self) -> bool:
        return len(self.steps) == 0


# ==============================================================================
# FILE: src/awe/domain/suggestion.py
# ==============================================================================
"""Selector çıktısı ve suggestion lifecycle modeli (bölüm 6.15).

`SELECTED`, "kullanıcıya gösterildi" değil, "gösterilmeye uygun aday" demektir — gösterim
zamanlaması, cooldown ve dismiss/revive akışı ayrı bir lifecycle katmanıdır (bölüm 9.11,
bu tasarımda tamamlanmamıştır; mevcut lifecycle mekanizması korunmuştur).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import ReasonCode, SelectionOutcome, SuggestionState


@dataclass(frozen=True, slots=True)
class SelectionResult:
    intent_id: str
    outcome: SelectionOutcome
    reason_codes: tuple[ReasonCode, ...] = ()


@dataclass
class Suggestion:
    """Bir `TargetVariant` en fazla bir Anchor (dolayısıyla en fazla bir Shortcut Intent)
    üretebildiği için (bölüm 6.9-6.12), eski tasarımdaki "fallback plan" kavramı yoktur —
    bir variant'ın tek intent'i vardır."""

    suggestion_id: str
    project_id: str
    subject_id: str
    family_id: str
    variant_id: str

    primary_intent_id: str

    state: SuggestionState
    reason_codes: tuple[ReasonCode, ...] = field(default_factory=tuple)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismiss_cooldown_until: datetime | None = None


# ==============================================================================
# FILE: src/awe/domain/target.py
# ==============================================================================
"""Target Resolver çıktı modeli (bölüm 6.6).

Bir Base Family, occurrence'larının target fingerprint'ine (her adımın gözlenen target'ı,
sırayla) göre alt kümelere bölünür. Her exact fingerprint ayrı bir `TargetVariant` olarak
Habit Evaluator'a gider — böylece örn. `course_42` ve `course_17` hedefleri aynı family
içinde görülse bile kanıtları havuzlanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from awe.domain.enums import TargetVariantKind

TargetFingerprint = tuple[str | None, ...]
"""Occurrence içindeki her adımın gözlenen target'ı, adım sırasına göre. `None` = o adımda
açıkça hedef yok (bkz. `Observation.target` semantiği)."""


@dataclass
class TargetVariant:
    variant_id: str
    family_id: str
    kind: TargetVariantKind
    fingerprint: TargetFingerprint

    occurrence_ids: list[str] = field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def support(self) -> int:
        return len(self.occurrence_ids)

    @property
    def single_target(self) -> str | None:
        """Fingerprint'teki tek, boş-olmayan hedef değeri — Shortcut Intent Builder'ın
        `target` alanı için kullanılır. Birden fazla farklı non-null değer varsa (compound
        identity, bölüm 6.12) `None` döner; çağıran bunu `UNSUPPORTED` olarak ele almalıdır."""
        distinct = {value for value in self.fingerprint if value}
        if len(distinct) == 1:
            return next(iter(distinct))
        return None


# ==============================================================================
# FILE: src/awe/domain/tokens.py
# ==============================================================================
"""Karşılaştırma için canonical davranış sembolü ve adım modeli.

Tasarım kararı (bölüm 6.4 Episode Candidate Builder, 6.5 Exact Base Family): karşılaştırma
sembolü `(actionKey, exact effect, opaque screen, mappingVersion)` dörtlüsüdür. Eski tasarımdan
farklı olarak `screen` artık sembolün bir parçasıdır — fuzzy/ağırlıklı benzerlik yoktur, yalnız
exact eşitlik vardır ("Fuzzy merge yoktur. Optional step toleransı yoktur.", bölüm 6.4). Bu,
precision'ı artırır ama varyasyonlu gerçek akışları parçalayabilir (bkz. bölüm 9.3 — bilinçli
kabul edilmiş bir ödünleşim, motor tarafında telafi edilmez).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ObservationEffect, ObservationStatus

Symbol = tuple[str, str, str | None, str]
"""(action, effect, screen, mapping_version) — Episode Candidate ve Exact Base Family
karşılaştırmasının atomik birimi."""


@dataclass(frozen=True, slots=True)
class BehaviorToken:
    action: str
    effect: ObservationEffect
    screen: str | None
    mapping_version: str

    @property
    def symbol(self) -> Symbol:
        return (self.action, self.effect.value, self.screen, self.mapping_version)


@dataclass(frozen=True, slots=True)
class BehaviorStep:
    """Bir ACTION-classified adım: karşılaştırma sembolü + hedef + izlenebilirlik."""

    token: BehaviorToken
    target: str | None
    target_unknown: bool
    """Kaynak Observation'ın `quality.missing_target_field` değeri — bu adımda target verisi
    hiç gönderilmemiş miydi (bölüm 3 kural 6). Target Resolver'ın `UNKNOWN_TARGET` kararı için
    gereklidir; `target=None` tek başına "açıkça yok" ile "bilinmiyor"u ayırt edemez."""
    status: ObservationStatus
    observation_index: int
    """Bu adımın ait olduğu ham Observation'ın chunk içindeki sırası (izlenebilirlik)."""

    @property
    def symbol(self) -> Symbol:
        return self.token.symbol


# ==============================================================================
# FILE: src/awe/episodes/__init__.py
# ==============================================================================
from awe.episodes.candidates import build_episode_candidates

__all__ = ["build_episode_candidates"]


# ==============================================================================
# FILE: src/awe/episodes/candidates.py
# ==============================================================================
"""Episode Candidate Builder: Exact Base Family eşleştirmesine giren aday davranış
birimlerini üretir. Henüz habit kararı vermez.

İki aday tipi çıkarılır:
1. Her `OSeries` (structural chunk) chunk'ın tamamı (`FULL_CHUNK`).
2. Farklı chunk'lar arasında bulunan, sıra-korumalı exact ortak alt diziler
   (`COMMON_SUBSEQUENCE`).

Step eşitliği `Symbol = (action, effect, screen, mapping_version)` tam eşitliğidir; bir
adımın DEĞERİNDE hiçbir tolerans yoktur (fuzzy/yaklaşık eşleşme yok). Ancak iki chunk
arasındaki ortak deseni ararken **ardışıklık (contiguity) zorunlu değildir** — sıra
korunduğu sürece araya, kaynak dizide eşleşmeyen adımlar girebilir (ör. bir bildirim
kontrolü, yanlış tıklama, retry). Bu kasıtlı bir tasarım kararıdır ve bölüm 6.4'ün
"Optional step toleransı yoktur" ifadesinden bilinçli bir sapmadır: gerçek event
loglarında kullanıcılar aynı davranışı neredeyse hiçbir zaman birebir aynı, kesintisiz
adım dizisiyle tekrar etmez; yalnızca ardışık ortak alt dize (substring) arayan bir
algoritma bu yüzden gerçek alışkanlıkları aşırı parçalar (bölüm 9.3'ün kabul ettiği
riskin, kullanım verisinde kabul edilemez boyuta ulaşması). Klasik "en uzun ortak alt
dizi" (LCS) problemidir — eşleşen her adım hâlâ tam (exact) değer eşitliği taşımalıdır,
yalnızca aralarındaki boşluk toleransı gevşetilmiştir; bu hâlâ fuzzy/yaklaşık bir
benzerlik skoru DEĞİLDİR.

Bir chunk çifti arasında birden fazla bağımsız ortak desen olabileceğinden (ör. iki farklı
alışkanlık aynı iki session'da da görülüyorsa), tek bir LCS bulunduktan sonra eşleşen
pozisyonlar her iki diziden de çıkarılır ve arama `min_symbols` altına düşene kadar
tekrarlanır ("iterative peeling").

Maksimum aday uzunluğu belgede kesinleştirilmemiş bir karardır ("Eski MVP'deki max=8
korunacaksa bu ayrıca sabitlenip test edilmelidir") — burada `EpisodeConfig.max_symbols`
(varsayılan 8) olarak sabitlenmiş ve konfigüre edilebilir bırakılmıştır.
"""

from __future__ import annotations

from awe.config.engine_config import EpisodeConfig
from awe.domain.enums import EpisodeCandidateKind, ObservationTrigger
from awe.domain.episode import EpisodeCandidate
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol


def _longest_common_subsequence_indices(
    left: tuple[Symbol, ...], right: tuple[Symbol, ...]
) -> tuple[list[int], list[int]]:
    """İki sembol dizisi arasında sıra-korumalı (ardışık olması gerekmeyen) TEK bir en uzun
    ortak alt diziyi (LCS) bulur. Eşit uzunlukta birden fazla aday varsa deterministik bir
    seçim yapılır (traceback eşitlikte her zaman `left`'te geriye gitmeyi tercih eder).
    Döner: `(left'teki eşleşen pozisyonlar, right'teki eşleşen pozisyonlar)` — ikisi de aynı
    uzunlukta ve sırayla birbirine karşılık gelir."""

    n, m = len(left), len(right)
    if n == 0 or m == 0:
        return [], []

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if left[i - 1] == right[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = dp[i - 1][j] if dp[i - 1][j] >= dp[i][j - 1] else dp[i][j - 1]

    left_indices: list[int] = []
    right_indices: list[int] = []
    i, j = n, m
    while i > 0 and j > 0:
        if left[i - 1] == right[j - 1]:
            left_indices.append(i - 1)
            right_indices.append(j - 1)
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    left_indices.reverse()
    right_indices.reverse()
    return left_indices, right_indices


def _iterative_common_subsequences(
    left: tuple[Symbol, ...], right: tuple[Symbol, ...], min_length: int
) -> list[tuple[list[int], list[int]]]:
    """`_longest_common_subsequence_indices`'i tekrarlı uygular: bulunan her LCS'in eşleşen
    pozisyonlarını her iki diziden de çıkarır (maskeler) ve kalan pozisyonlar üzerinde
    `min_length`'in altına düşene kadar tekrar arar. Bu, bir chunk çiftinin birden fazla
    bağımsız ortak deseni paylaşabildiği durumları yakalar."""

    results: list[tuple[list[int], list[int]]] = []
    left_active = list(range(len(left)))
    right_active = list(range(len(right)))

    while left_active and right_active:
        sub_left = tuple(left[i] for i in left_active)
        sub_right = tuple(right[j] for j in right_active)
        rel_left, rel_right = _longest_common_subsequence_indices(sub_left, sub_right)
        if len(rel_left) < min_length:
            break

        left_indices = [left_active[i] for i in rel_left]
        right_indices = [right_active[j] for j in rel_right]
        results.append((left_indices, right_indices))

        left_used = set(left_indices)
        right_used = set(right_indices)
        left_active = [i for i in left_active if i not in left_used]
        right_active = [j for j in right_active if j not in right_used]

    return results


def _candidate_from_indices(series: OSeries, indices: list[int], kind: EpisodeCandidateKind) -> EpisodeCandidate:
    steps = tuple(series.steps[i] for i in indices)
    first_observation = series.raw_observations[steps[0].observation_index]
    has_shortcut_trigger = any(
        series.raw_observations[step.observation_index].trigger == ObservationTrigger.SHORTCUT for step in steps
    )
    index_key = "-".join(str(i) for i in indices)
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:{kind.value}:{index_key}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=kind,
        steps=steps,
        step_indices=tuple(indices),
        observed_at=series.started_at,
        entry_trigger=first_observation.trigger,
        has_shortcut_trigger=has_shortcut_trigger,
        final_status=steps[-1].status,
    )


def build_episode_candidates(all_series: list[OSeries], config: EpisodeConfig) -> list[EpisodeCandidate]:
    candidates: list[EpisodeCandidate] = []
    seen_keys: set[tuple[str, tuple[int, ...]]] = set()

    for series in all_series:
        if len(series.steps) < config.min_symbols:
            continue
        indices = list(range(min(len(series.steps), config.max_symbols)))
        candidates.append(_candidate_from_indices(series, indices, EpisodeCandidateKind.FULL_CHUNK))
        # Bir common-subsequence karşılaştırması aynı pozisyon kümesini tekrar bulursa (iki
        # chunk baştan sona birebir aynıysa bu kaçınılmazdır), FULL_CHUNK adayıyla çakışan bir
        # kopya eklenmesin — aksi halde tek gerçek occurrence iki kez sayılır (bkz. Habit'in
        # organic_occurrences kanıtı).
        seen_keys.add((series.series_id, tuple(indices)))

    eligible = [series for series in all_series if len(series.steps) >= config.min_symbols]

    for a_idx in range(len(eligible)):
        series_a = eligible[a_idx]
        symbols_a = series_a.symbols
        for b_idx in range(a_idx + 1, len(eligible)):
            series_b = eligible[b_idx]
            symbols_b = series_b.symbols

            for left_indices, right_indices in _iterative_common_subsequences(
                symbols_a, symbols_b, config.min_symbols
            ):
                capped_left = left_indices[: config.max_symbols]
                capped_right = right_indices[: config.max_symbols]
                for series, indices in ((series_a, capped_left), (series_b, capped_right)):
                    key = (series.series_id, tuple(indices))
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    candidates.append(
                        _candidate_from_indices(series, indices, EpisodeCandidateKind.COMMON_SUBSEQUENCE)
                    )

    return candidates


# ==============================================================================
# FILE: src/awe/families/__init__.py
# ==============================================================================
from awe.families.matching import compute_family_id, group_into_families

__all__ = ["compute_family_id", "group_into_families"]


# ==============================================================================
# FILE: src/awe/families/matching.py
# ==============================================================================
"""Exact Base Family (bölüm 6.5): tamamen aynı yapısal izi taşıyan `EpisodeCandidate`'ları
aynı family'de toplar.

Eşitlik `Symbol = (action, effect, screen, mapping_version)` dizisinin tam eşitliğidir.
Fuzzy benzerlik, ağırlıklandırma, ambiguity marjı yoktur (bölüm 6.4: "Fuzzy merge yoktur")
— bu, eski tasarımın MATCH/VARIANT_MATCH/AMBIGUOUS/NO_MATCH karar sürecini tamamen ortadan
kaldırır: aynı exact dizi her zaman aynı family'ye gider, bu deterministik olarak dizinin
kendisinden türetilen `family_id` ile sağlanır (aday sırasından veya "önce kim geldi"den
bağımsız — bölüm 9.3'te kabul edilen fragmentation riskinin bilinçli karşılığıdır)."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from awe.domain.episode import EpisodeCandidate
from awe.domain.family import BaseFamily
from awe.domain.tokens import Symbol


def compute_family_id(project_id: str, subject_id: str, symbols: tuple[Symbol, ...]) -> str:
    serialized = "\x1e".join(
        f"{action}\x1f{effect}\x1f{screen or ''}\x1f{mapping_version}"
        for action, effect, screen, mapping_version in symbols
    )
    digest = hashlib.sha1(f"{project_id}\x1d{subject_id}\x1d{serialized}".encode()).hexdigest()[:16]
    return f"fam_{digest}"


def group_into_families(candidates: list[EpisodeCandidate]) -> list[BaseFamily]:
    if not candidates:
        return []

    project_id = candidates[0].project_id
    subject_id = candidates[0].subject_id

    grouped: dict[tuple[Symbol, ...], list[EpisodeCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.symbols].append(candidate)

    families: list[BaseFamily] = []
    for symbols, members in grouped.items():
        families.append(
            BaseFamily(
                family_id=compute_family_id(project_id, subject_id, symbols),
                project_id=project_id,
                subject_id=subject_id,
                symbols=symbols,
                occurrence_ids=[member.candidate_id for member in members],
            )
        )
    return families


# ==============================================================================
# FILE: src/awe/habit/__init__.py
# ==============================================================================
from awe.habit.assessment import evaluate_habit

__all__ = ["evaluate_habit"]


# ==============================================================================
# FILE: src/awe/habit/assessment.py
# ==============================================================================
"""Habit Evaluator (bölüm 6.7): tek görevi recurrence ölçmektir.

MVP kapısı: `distinct session >= 3 AND distinct calendar day >= 2`. Bu katman regularity/
entropy/lift gibi gelişmiş istatistikler kullanmaz — yalnızca hard count-based gate.

Kısayol tetiklemesiyle başlayan occurrence'lar organik kanıttan hariç tutulur (belgede yazılı
değil, bkz. `ObservationTrigger.SHORTCUT` docstring'i — kasıtlı bir superset koruması: aksi
halde bir kısayolun kendi kullanımı kendi önerisini besleyen bir döngü oluşturabilir)."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from awe.config.engine_config import HabitConfig
from awe.domain.enums import HabitDecision, ObservationStatus, ReasonCode
from awe.domain.episode import EpisodeCandidate
from awe.domain.habit import HabitAssessment, HabitEvidence, StatusVector
from awe.domain.target import TargetVariant


def evaluate_habit(
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
    timezone_name: str,
    config: HabitConfig,
) -> HabitAssessment:
    members = [candidates_by_id[occurrence_id] for occurrence_id in variant.occurrence_ids]
    organic = [candidate for candidate in members if not candidate.has_shortcut_trigger]

    if not organic:
        return HabitAssessment(
            variant_id=variant.variant_id,
            decision=HabitDecision.INSUFFICIENT_EVIDENCE,
            evidence=None,
            reason_codes=(ReasonCode.INSUFFICIENT_OCCURRENCES,),
        )

    tz = ZoneInfo(timezone_name)
    distinct_sessions = len({candidate.session_id for candidate in organic})
    distinct_days = len({candidate.observed_at.astimezone(tz).date() for candidate in organic})

    reason_codes: list[ReasonCode] = []
    if distinct_sessions < config.min_distinct_sessions:
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_SESSIONS)
    if distinct_days < config.min_distinct_days:
        reason_codes.append(ReasonCode.INSUFFICIENT_DISTINCT_DAYS)

    if reason_codes:
        return HabitAssessment(
            variant_id=variant.variant_id,
            decision=HabitDecision.INSUFFICIENT_EVIDENCE,
            evidence=None,
            reason_codes=tuple(reason_codes),
        )

    status_counts = dict.fromkeys(ObservationStatus, 0)
    for candidate in organic:
        status_counts[candidate.final_status] += 1

    evidence = HabitEvidence(
        organic_occurrences=len(organic),
        distinct_sessions=distinct_sessions,
        distinct_days=distinct_days,
        first_seen_at=min(candidate.observed_at for candidate in organic),
        last_seen_at=max(candidate.observed_at for candidate in organic),
        status_vector=StatusVector(
            success=status_counts[ObservationStatus.SUCCESS],
            fail=status_counts[ObservationStatus.FAIL],
            cancel=status_counts[ObservationStatus.CANCEL],
            unknown=status_counts[ObservationStatus.UNKNOWN],
        ),
    )
    return HabitAssessment(variant_id=variant.variant_id, decision=HabitDecision.HABIT_DETECTED, evidence=evidence)


# ==============================================================================
# FILE: src/awe/lifecycle/__init__.py
# ==============================================================================
from awe.lifecycle.transitions import dismiss, next_state_for_reanalysis

__all__ = ["dismiss", "next_state_for_reanalysis"]


# ==============================================================================
# FILE: src/awe/lifecycle/transitions.py
# ==============================================================================
"""Suggestion lifecycle geçişleri.

Bir suggestion DISMISSED durumundayken cooldown süresi dolar ve davranış organik olarak
tekrar etmeye devam ederse ACTIVE'e geri döner — dismiss kalıcı bir ret değil, geçici bir
bastırmadır. Cooldown süresi dolmuş ama organik kanıt de kaybolmuşsa DISMISSED'te kalır
(kullanıcı zaten reddetmişti, yeniden canlanmak için tekrar organik kullanım gerekir).

Bu katman yeni tasarımda ele alınmamıştır (bölüm 9.11: "bu tasarımda tamamlanmamıştır") —
mevcut, çalışan mekanizma korunmuş ve yalnızca girdi şekli yeni pipeline'a uyarlanmıştır.
Staleness artık Habit Evaluator'dan gelen bir `liveness` skoruna değil (bölüm 6.7 artık böyle
bir skor üretmiyor — "regularity/entropy/lift ... MVP dışında bırakılmıştır"), doğrudan
`HabitEvidence.last_seen_at` üzerinden bu katmanın kendi basit eşiğine dayanır.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from awe.config.engine_config import LifecycleConfig
from awe.domain.enums import HabitDecision, SuggestionState


def next_state_for_reanalysis(
    current_state: SuggestionState | None,
    dismiss_cooldown_until: datetime | None,
    habit_decision: HabitDecision,
    has_eligible_intent: bool,
    last_seen_at: datetime | None,
    now: datetime,
    config: LifecycleConfig,
) -> SuggestionState:
    if current_state == SuggestionState.DISMISSED:
        cooldown_expired = dismiss_cooldown_until is not None and now >= dismiss_cooldown_until
        if cooldown_expired and habit_decision == HabitDecision.HABIT_DETECTED and has_eligible_intent:
            return SuggestionState.ACTIVE
        return SuggestionState.DISMISSED

    if habit_decision != HabitDecision.HABIT_DETECTED or not has_eligible_intent:
        return SuggestionState.INVALIDATED if current_state is not None else SuggestionState.PENDING_EVIDENCE

    if last_seen_at is not None:
        days_since_last_seen = (now - last_seen_at).total_seconds() / 86400
        if days_since_last_seen > config.stale_after_days:
            return SuggestionState.STALE

    return SuggestionState.ACTIVE


def dismiss(now: datetime, config: LifecycleConfig) -> tuple[SuggestionState, datetime]:
    return SuggestionState.DISMISSED, now + timedelta(days=config.dismiss_cooldown_days)


# ==============================================================================
# FILE: src/awe/ordering/__init__.py
# ==============================================================================
from awe.ordering.order_session import group_by_session, order_session

__all__ = ["group_by_session", "order_session"]


# ==============================================================================
# FILE: src/awe/ordering/order_session.py
# ==============================================================================
"""Deterministik session içi sıralama (bölüm 6.3).

Bu modül yalnızca genel, sınıflandırmadan bağımsız sıralama + eşit-timestamp tespiti yapar.
Bir eşitliğin gerçek bir "ambiguity barrier" (yalnızca 2+ ACTION-classified event aynı
timestamp'i paylaştığında chunk'ı kesen sınır, bölüm 6.3) olup olmadığına O-Series Builder
karar verir — çünkü bu karar `classify_event` sonucunu bilmeyi gerektirir ve ordering
katmanı sınıflandırmayı tekrar hesaplamamalıdır.
"""

from __future__ import annotations

from collections import defaultdict

from awe.domain.enums import OrderingConfidence
from awe.domain.observation import Observation


def group_by_session(observations: list[Observation]) -> dict[str, list[Observation]]:
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.session_id].append(observation)
    return dict(grouped)


def order_session(observations: list[Observation]) -> tuple[list[Observation], OrderingConfidence]:
    """`(timestamp, event_id)` ile deterministik sıralar. `event_id` yalnızca determinizmi
    garanti eder — motor hiçbir zaman bir kaynak sıra numarası uydurmaz veya talep etmez.
    Eşit timestamp varsa `OrderingConfidence.LOW` döner (yalnızca bilgilendirme amaçlı; asıl
    ambiguity-barrier kararı O-Series Builder'da verilir)."""

    if not observations:
        return [], OrderingConfidence.HIGH

    ordered = sorted(observations, key=lambda o: (o.timestamp, o.event_id))
    has_ambiguous_tie = any(ordered[i].timestamp == ordered[i + 1].timestamp for i in range(len(ordered) - 1))
    confidence = OrderingConfidence.LOW if has_ambiguous_tie else OrderingConfidence.HIGH
    return ordered, confidence


# ==============================================================================
# FILE: src/awe/persistence/__init__.py
# ==============================================================================
from awe.persistence.database import create_database_engine, create_session_factory, session_scope
from awe.persistence.models import Base

__all__ = ["Base", "create_database_engine", "create_session_factory", "session_scope"]


# ==============================================================================
# FILE: src/awe/persistence/database.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/persistence/models.py
# ==============================================================================
"""SQLAlchemy şema tanımları.

Yalnızca portable tipler kullanılır (`String`, `Integer`, `Float`, `Boolean`, `UTCDateTime`,
`JSON`) — SQLite ve PostgreSQL arasında taşınabilirlik için Postgres'e özgü tipler kullanılmaz.

Mimari not: `series`/`episode_candidates`/`families`/`target_variants` için ayrı tablo YOKTUR.
Yeni tasarımda Family/TargetVariant kimlikleri deterministiktir (exact sembol dizisinden türetilen
hash, bkz. `awe.families.matching.compute_family_id`) — durumsal/artımlı bir varlık değil, saf bir
hesaplama görünümüdür. O-Series Builder ve Episode Candidate Builder her `analyze_subject`
çağrısında `observations` tablosundan sıfırdan yeniden hesaplanır (bölüm 9.10: "incremental
tutulması ... bu algoritma prototiplerinin dışında kalmıştır" — bu motor bilinçli olarak batch/
recompute modelindedir, artımlı state yönetimi bu MVP'nin kapsamı dışıdır). Yalnızca ham
`observations` ve kullanıcı etkileşimine bağlı `suggestions` durumu gerçekten kalıcıdır;
`habit_evaluations`/`shortcut_intents` her analiz çalışmasında tamamen yeniden yazılan bir
önbellektir (eski `replace_plan_candidates` deseniyle aynı, bkz. `awe.persistence.repository`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Integer, String, UniqueConstraint
from sqlalchemy import Index as SqlIndex
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


class EventConflictRecord(Base):
    """Aynı `(project_id, event_id)` farklı içerikle geldiğinde karantina kaydı (bölüm 6.3:
    "conflict quarantine edilir"). İkinci event reddedilir; bu tablo yalnızca denetim içindir."""

    __tablename__ = "event_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    first_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    conflicting_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (SqlIndex("ix_event_conflicts_project_event", "project_id", "event_id"),)


class ObservationRecord(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    action: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    effect: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)

    quality_has_screen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_missing_target_field: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_invalid_duration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("project_id", "event_id", name="uq_observations_project_event"),
        SqlIndex("ix_observations_subject_scope", "project_id", "subject_id", "session_id"),
    )


class HabitEvaluationRecord(Base):
    __tablename__ = "habit_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (SqlIndex("ix_habit_evaluations_subject_scope", "project_id", "subject_id"),)


class ShortcutIntentRecord(Base):
    __tablename__ = "shortcut_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intent_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False)

    anchor: Mapped[dict] = mapped_column(JSON, nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)

    state: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    destination_screen: Mapped[str | None] = mapped_column(String(256), nullable=True)
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    requires_user_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supporting_occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intent_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    risk_decision: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    benefit_observed_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    benefit_planned_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    selection_outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    selection_reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (SqlIndex("ix_shortcut_intents_subject_scope", "project_id", "subject_id"),)


class SuggestionRecord(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suggestion_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    family_key: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    primary_intent_key: Mapped[str] = mapped_column(String(160), nullable=False)

    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    dismiss_cooldown_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (SqlIndex("ix_suggestions_subject_scope", "project_id", "subject_id"),)


# ==============================================================================
# FILE: src/awe/persistence/repository.py
# ==============================================================================
"""Analiz pipeline'ının ihtiyaç duyduğu okuma/yazma işlemleri.

Bu katman iş kuralı içermez; yalnızca domain nesneleri ile veritabanı satırları arasında köprü
kurar. Motor batch/recompute modelindedir (bkz. `awe.persistence.models` modül docstring'i):
her `analyze_subject` çağrısı bir subject'in TÜM `observations`'ını okur ve Habit/Intent
sonuçlarını sıfırdan yeniden hesaplayıp `habit_evaluations`/`shortcut_intents` tablolarını
tamamen değiştirir (delete+reinsert). Yalnızca `suggestions` gerçek kalıcı state taşır
(dismiss/cooldown) ve bu yüzden upsert edilir, asla toptan silinmez.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from awe.domain.benefit import BenefitEvidence
from awe.domain.habit import HabitAssessment
from awe.domain.observation import Observation
from awe.domain.plan import Scope, ShortcutIntent
from awe.domain.risk import RiskAssessment
from awe.persistence.models import (
    EventConflictRecord,
    EventRecord,
    HabitEvaluationRecord,
    ObservationRecord,
    ShortcutIntentRecord,
    SuggestionRecord,
)
from awe.persistence.serialization import (
    anchor_to_dict,
    habit_evidence_to_dict,
    observation_to_record,
    reason_codes_to_list,
    record_to_observation,
    risk_evidence_to_dict,
    scope_to_dict,
)


def event_exists(session: Session, project_id: str, event_id: str) -> bool:
    stmt = select(EventRecord.id).where(EventRecord.project_id == project_id, EventRecord.event_id == event_id)
    return session.execute(stmt).first() is not None


def fetch_event_payload(session: Session, project_id: str, event_id: str) -> dict | None:
    stmt = select(EventRecord.raw_payload).where(
        EventRecord.project_id == project_id, EventRecord.event_id == event_id
    )
    row = session.execute(stmt).first()
    return row[0] if row is not None else None


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


def insert_event_conflict(
    session: Session,
    project_id: str,
    event_id: str,
    first_payload: dict,
    conflicting_payload: dict,
    detected_at: datetime,
) -> None:
    session.add(
        EventConflictRecord(
            project_id=project_id,
            event_id=event_id,
            first_payload=first_payload,
            conflicting_payload=conflicting_payload,
            detected_at=detected_at,
        )
    )


def insert_observation(session: Session, observation: Observation) -> ObservationRecord:
    record = observation_to_record(observation)
    session.add(record)
    session.flush()
    return record


def fetch_all_observations(session: Session, project_id: str, subject_id: str) -> list[Observation]:
    stmt = (
        select(ObservationRecord)
        .where(ObservationRecord.project_id == project_id, ObservationRecord.subject_id == subject_id)
        .order_by(ObservationRecord.timestamp)
    )
    records = session.execute(stmt).scalars().all()
    return [record_to_observation(record) for record in records]


def replace_habit_evaluations(
    session: Session,
    project_id: str,
    subject_id: str,
    assessments: list[HabitAssessment],
    family_key_by_variant: dict[str, str],
    now: datetime,
) -> None:
    session.query(HabitEvaluationRecord).filter(
        HabitEvaluationRecord.project_id == project_id, HabitEvaluationRecord.subject_id == subject_id
    ).delete(synchronize_session=False)

    for assessment in assessments:
        session.add(
            HabitEvaluationRecord(
                project_id=project_id,
                subject_id=subject_id,
                variant_key=assessment.variant_id,
                family_key=family_key_by_variant[assessment.variant_id],
                decision=assessment.decision.value,
                reason_codes=reason_codes_to_list(assessment.reason_codes),
                evidence=habit_evidence_to_dict(assessment.evidence) if assessment.evidence else None,
                evaluated_at=now,
            )
        )


def replace_shortcut_intents(
    session: Session,
    project_id: str,
    subject_id: str,
    entries: list[tuple[ShortcutIntent, Scope, str, RiskAssessment, BenefitEvidence, str, list[str]]],
    now: datetime,
) -> None:
    """`entries`: `(intent, scope, family_key, risk, benefit, selection_outcome, selection_reason_codes)`."""

    session.query(ShortcutIntentRecord).filter(
        ShortcutIntentRecord.project_id == project_id, ShortcutIntentRecord.subject_id == subject_id
    ).delete(synchronize_session=False)

    for intent, scope, family_key, risk, benefit, selection_outcome, selection_reasons in entries:
        session.add(
            ShortcutIntentRecord(
                intent_key=intent.intent_id,
                project_id=project_id,
                subject_id=subject_id,
                variant_key=intent.variant_id,
                family_key=family_key,
                anchor=anchor_to_dict(intent.anchor),
                scope=scope_to_dict(scope),
                state=intent.state.value,
                mode=intent.mode.value if intent.mode else None,
                destination_screen=intent.destination_screen,
                target=intent.target,
                requires_user_confirmation=intent.requires_user_confirmation,
                supporting_occurrences=intent.supporting_occurrences,
                intent_reason_codes=reason_codes_to_list(intent.reason_codes),
                risk_decision=risk.decision.value,
                risk_evidence=risk_evidence_to_dict(risk.evidence),
                risk_reason_codes=reason_codes_to_list(risk.reason_codes),
                benefit_observed_actions=benefit.observed_actions,
                benefit_planned_actions=benefit.planned_actions,
                selection_outcome=selection_outcome,
                selection_reason_codes=selection_reasons,
                evaluated_at=now,
            )
        )


def fetch_suggestion_by_variant(session: Session, variant_key: str) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.variant_key == variant_key)
    return session.execute(stmt).scalar_one_or_none()


def upsert_suggestion(
    session: Session,
    project_id: str,
    subject_id: str,
    family_key: str,
    variant_key: str,
    primary_intent_key: str,
    state: str,
    reason_codes: list[str],
    now: datetime,
    dismissed_at: datetime | None,
    dismiss_cooldown_until: datetime | None,
) -> SuggestionRecord:
    record = fetch_suggestion_by_variant(session, variant_key)
    if record is None:
        record = SuggestionRecord(
            suggestion_key=f"sug_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            subject_id=subject_id,
            family_key=family_key,
            variant_key=variant_key,
            created_at=now,
        )
        session.add(record)
    record.primary_intent_key = primary_intent_key
    record.state = state
    record.reason_codes = reason_codes
    record.updated_at = now
    record.dismissed_at = dismissed_at
    record.dismiss_cooldown_until = dismiss_cooldown_until
    session.flush()
    return record


def list_suggestions(
    session: Session, project_id: str, subject_id: str, states: set[str] | None = None
) -> list[SuggestionRecord]:
    stmt = select(SuggestionRecord).where(
        SuggestionRecord.project_id == project_id, SuggestionRecord.subject_id == subject_id
    )
    if states is not None:
        stmt = stmt.where(SuggestionRecord.state.in_(states))
    return list(session.execute(stmt).scalars().all())


def fetch_suggestion_by_key(session: Session, suggestion_key: str) -> SuggestionRecord | None:
    stmt = select(SuggestionRecord).where(SuggestionRecord.suggestion_key == suggestion_key)
    return session.execute(stmt).scalar_one_or_none()


def fetch_shortcut_intent_by_key(session: Session, intent_key: str) -> ShortcutIntentRecord | None:
    stmt = select(ShortcutIntentRecord).where(ShortcutIntentRecord.intent_key == intent_key)
    return session.execute(stmt).scalar_one_or_none()


# ==============================================================================
# FILE: src/awe/persistence/serialization.py
# ==============================================================================
"""Domain modelleri ile JSON-uyumlu sözlükler arasında dönüşüm.

Bu modül yalnızca veri şekli dönüşümü yapar; hiçbir iş kuralı içermez.
"""

from __future__ import annotations

from datetime import datetime

from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    EffectPolicy,
    ExecutionExposure,
    HabitDecision,
    ObservationEffect,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    PlanMode,
    ReasonCode,
    RiskDecision,
)
from awe.domain.habit import HabitEvidence, StatusVector
from awe.domain.observation import Observation, ObservationQuality
from awe.domain.plan import Scope, ShortcutAnchor
from awe.domain.risk import ReliabilityEvidence, RiskEvidence
from awe.domain.tokens import Symbol
from awe.persistence.models import ObservationRecord


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def observation_to_record(observation: Observation) -> ObservationRecord:
    return ObservationRecord(
        project_id=observation.project_id,
        subject_id=observation.subject_id,
        session_id=observation.session_id,
        event_id=observation.event_id,
        timestamp=observation.timestamp,
        action=observation.action,
        source=observation.source.value,
        effect=observation.effect.value,
        trigger=observation.trigger.value,
        status=observation.status.value,
        screen=observation.screen,
        target=observation.target,
        duration_ms=observation.duration_ms,
        mapping_version=observation.mapping_version,
        quality_has_screen=observation.quality.has_screen,
        quality_missing_target_field=observation.quality.missing_target_field,
        quality_invalid_duration=observation.quality.invalid_duration,
        quality_warnings=list(observation.quality.warnings),
    )


def record_to_observation(record: ObservationRecord) -> Observation:
    return Observation(
        event_id=record.event_id,
        project_id=record.project_id,
        subject_id=record.subject_id,
        session_id=record.session_id,
        timestamp=record.timestamp,
        action=record.action,
        source=ObservationSource(record.source),
        trigger=ObservationTrigger(record.trigger),
        effect=ObservationEffect(record.effect),
        status=ObservationStatus(record.status),
        screen=record.screen,
        target=record.target,
        duration_ms=record.duration_ms,
        mapping_version=record.mapping_version,
        quality=ObservationQuality(
            has_screen=record.quality_has_screen,
            missing_target_field=record.quality_missing_target_field,
            invalid_duration=record.quality_invalid_duration,
            warnings=tuple(record.quality_warnings),
        ),
    )


def reason_codes_to_list(codes: tuple[ReasonCode, ...]) -> list[str]:
    return [code.value for code in codes]


def list_to_reason_codes(values: list[str]) -> tuple[ReasonCode, ...]:
    return tuple(ReasonCode(value) for value in values)


def symbol_to_list(symbol: Symbol) -> list:
    return [symbol[0], symbol[1], symbol[2], symbol[3]]


def list_to_symbol(data: list) -> Symbol:
    return (data[0], data[1], data[2], data[3])


def habit_evidence_to_dict(evidence: HabitEvidence) -> dict:
    return {
        "organic_occurrences": evidence.organic_occurrences,
        "distinct_sessions": evidence.distinct_sessions,
        "distinct_days": evidence.distinct_days,
        "first_seen_at": _iso(evidence.first_seen_at),
        "last_seen_at": _iso(evidence.last_seen_at),
        "status_vector": {
            "success": evidence.status_vector.success,
            "fail": evidence.status_vector.fail,
            "cancel": evidence.status_vector.cancel,
            "unknown": evidence.status_vector.unknown,
        },
    }


def dict_to_habit_evidence(data: dict) -> HabitEvidence:
    status_vector = data["status_vector"]
    return HabitEvidence(
        organic_occurrences=data["organic_occurrences"],
        distinct_sessions=data["distinct_sessions"],
        distinct_days=data["distinct_days"],
        first_seen_at=datetime.fromisoformat(data["first_seen_at"]),
        last_seen_at=datetime.fromisoformat(data["last_seen_at"]),
        status_vector=StatusVector(
            success=status_vector["success"],
            fail=status_vector["fail"],
            cancel=status_vector["cancel"],
            unknown=status_vector["unknown"],
        ),
    )


def habit_decision_to_str(decision: HabitDecision) -> str:
    return decision.value


def str_to_habit_decision(value: str) -> HabitDecision:
    return HabitDecision(value)


def anchor_to_dict(anchor: ShortcutAnchor) -> dict:
    return {
        "symbol": symbol_to_list(anchor.symbol),
        "position": anchor.position,
        "strength": anchor.strength.value,
        "status": anchor.status.value,
        "reason_codes": reason_codes_to_list(anchor.reason_codes),
    }


def dict_to_anchor(data: dict) -> ShortcutAnchor:
    return ShortcutAnchor(
        symbol=list_to_symbol(data["symbol"]),
        position=data["position"],
        strength=AnchorStrength(data["strength"]),
        status=AnchorStatus(data["status"]),
        reason_codes=list_to_reason_codes(data["reason_codes"]),
    )


def scope_to_dict(scope: Scope) -> dict:
    return {
        "variant_id": scope.variant_id,
        "included": [symbol_to_list(symbol) for symbol in scope.included],
        "excluded_trailing": [symbol_to_list(symbol) for symbol in scope.excluded_trailing],
    }


def dict_to_scope(data: dict) -> Scope:
    return Scope(
        variant_id=data["variant_id"],
        included=tuple(list_to_symbol(symbol) for symbol in data["included"]),
        excluded_trailing=tuple(list_to_symbol(symbol) for symbol in data["excluded_trailing"]),
    )


def risk_evidence_to_dict(evidence: RiskEvidence) -> dict:
    return {
        "policy": evidence.policy.value,
        "plan_surface": evidence.plan_surface.value,
        "execution_exposure": evidence.execution_exposure.value,
        "interaction_guard_intact": evidence.interaction_guard_intact,
        "observed_goal_sensitivity": evidence.observed_goal_sensitivity.value,
        "reliability": {
            "completion_rate": evidence.reliability.completion_rate,
            "failure_rate": evidence.reliability.failure_rate,
            "cancel_rate": evidence.reliability.cancel_rate,
            "sample_size": evidence.reliability.sample_size,
        },
        "data_quality_ok": evidence.data_quality_ok,
    }


def dict_to_risk_evidence(data: dict) -> RiskEvidence:
    reliability = data["reliability"]
    return RiskEvidence(
        policy=EffectPolicy(data["policy"]),
        plan_surface=PlanMode(data["plan_surface"]),
        execution_exposure=ExecutionExposure(data["execution_exposure"]),
        interaction_guard_intact=data["interaction_guard_intact"],
        observed_goal_sensitivity=EffectPolicy(data["observed_goal_sensitivity"]),
        reliability=ReliabilityEvidence(
            completion_rate=reliability["completion_rate"],
            failure_rate=reliability["failure_rate"],
            cancel_rate=reliability["cancel_rate"],
            sample_size=reliability["sample_size"],
        ),
        data_quality_ok=data["data_quality_ok"],
    )


def risk_decision_to_str(decision: RiskDecision) -> str:
    return decision.value


def str_to_risk_decision(value: str) -> RiskDecision:
    return RiskDecision(value)


# ==============================================================================
# FILE: src/awe/persistence/types.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/planner/__init__.py
# ==============================================================================
from awe.planner.anchors import resolve_anchor
from awe.planner.destination import resolve_destination
from awe.planner.intent import build_shortcut_intent
from awe.planner.scope import project_scope

__all__ = ["resolve_anchor", "project_scope", "resolve_destination", "build_shortcut_intent"]


# ==============================================================================
# FILE: src/awe/planner/anchors.py
# ==============================================================================
"""Anchor Resolver (bölüm 6.9): tekrarlanan davranışın gözlenen amaç/son işlem noktasını bulur.
Shortcut değildir; yalnızca `HABIT_DETECTED` variant üzerinde çalışır.

Strength yorumu (belgenin üç kanıt kaynağından türetilmiştir, belge STRONG/MEDIUM ayrımını
formülle vermez): pozisyon exact target taşıyorsa `STRONG`; yalnızca outcome-evidence effect
taşıyorsa `MEDIUM`; yalnızca stable post-view kanıtından çözülmüşse `WEAK`.
"""

from __future__ import annotations

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    ObservationEffect,
    ObservationStatus,
    ReasonCode,
    ScreenEvidenceState,
    TargetVariantKind,
)
from awe.domain.episode import EpisodeCandidate
from awe.domain.plan import ShortcutAnchor
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol
from awe.screen_evidence import build_screen_transition_evidence

_OUTCOME_EVIDENCE_EFFECTS = frozenset(
    effect.value
    for effect in (
        ObservationEffect.SUBMIT,
        ObservationEffect.CREATE,
        ObservationEffect.DELETE,
        ObservationEffect.CONFIRM,
        ObservationEffect.UPDATE,
        ObservationEffect.TOGGLE,
        ObservationEffect.REQUEST,
        ObservationEffect.DOWNLOAD,
        ObservationEffect.SELECT,
        ObservationEffect.FILTER,
        ObservationEffect.SORT,
    )
)
ROUTE_OPEN_EFFECTS = frozenset(effect.value for effect in (ObservationEffect.ROUTE, ObservationEffect.OPEN))


def _occurrence_status_at(
    position: int, variant: TargetVariant, candidates_by_id: dict[str, EpisodeCandidate]
) -> AnchorStatus:
    any_success = any(
        candidates_by_id[occurrence_id].steps[position].status == ObservationStatus.SUCCESS
        for occurrence_id in variant.occurrence_ids
        if position < len(candidates_by_id[occurrence_id].steps)
    )
    return AnchorStatus.RESOLVED if any_success else AnchorStatus.ATTEMPT_ONLY


def resolve_anchor(
    family_symbols: tuple[Symbol, ...],
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    screen_evidence_config: ScreenEvidenceConfig,
) -> ShortcutAnchor:
    last_position = max(len(family_symbols) - 1, 0)
    fallback_symbol = family_symbols[-1] if family_symbols else ("", "", None, "")

    if variant.kind == TargetVariantKind.UNKNOWN_TARGET:
        return ShortcutAnchor(
            symbol=fallback_symbol,
            position=last_position,
            strength=AnchorStrength.WEAK,
            status=AnchorStatus.UNRESOLVED,
            reason_codes=(ReasonCode.UNKNOWN_TARGET_BLOCKS_ANCHOR,),
        )

    target_positions = {i for i in range(len(family_symbols)) if variant.fingerprint[i] is not None}
    outcome_positions = {i for i, symbol in enumerate(family_symbols) if symbol[1] in _OUTCOME_EVIDENCE_EFFECTS}
    strong_positions = target_positions | outcome_positions

    if strong_positions:
        position = max(strong_positions)
        strength = AnchorStrength.STRONG if position in target_positions else AnchorStrength.MEDIUM
        trailing = family_symbols[position + 1 :]
        trailing_is_route_open_only = bool(trailing) and all(
            symbol[1] in ROUTE_OPEN_EFFECTS for symbol in trailing
        )
        if trailing_is_route_open_only:
            return ShortcutAnchor(
                symbol=family_symbols[position],
                position=position,
                strength=strength,
                status=AnchorStatus.AMBIGUOUS,
                reason_codes=(ReasonCode.AMBIGUOUS_ANCHOR,),
            )
        status = _occurrence_status_at(position, variant, candidates_by_id)
        reasons = () if status == AnchorStatus.RESOLVED else (ReasonCode.ATTEMPT_ONLY,)
        return ShortcutAnchor(
            symbol=family_symbols[position],
            position=position,
            strength=strength,
            status=status,
            reason_codes=reasons,
        )

    all_route_open_only = bool(family_symbols) and all(
        symbol[1] in ROUTE_OPEN_EFFECTS for symbol in family_symbols
    )
    if all_route_open_only:
        evidence = build_screen_transition_evidence(
            variant,
            last_position,
            family_symbols[last_position],
            candidates_by_id,
            series_by_id,
            screen_evidence_config,
        )
        if evidence.state == ScreenEvidenceState.STABLE:
            status = _occurrence_status_at(last_position, variant, candidates_by_id)
            reasons = () if status == AnchorStatus.RESOLVED else (ReasonCode.ATTEMPT_ONLY,)
            return ShortcutAnchor(
                symbol=family_symbols[last_position],
                position=last_position,
                strength=AnchorStrength.WEAK,
                status=status,
                reason_codes=reasons,
            )

    return ShortcutAnchor(
        symbol=fallback_symbol,
        position=last_position,
        strength=AnchorStrength.WEAK,
        status=AnchorStatus.AMBIGUOUS,
        reason_codes=(ReasonCode.AMBIGUOUS_ANCHOR,),
    )


# ==============================================================================
# FILE: src/awe/planner/destination.py
# ==============================================================================
"""Destination Resolver (bölüm 6.11): tek görevi açılacak opaque `screen` anahtarını seçmektir.

`screen`, karşılaştırma sembolünün bir parçası olduğu için (bölüm 6.5) aynı family'nin tüm
üye occurrence'ları anchor pozisyonunda zaten aynı `screen` değerini paylaşır — action-surface
durumunda ayrı bir "representative screen" hesaplamaya gerek yoktur, sembolden doğrudan okunur.
"""

from __future__ import annotations

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import AnchorStatus, ObservationEffect, ReasonCode, ScreenEvidenceState
from awe.domain.episode import EpisodeCandidate
from awe.domain.plan import Destination, ShortcutAnchor
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.planner.anchors import ROUTE_OPEN_EFFECTS
from awe.screen_evidence import build_screen_transition_evidence

_ACTION_SURFACE_EFFECTS = frozenset(
    effect.value
    for effect in (
        ObservationEffect.SUBMIT,
        ObservationEffect.CREATE,
        ObservationEffect.DELETE,
        ObservationEffect.CONFIRM,
        ObservationEffect.UPDATE,
        ObservationEffect.TOGGLE,
        ObservationEffect.REQUEST,
        ObservationEffect.DOWNLOAD,
        ObservationEffect.INPUT,
        ObservationEffect.SELECT,
        ObservationEffect.FILTER,
        ObservationEffect.SORT,
        ObservationEffect.FOCUS,
    )
)

_UNRESOLVED = Destination(screen=None, resolved=False, reason_codes=(ReasonCode.DESTINATION_UNRESOLVED,))


def resolve_destination(
    anchor: ShortcutAnchor,
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: ScreenEvidenceConfig,
) -> Destination:
    if anchor.status not in (AnchorStatus.RESOLVED, AnchorStatus.ATTEMPT_ONLY):
        return _UNRESOLVED

    _action, effect, screen, _mapping_version = anchor.symbol

    if effect in ROUTE_OPEN_EFFECTS:
        evidence = build_screen_transition_evidence(
            variant, anchor.position, anchor.symbol, candidates_by_id, series_by_id, config
        )
        if evidence.state == ScreenEvidenceState.STABLE and evidence.screen:
            return Destination(screen=evidence.screen, resolved=True)
        return _UNRESOLVED

    if effect in _ACTION_SURFACE_EFFECTS:
        if screen:
            return Destination(screen=screen, resolved=True)
        return _UNRESOLVED

    return _UNRESOLVED


# ==============================================================================
# FILE: src/awe/planner/intent.py
# ==============================================================================
"""Shortcut Intent Builder (bölüm 6.12): yalnızca çözülmüş Habit + Anchor + Scope + Destination
sonucunu runtime sözleşmesine çevirir. `EXECUTE` modu yoktur.
"""

from __future__ import annotations

from awe.domain.enums import (
    AnchorStatus,
    AutomaticAction,
    FinalActionOwner,
    IntentState,
    PlanMode,
    ReasonCode,
    TargetVariantKind,
)
from awe.domain.plan import Destination, Scope, ShortcutAnchor, ShortcutIntent
from awe.domain.target import TargetVariant
from awe.planner.anchors import ROUTE_OPEN_EFFECTS


def _unsupported(
    variant: TargetVariant,
    anchor: ShortcutAnchor,
    destination_screen: str | None,
    reason_codes: tuple[ReasonCode, ...],
) -> ShortcutIntent:
    return ShortcutIntent(
        intent_id=f"{variant.variant_id}:{anchor.position}",
        variant_id=variant.variant_id,
        anchor=anchor,
        state=IntentState.UNSUPPORTED,
        mode=None,
        destination_screen=destination_screen,
        target=None,
        requires_user_confirmation=False,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=len(variant.occurrence_ids),
        reason_codes=reason_codes,
    )


def build_shortcut_intent(
    variant: TargetVariant, anchor: ShortcutAnchor, scope: Scope, destination: Destination
) -> ShortcutIntent:
    if anchor.status not in (AnchorStatus.RESOLVED, AnchorStatus.ATTEMPT_ONLY) or scope.is_empty:
        reasons = anchor.reason_codes or (ReasonCode.AMBIGUOUS_ANCHOR,)
        return _unsupported(variant, anchor, destination.screen, reasons)

    if not destination.resolved:
        return _unsupported(
            variant, anchor, None, destination.reason_codes or (ReasonCode.DESTINATION_UNRESOLVED,)
        )

    # Anchor'dan önceki ara adımlar yalnız route/open olabilir; başka bir ara effect varsa
    # generic screen+target sözleşmesi o adımı yeniden oluşturamaz (bölüm 6.12).
    intermediate = scope.included[:-1]
    if any(symbol[1] not in ROUTE_OPEN_EFFECTS for symbol in intermediate):
        return _unsupported(variant, anchor, destination.screen, (ReasonCode.UNREPRESENTED_INTERMEDIATE_ACTION,))

    if variant.kind == TargetVariantKind.VARIABLE_TARGET:
        return _unsupported(variant, anchor, destination.screen, (ReasonCode.UNSUPPORTED_COMPOUND_TARGET,))

    target = variant.single_target if variant.kind == TargetVariantKind.FIXED_TARGET else None
    mode = PlanMode.PREFILL if target is not None else PlanMode.NAVIGATE

    return ShortcutIntent(
        intent_id=f"{variant.variant_id}:{anchor.position}",
        variant_id=variant.variant_id,
        anchor=anchor,
        state=IntentState.READY,
        mode=mode,
        destination_screen=destination.screen,
        target=target,
        requires_user_confirmation=mode == PlanMode.PREFILL,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=len(variant.occurrence_ids),
    )


# ==============================================================================
# FILE: src/awe/planner/scope.py
# ==============================================================================
"""Scope Projector (bölüm 6.10): yeni davranış kararı vermez, Anchor çözülmüşse family
prefix'ini mekanik olarak keser. Anchor ambiguous/unresolved ise scope boş kalır."""

from __future__ import annotations

from awe.domain.enums import AnchorStatus
from awe.domain.plan import Scope, ShortcutAnchor
from awe.domain.tokens import Symbol

_PROJECTABLE_STATUSES = frozenset({AnchorStatus.RESOLVED, AnchorStatus.ATTEMPT_ONLY})


def project_scope(family_symbols: tuple[Symbol, ...], variant_id: str, anchor: ShortcutAnchor) -> Scope:
    if anchor.status not in _PROJECTABLE_STATUSES:
        return Scope(variant_id=variant_id, included=(), excluded_trailing=())

    included = family_symbols[: anchor.position + 1]
    excluded_trailing = family_symbols[anchor.position + 1 :]
    return Scope(variant_id=variant_id, included=included, excluded_trailing=excluded_trailing)


# ==============================================================================
# FILE: src/awe/risk/__init__.py
# ==============================================================================
from awe.risk.evaluation import evaluate_risk

__all__ = ["evaluate_risk"]


# ==============================================================================
# FILE: src/awe/risk/evaluation.py
# ==============================================================================
"""Risk Evaluator (bölüm 6.13): üretilen gerçek Shortcut Intent'i değerlendirir; Anchor
effect'ini otomatik çalıştırdığını varsaymaz. Çıktı tek bir skor değil, açıklanabilir bir
vektördür — Selector yalnızca `RiskDecision.ALLOW`/`BLOCK` kapısına bakar.

MVP kuralları (belgeden birebir): delete bağlamı BLOCK; unknown effect BLOCK; kritik quality
flag BLOCK; unknown anchor status BLOCK; fail/cancel karışımı `MIXED_OBSERVED_OUTCOMES` olarak
korunur ama tek başına BLOCK nedeni değildir. State-changing gözlenen akış, kısayol onu
execute etmediği sürece (ki hiçbir zaman etmez — EXECUTE modu yoktur) otomatik BLOCK edilmez.
"""

from __future__ import annotations

from awe.config.engine_config import RiskConfig
from awe.domain.enums import (
    AutomaticAction,
    EffectPolicy,
    ExecutionExposure,
    FinalActionOwner,
    ObservationEffect,
    ObservationStatus,
    PlanMode,
    ReasonCode,
    RiskDecision,
)
from awe.domain.episode import EpisodeCandidate
from awe.domain.plan import Scope, ShortcutIntent
from awe.domain.risk import ReliabilityEvidence, RiskAssessment, RiskEvidence
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol


def _reliability(
    variant: TargetVariant, anchor_position: int, candidates_by_id: dict[str, EpisodeCandidate]
) -> ReliabilityEvidence:
    statuses = [
        candidates_by_id[occurrence_id].steps[anchor_position].status
        for occurrence_id in variant.occurrence_ids
        if anchor_position < len(candidates_by_id[occurrence_id].steps)
    ]
    sample_size = len(statuses)
    if sample_size == 0:
        return ReliabilityEvidence(completion_rate=0.0, failure_rate=0.0, cancel_rate=0.0, sample_size=0)
    return ReliabilityEvidence(
        completion_rate=statuses.count(ObservationStatus.SUCCESS) / sample_size,
        failure_rate=statuses.count(ObservationStatus.FAIL) / sample_size,
        cancel_rate=statuses.count(ObservationStatus.CANCEL) / sample_size,
        sample_size=sample_size,
    )


def _scope_data_quality_ok(
    variant: TargetVariant,
    scope_length: int,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: RiskConfig,
) -> bool:
    total = 0
    clean = 0
    for occurrence_id in variant.occurrence_ids:
        candidate = candidates_by_id[occurrence_id]
        series = series_by_id[candidate.series_id]
        for step in candidate.steps[:scope_length]:
            observation = series.raw_observations[step.observation_index]
            total += 1
            if (
                not observation.quality.missing_target_field
                and not observation.quality.invalid_duration
                and not observation.quality.warnings
            ):
                clean += 1
    if total == 0:
        return True
    return (clean / total) >= config.min_data_quality_for_allow


def _policy_of(symbol: Symbol, config: RiskConfig) -> EffectPolicy:
    return config.effect_policy.get(ObservationEffect(symbol[1]), EffectPolicy.SENSITIVE)


def _observed_goal_sensitivity(excluded_trailing: tuple[Symbol, ...], config: RiskConfig) -> EffectPolicy:
    """Anchor'dan SONRA gözlenen ama Scope'a (dolayısıyla kısayola) dahil OLMAYAN adımların en
    hassas policy'si — yalnızca açıklanabilirlik: kısayolun neyi kasıtlı olarak dışarıda
    bıraktığını gösterir, kendisi bir BLOCK nedeni değildir."""
    if not excluded_trailing:
        return EffectPolicy.SAFE
    policies = [_policy_of(symbol, config) for symbol in excluded_trailing]
    if EffectPolicy.BLOCKED in policies:
        return EffectPolicy.BLOCKED
    if EffectPolicy.SENSITIVE in policies:
        return EffectPolicy.SENSITIVE
    return EffectPolicy.SAFE


def evaluate_risk(
    intent: ShortcutIntent,
    variant: TargetVariant,
    scope: Scope,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: RiskConfig,
) -> RiskAssessment:
    anchor_effect = intent.anchor.symbol[1]
    anchor_policy = _policy_of(intent.anchor.symbol, config)
    reliability = _reliability(variant, intent.anchor.position, candidates_by_id)
    data_quality_ok = _scope_data_quality_ok(variant, len(scope.included), candidates_by_id, series_by_id, config)
    goal_sensitivity = _observed_goal_sensitivity(scope.excluded_trailing, config)

    reason_codes: list[ReasonCode] = []
    decision = RiskDecision.ALLOW

    if anchor_policy == EffectPolicy.BLOCKED:
        decision = RiskDecision.BLOCK
        is_unknown_effect = anchor_effect == ObservationEffect.UNKNOWN.value
        reason_codes.append(ReasonCode.UNKNOWN_EFFECT if is_unknown_effect else ReasonCode.EXECUTE_BLOCKED_EFFECT)

    if not data_quality_ok:
        decision = RiskDecision.BLOCK
        reason_codes.append(ReasonCode.CRITICAL_QUALITY_FLAG)

    all_unknown_status = (
        reliability.sample_size > 0
        and reliability.completion_rate == 0.0
        and reliability.failure_rate == 0.0
        and reliability.cancel_rate == 0.0
    )
    if all_unknown_status:
        decision = RiskDecision.BLOCK
        reason_codes.append(ReasonCode.UNKNOWN_ANCHOR_STATUS)

    if (
        reliability.failure_rate > config.mixed_outcome_rate_threshold
        or reliability.cancel_rate > config.mixed_outcome_rate_threshold
    ):
        reason_codes.append(ReasonCode.MIXED_OBSERVED_OUTCOMES)

    evidence = RiskEvidence(
        policy=anchor_policy,
        plan_surface=intent.mode if intent.mode is not None else PlanMode.NAVIGATE,
        execution_exposure=ExecutionExposure.NONE,
        interaction_guard_intact=intent.automatic_action == AutomaticAction.NONE
        and intent.final_action_owner == FinalActionOwner.USER,
        observed_goal_sensitivity=goal_sensitivity,
        reliability=reliability,
        data_quality_ok=data_quality_ok,
    )
    return RiskAssessment(
        intent_id=intent.intent_id,
        decision=decision,
        evidence=evidence,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


# ==============================================================================
# FILE: src/awe/screen_evidence/__init__.py
# ==============================================================================
from awe.screen_evidence.evidence import build_screen_transition_evidence

__all__ = ["build_screen_transition_evidence"]


# ==============================================================================
# FILE: src/awe/screen_evidence/evidence.py
# ==============================================================================
"""Screen Transition Evidence (bölüm 6.8): bir ACTION sonrasında gözlenen opaque screen
anahtarını toplar. Bu katman ekranın semantik anlamını bulmaz; nedensellik kanıtlamaz,
yalnızca korelasyon gösterir (bölüm 9.2).

Pipeline sırasında Anchor Resolver'dan ÖNCE gelir (bölüm 5) — bir `ShortcutAnchor` tüketmez,
tam tersine Anchor Resolver'ın aday pozisyonlar için danıştığı bir kanıt kaynağıdır. Bu yüzden
girdi bir sembol pozisyonudur, çözülmüş bir anchor değil.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import ObservationEffect, ObservationStatus, ScreenEvidenceState
from awe.domain.episode import EpisodeCandidate
from awe.domain.screen_evidence import ScreenTransitionEvidence
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class _OccurrenceScreenResult:
    screen: str | None
    ambiguous: bool


def _occurrence_post_view_screen(
    candidate: EpisodeCandidate, series: OSeries, position: int
) -> _OccurrenceScreenResult:
    anchor_step = candidate.steps[position]
    if anchor_step.status != ObservationStatus.SUCCESS:
        return _OccurrenceScreenResult(screen=None, ambiguous=False)

    anchor_obs_index = anchor_step.observation_index
    anchor_timestamp = series.raw_observations[anchor_obs_index].timestamp

    next_action_timestamp = None
    if position + 1 < len(candidate.steps):
        next_index = candidate.steps[position + 1].observation_index
        next_action_timestamp = series.raw_observations[next_index].timestamp

    screens: set[str] = set()
    for obs in series.raw_observations[anchor_obs_index + 1 :]:
        if obs.timestamp <= anchor_timestamp:
            continue
        if next_action_timestamp is not None and obs.timestamp >= next_action_timestamp:
            break
        if obs.effect == ObservationEffect.VIEW and obs.screen:
            screens.add(obs.screen)

    if not screens:
        return _OccurrenceScreenResult(screen=None, ambiguous=False)
    if len(screens) > 1:
        return _OccurrenceScreenResult(screen=None, ambiguous=True)
    return _OccurrenceScreenResult(screen=next(iter(screens)), ambiguous=False)


def build_screen_transition_evidence(
    variant: TargetVariant,
    position: int,
    symbol: Symbol,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: ScreenEvidenceConfig,
) -> ScreenTransitionEvidence:
    session_screens: dict[str, str] = {}
    conflicting_sessions: set[str] = set()

    for occurrence_id in variant.occurrence_ids:
        candidate = candidates_by_id[occurrence_id]
        if position >= len(candidate.steps):
            continue
        series = series_by_id[candidate.series_id]
        result = _occurrence_post_view_screen(candidate, series, position)

        if result.ambiguous:
            conflicting_sessions.add(candidate.session_id)
            continue
        if result.screen is None:
            continue

        existing = session_screens.get(candidate.session_id)
        if existing is not None and existing != result.screen:
            conflicting_sessions.add(candidate.session_id)
        else:
            session_screens[candidate.session_id] = result.screen

    screen_counts = Counter(session_screens.values())

    if conflicting_sessions or len(screen_counts) > 1:
        return ScreenTransitionEvidence(
            symbol=symbol,
            state=ScreenEvidenceState.CONFLICTING,
            screen=None,
            supporting_sessions=sum(screen_counts.values()),
            conflicting_screens=tuple(sorted(screen_counts)),
        )

    if not screen_counts:
        return ScreenTransitionEvidence(
            symbol=symbol, state=ScreenEvidenceState.INSUFFICIENT, screen=None, supporting_sessions=0
        )

    ((screen, supporting_sessions),) = screen_counts.items()
    if supporting_sessions >= config.min_supporting_sessions:
        return ScreenTransitionEvidence(
            symbol=symbol,
            state=ScreenEvidenceState.STABLE,
            screen=screen,
            supporting_sessions=supporting_sessions,
        )
    return ScreenTransitionEvidence(
        symbol=symbol,
        state=ScreenEvidenceState.INSUFFICIENT,
        screen=None,
        supporting_sessions=supporting_sessions,
    )


# ==============================================================================
# FILE: src/awe/selection/__init__.py
# ==============================================================================
from awe.selection.selector import Candidate, select

__all__ = ["Candidate", "select"]


# ==============================================================================
# FILE: src/awe/selection/selector.py
# ==============================================================================
"""Selector (bölüm 6.15): upstream kararları tekrar hesaplamaz, tek final skor üretmez.

MVP yüksek-precision politikası nedeniyle `LIMITED` dahil `CLEAR` dışındaki Benefit seviyeleri
reddedilir. Weak Anchor yalnızca mode=NAVIGATE + Risk=ALLOW + Benefit=CLEAR koşullarının
tamamında eligible olabilir (bir WEAK anchor, target taşıyan hiçbir pozisyon olmadığı için
zaten yalnızca NAVIGATE üretebilir — bkz. `awe.planner.anchors` — bu kontrol savunma amaçlıdır).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    BenefitLevel,
    HabitDecision,
    IntentState,
    PlanMode,
    ReasonCode,
    RiskDecision,
    SelectionOutcome,
)
from awe.domain.habit import HabitAssessment
from awe.domain.plan import Scope, ShortcutIntent
from awe.domain.risk import RiskAssessment
from awe.domain.suggestion import SelectionResult

_STRENGTH_RANK = {AnchorStrength.STRONG: 2, AnchorStrength.MEDIUM: 1, AnchorStrength.WEAK: 0}


@dataclass(frozen=True, slots=True)
class Candidate:
    """Selector'ın işlediği tek birim: bir intent'in tüm upstream sonuçlarıyla birlikte hali."""

    intent: ShortcutIntent
    scope: Scope
    habit: HabitAssessment
    risk: RiskAssessment
    benefit: BenefitEvidence


def _is_eligible(candidate: Candidate) -> bool:
    if candidate.habit.decision != HabitDecision.HABIT_DETECTED or candidate.habit.evidence is None:
        return False
    if candidate.intent.state != IntentState.READY:
        return False
    if candidate.intent.anchor.status != AnchorStatus.RESOLVED:
        return False
    if candidate.risk.decision != RiskDecision.ALLOW:
        return False
    if candidate.benefit.level != BenefitLevel.CLEAR:
        return False
    if candidate.intent.anchor.strength == AnchorStrength.WEAK:
        return candidate.intent.mode == PlanMode.NAVIGATE
    return True


def _dedupe_key(candidate: Candidate, project_id: str, subject_id: str) -> tuple:
    mapping_versions = frozenset(symbol[3] for symbol in candidate.scope.included)
    intent = candidate.intent
    return (
        project_id,
        subject_id,
        mapping_versions,
        intent.mode,
        intent.destination_screen,
        intent.target,
        intent.requires_user_confirmation,
        intent.automatic_action,
        intent.final_action_owner,
    )


def _ranking_key(candidate: Candidate) -> tuple:
    evidence = candidate.habit.evidence
    assert evidence is not None  # eligibility already guarantees this
    return (
        -_STRENGTH_RANK[candidate.intent.anchor.strength],
        -candidate.benefit.saved_actions,
        -evidence.distinct_days,
        -evidence.distinct_sessions,
        -candidate.intent.supporting_occurrences,
        candidate.intent.intent_id,
    )


def select(candidates: list[Candidate], project_id: str, subject_id: str) -> list[SelectionResult]:
    results: list[SelectionResult] = []
    dedupe_groups: dict[tuple, list[Candidate]] = defaultdict(list)

    for candidate in candidates:
        if not _is_eligible(candidate):
            reasons = (
                candidate.risk.reason_codes or candidate.intent.reason_codes or (ReasonCode.NO_PLAN_CANDIDATE,)
            )
            results.append(
                SelectionResult(
                    intent_id=candidate.intent.intent_id, outcome=SelectionOutcome.REJECTED, reason_codes=reasons
                )
            )
            continue
        dedupe_groups[_dedupe_key(candidate, project_id, subject_id)].append(candidate)

    for group in dedupe_groups.values():
        ranked = sorted(group, key=_ranking_key)
        winner = ranked[0]
        results.append(SelectionResult(intent_id=winner.intent.intent_id, outcome=SelectionOutcome.SELECTED))
        for loser in ranked[1:]:
            results.append(
                SelectionResult(
                    intent_id=loser.intent.intent_id,
                    outcome=SelectionOutcome.DEDUPED,
                    reason_codes=(ReasonCode.DUPLICATE_PLAN,),
                )
            )

    return results


# ==============================================================================
# FILE: src/awe/series/__init__.py
# ==============================================================================
from awe.series.extraction import extract_series

__all__ = ["extract_series"]


# ==============================================================================
# FILE: src/awe/series/extraction.py
# ==============================================================================
"""O-Series Builder: bir session'ın sıralı Observation akışını structural chunk'lara böler
(bölüm 6.3). Henüz Family/Habit/Risk/Benefit hesaplamaz.

Eski tasarımdan farklı olarak sınır `breaksEpisode` bayrağı ya da "completion effect" tahmini
değildir (bu alanlar artık yok). Yalnızca iki yapısal kural chunk sınırı çizer:
1. Aynı timestamp'te 2+ ACTION-classified event varsa sıra üretilmez — bu grup hiçbir chunk'ın
   step dizisine girmez (yalnızca trailing raw kanıt olarak korunur), mevcut chunk kesilir.
2. `navigation`/`notification`/`deeplink` tetikleyicili bir ACTION, mevcut chunk zaten en az
   bir step içeriyorsa (yani "akışın ortasında" geliyorsa) yeni bir chunk başlatır; kendisi
   yeni chunk'ın giriş adımı olur.

Retry/detour sıkıştırması kasıtlı olarak yoktur (bölüm 6.4: "Fuzzy merge yoktur") — tekrarlanan
adımlar veya geri-navigasyonlar olduğu gibi kalır; bu, exact family fragmentation riskini
(bölüm 9.3) motor tarafında telafi etmeden kabul eden bilinçli bir tasarım kararıdır.
"""

from __future__ import annotations

from awe.adapter.classification import classify_event
from awe.domain.enums import EventClassification, ObservationTrigger, OrderingConfidence
from awe.domain.observation import Observation
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken

_CHUNK_STARTING_TRIGGERS = frozenset(
    {ObservationTrigger.NAVIGATION, ObservationTrigger.NOTIFICATION, ObservationTrigger.DEEPLINK}
)

_ChunkEntry = tuple[Observation, bool]
"""(observation, excluded_from_steps). `excluded_from_steps=True`, bu event'in bir ambiguity
grubunun parçası olduğu ve hiçbir chunk'ın step dizisine giremeyeceği anlamına gelir."""


def extract_series(
    ordered_observations: list[Observation], ordering_confidence: OrderingConfidence
) -> list[OSeries]:
    if not ordered_observations:
        return []

    project_id = ordered_observations[0].project_id
    subject_id = ordered_observations[0].subject_id
    session_id = ordered_observations[0].session_id

    timestamp_groups: list[list[Observation]] = []
    for obs in ordered_observations:
        if timestamp_groups and timestamp_groups[-1][0].timestamp == obs.timestamp:
            timestamp_groups[-1].append(obs)
        else:
            timestamp_groups.append([obs])

    chunks: list[list[_ChunkEntry]] = [[]]
    cut_by_ambiguity: list[bool] = [False]
    chunk_has_step = False

    for group in timestamp_groups:
        action_members = [o for o in group if classify_event(o) == EventClassification.ACTION]

        if len(action_members) >= 2:
            chunks[-1].extend((o, True) for o in group)
            cut_by_ambiguity[-1] = True
            chunks.append([])
            cut_by_ambiguity.append(False)
            chunk_has_step = False
            continue

        action_obs = action_members[0] if action_members else None
        if action_obs is not None and chunk_has_step and action_obs.trigger in _CHUNK_STARTING_TRIGGERS:
            chunks.append([])
            cut_by_ambiguity.append(False)
            chunk_has_step = False

        chunks[-1].extend((o, False) for o in group)
        if action_obs is not None:
            chunk_has_step = True

    series_list: list[OSeries] = []
    for entries, was_cut in zip(chunks, cut_by_ambiguity, strict=True):
        if not entries:
            continue
        series_list.append(_build_chunk(entries, project_id, subject_id, session_id, ordering_confidence, was_cut))
    return series_list


def _build_chunk(
    entries: list[_ChunkEntry],
    project_id: str,
    subject_id: str,
    session_id: str,
    ordering_confidence: OrderingConfidence,
    cut_by_ambiguity: bool,
) -> OSeries:
    observations = [obs for obs, _excluded in entries]

    steps: list[BehaviorStep] = []
    for index, (obs, excluded) in enumerate(entries):
        if excluded or classify_event(obs) != EventClassification.ACTION:
            continue
        token = BehaviorToken(
            action=obs.action, effect=obs.effect, screen=obs.screen, mapping_version=obs.mapping_version
        )
        steps.append(
            BehaviorStep(
                token=token,
                target=obs.target,
                target_unknown=obs.quality.missing_target_field,
                status=obs.status,
                observation_index=index,
            )
        )

    first, last = observations[0], observations[-1]
    entry_obs = next(
        (obs for obs, excluded in entries if not excluded and classify_event(obs) == EventClassification.ACTION),
        first,
    )

    return OSeries(
        series_id=f"{session_id}#{first.event_id}",
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        started_at=first.timestamp,
        ended_at=last.timestamp,
        ordering_confidence=ordering_confidence,
        raw_observations=tuple(observations),
        steps=tuple(steps),
        entry_trigger=entry_obs.trigger,
        entry_screen=entry_obs.screen,
        has_shortcut_trigger=any(obs.trigger == ObservationTrigger.SHORTCUT for obs in observations),
        final_status=last.status,
        cut_by_ambiguity=cut_by_ambiguity,
    )


# ==============================================================================
# FILE: src/awe/services/__init__.py
# ==============================================================================
from awe.services.analysis import AnalysisSummary, VariantAnalysisSummary, analyze_subject
from awe.services.ingestion import IngestOutcome, ingest_batch, ingest_event
from awe.services.suggestions import (
    IntentView,
    SuggestionView,
    dismiss_suggestion,
    list_subject_suggestions,
)

__all__ = [
    "analyze_subject",
    "AnalysisSummary",
    "VariantAnalysisSummary",
    "ingest_event",
    "ingest_batch",
    "IngestOutcome",
    "list_subject_suggestions",
    "dismiss_suggestion",
    "SuggestionView",
    "IntentView",
]


# ==============================================================================
# FILE: src/awe/services/analysis.py
# ==============================================================================
"""Subject analizi: pipeline'ın tamamını (O-Series Builder → ... → Selector) uçtan uca bağlar.

Motor batch/recompute modelindedir (bkz. `awe.persistence.models` modül docstring'i, bölüm
9.10): her `analyze_subject` çağrısı, subject'in TÜM `observations`'ını okuyup O-Series →
Episode Candidate → Exact Base Family → Target Resolver → Habit → (Anchor → Scope →
Destination → Shortcut Intent → Risk → Benefit) → Selector zincirini sıfırdan çalıştırır.
Family/TargetVariant kimlikleri deterministik olduğundan (exact sembol dizisinden türetilir)
bu artımlı bir state güncellemesi değil, saf bir yeniden hesaplamadır. Yalnızca `suggestions`
tablosu (dismiss/cooldown) gerçek kalıcı state taşır ve bu yüzden upsert edilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.benefit import evaluate_benefit
from awe.config import EngineConfig, ProjectConfig, log_event
from awe.config.engine_config import LifecycleConfig
from awe.domain.enums import (
    BenefitLevel,
    HabitDecision,
    IntentState,
    ReasonCode,
    RiskDecision,
    SelectionOutcome,
    SuggestionState,
)
from awe.domain.episode import EpisodeCandidate
from awe.domain.family import BaseFamily
from awe.domain.habit import HabitAssessment
from awe.domain.series import OSeries
from awe.episodes import build_episode_candidates
from awe.families import group_into_families
from awe.habit import evaluate_habit
from awe.lifecycle import next_state_for_reanalysis
from awe.ordering import group_by_session, order_session
from awe.persistence.repository import (
    fetch_all_observations,
    fetch_suggestion_by_variant,
    replace_habit_evaluations,
    replace_shortcut_intents,
    upsert_suggestion,
)
from awe.persistence.serialization import reason_codes_to_list
from awe.planner import build_shortcut_intent, project_scope, resolve_anchor, resolve_destination
from awe.risk import evaluate_risk
from awe.selection import Candidate, select
from awe.series import extract_series
from awe.targeting import resolve_targets


@dataclass(frozen=True, slots=True)
class VariantAnalysisSummary:
    variant_key: str
    habit_decision: HabitDecision
    suggestion_state: SuggestionState | None


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    project_id: str
    subject_id: str
    series_count: int
    variants: list[VariantAnalysisSummary]


def _extract_all_series(session: Session, project_id: str, subject_id: str) -> list[OSeries]:
    observations = fetch_all_observations(session, project_id, subject_id)
    all_series: list[OSeries] = []
    for _session_id, session_observations in group_by_session(observations).items():
        ordered, confidence = order_session(session_observations)
        all_series.extend(extract_series(ordered, confidence))
    return all_series


def _evaluate_variant(
    variant,
    family: BaseFamily,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    engine_config: EngineConfig,
    project_id: str,
    subject_id: str,
) -> tuple[HabitAssessment, Candidate | None]:
    assessment = evaluate_habit(variant, candidates_by_id, engine_config.timezone, engine_config.habit)
    if assessment.decision != HabitDecision.HABIT_DETECTED:
        log_event("habit_pending", project_id=project_id, subject_id=subject_id, variant_key=variant.variant_id)
        return assessment, None

    log_event("habit_detected", project_id=project_id, subject_id=subject_id, variant_key=variant.variant_id)

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, engine_config.screen_evidence)
    scope = project_scope(family.symbols, variant.variant_id, anchor)
    destination = resolve_destination(
        anchor, variant, candidates_by_id, series_by_id, engine_config.screen_evidence
    )
    intent = build_shortcut_intent(variant, anchor, scope, destination)

    if intent.state != IntentState.READY:
        log_event(
            "intent_unsupported",
            project_id=project_id,
            subject_id=subject_id,
            variant_key=variant.variant_id,
            reasons=reason_codes_to_list(intent.reason_codes),
        )
        return assessment, None

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, engine_config.risk)
    if risk.decision == RiskDecision.BLOCK:
        log_event("risk_blocked", project_id=project_id, subject_id=subject_id, intent_key=intent.intent_id)

    benefit = evaluate_benefit(intent, len(scope.included))
    if benefit.level != BenefitLevel.CLEAR:
        log_event(
            "benefit_rejected",
            project_id=project_id,
            subject_id=subject_id,
            intent_key=intent.intent_id,
            level=benefit.level.value,
        )

    return assessment, Candidate(intent=intent, scope=scope, habit=assessment, risk=risk, benefit=benefit)


def _persist_lifecycle_decisions(
    session: Session,
    project_id: str,
    subject_id: str,
    now: datetime,
    assessments: list[HabitAssessment],
    candidate_by_variant: dict[str, Candidate],
    outcome_by_intent: dict[str, tuple[SelectionOutcome, tuple[ReasonCode, ...]]],
    family_key_by_variant: dict[str, str],
    lifecycle_config: LifecycleConfig,
) -> list[VariantAnalysisSummary]:
    summaries: list[VariantAnalysisSummary] = []

    for assessment in assessments:
        variant_id = assessment.variant_id
        family_key = family_key_by_variant[variant_id]
        candidate = candidate_by_variant.get(variant_id)
        existing = fetch_suggestion_by_variant(session, variant_id)
        previous_state = SuggestionState(existing.state) if existing else None

        has_eligible_intent = False
        reason_codes = list(reason_codes_to_list(assessment.reason_codes))
        primary_intent_key: str | None = None

        if candidate is not None:
            outcome, selection_reasons = outcome_by_intent[candidate.intent.intent_id]
            reason_codes = [
                *reason_codes,
                *reason_codes_to_list(candidate.risk.reason_codes),
                *reason_codes_to_list(selection_reasons),
            ]
            if outcome == SelectionOutcome.SELECTED:
                has_eligible_intent = True
                primary_intent_key = candidate.intent.intent_id

        last_seen_at = assessment.evidence.last_seen_at if assessment.evidence else None
        next_state = next_state_for_reanalysis(
            previous_state,
            existing.dismiss_cooldown_until if existing else None,
            assessment.decision,
            has_eligible_intent,
            last_seen_at,
            now,
            lifecycle_config,
        )

        if primary_intent_key is None:
            if existing is not None:
                primary_intent_key = existing.primary_intent_key
            else:
                summaries.append(VariantAnalysisSummary(variant_id, assessment.decision, None))
                continue

        stays_dismissed = next_state == SuggestionState.DISMISSED and existing is not None
        dismissed_at = existing.dismissed_at if stays_dismissed and existing else None
        cooldown_until = existing.dismiss_cooldown_until if stays_dismissed and existing else None

        upsert_suggestion(
            session,
            project_id,
            subject_id,
            family_key,
            variant_id,
            primary_intent_key,
            next_state.value,
            reason_codes,
            now,
            dismissed_at,
            cooldown_until,
        )
        if next_state == SuggestionState.ACTIVE:
            log_event("suggestion_eligible", project_id=project_id, subject_id=subject_id, variant_key=variant_id)

        summaries.append(VariantAnalysisSummary(variant_id, assessment.decision, next_state))

    return summaries


def analyze_subject(
    session: Session, project_config: ProjectConfig, project_id: str, subject_id: str, now: datetime
) -> AnalysisSummary:
    engine_config = project_config.engine
    log_event("analysis_started", project_id=project_id, subject_id=subject_id)

    all_series = _extract_all_series(session, project_id, subject_id)
    series_by_id = {series.series_id: series for series in all_series}
    log_event("series_extracted", project_id=project_id, subject_id=subject_id, count=len(all_series))

    episode_candidates = build_episode_candidates(all_series, engine_config.episode)
    candidates_by_id = {candidate.candidate_id: candidate for candidate in episode_candidates}
    log_event(
        "episode_candidates_built", project_id=project_id, subject_id=subject_id, count=len(episode_candidates)
    )

    families = group_into_families(episode_candidates)
    log_event("families_grouped", project_id=project_id, subject_id=subject_id, count=len(families))

    assessments: list[HabitAssessment] = []
    family_key_by_variant: dict[str, str] = {}
    candidate_by_variant: dict[str, Candidate] = {}

    for family in families:
        for variant in resolve_targets(family, candidates_by_id):
            family_key_by_variant[variant.variant_id] = family.family_id
            assessment, candidate = _evaluate_variant(
                variant, family, candidates_by_id, series_by_id, engine_config, project_id, subject_id
            )
            assessments.append(assessment)
            if candidate is not None:
                candidate_by_variant[variant.variant_id] = candidate

    replace_habit_evaluations(session, project_id, subject_id, assessments, family_key_by_variant, now)

    selector_candidates = list(candidate_by_variant.values())
    selection_results = select(selector_candidates, project_id, subject_id)
    outcome_by_intent = {result.intent_id: (result.outcome, result.reason_codes) for result in selection_results}

    intent_entries = [
        (
            candidate.intent,
            candidate.scope,
            family_key_by_variant[candidate.intent.variant_id],
            candidate.risk,
            candidate.benefit,
            outcome_by_intent[candidate.intent.intent_id][0].value,
            reason_codes_to_list(outcome_by_intent[candidate.intent.intent_id][1]),
        )
        for candidate in selector_candidates
    ]
    replace_shortcut_intents(session, project_id, subject_id, intent_entries, now)

    summaries = _persist_lifecycle_decisions(
        session,
        project_id,
        subject_id,
        now,
        assessments,
        candidate_by_variant,
        outcome_by_intent,
        family_key_by_variant,
        engine_config.lifecycle,
    )

    return AnalysisSummary(
        project_id=project_id, subject_id=subject_id, series_count=len(all_series), variants=summaries
    )


# ==============================================================================
# FILE: src/awe/services/ingestion.py
# ==============================================================================
"""Raw event ingestion: idempotent kabul ve canonical Observation üretimi (bölüm 6.1, 6.3).

Aynı `(project_id, event_id)` daha önce farklı bir payload'la geldiyse ikinci event kabul
edilmez ve karantinaya alınır (bölüm 6.3: "Aynı (projectId, eventId) farklı içerikle geldiyse
conflict quarantine edilir") — ilk kabul edilen payload otorite kalır.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.adapter import AdapterValidationError, build_observation
from awe.config import ProjectConfig, log_event
from awe.persistence.repository import (
    event_exists,
    fetch_event_payload,
    insert_event,
    insert_event_conflict,
    insert_observation,
)


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    accepted: bool
    duplicate: bool
    conflict: bool = False
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
        first_payload = fetch_event_payload(session, observation.project_id, observation.event_id)
        if first_payload is not None and first_payload != raw_event:
            insert_event_conflict(
                session, observation.project_id, observation.event_id, first_payload, raw_event, now
            )
            log_event(
                "event_conflict_quarantined",
                project_id=observation.project_id,
                subject_id=observation.subject_id,
                event_id=observation.event_id,
            )
            return IngestOutcome(accepted=False, duplicate=True, conflict=True, event_id=observation.event_id)
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


# ==============================================================================
# FILE: src/awe/services/suggestions.py
# ==============================================================================
"""Subject'e ait suggestion'ların dışa sunulacak görünümü ve dismiss akışı."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from awe.config.engine_config import LifecycleConfig
from awe.domain.benefit import BenefitEvidence
from awe.lifecycle import dismiss as dismiss_lifecycle
from awe.persistence.models import ShortcutIntentRecord, SuggestionRecord
from awe.persistence.repository import (
    fetch_shortcut_intent_by_key,
    fetch_suggestion_by_key,
    list_suggestions,
)

_VISIBLE_STATES = {"active", "stale"}


@dataclass(frozen=True, slots=True)
class IntentView:
    intent_key: str
    mode: str | None
    destination_screen: str | None
    target: str | None
    requires_user_confirmation: bool
    risk_decision: str
    benefit_saved_actions: int
    benefit_level: str


@dataclass(frozen=True, slots=True)
class SuggestionView:
    suggestion_key: str
    project_id: str
    subject_id: str
    state: str
    reason_codes: list[str]
    intent: IntentView
    created_at: datetime
    updated_at: datetime
    dismissed_at: datetime | None


def _to_intent_view(record: ShortcutIntentRecord) -> IntentView:
    benefit = BenefitEvidence(
        intent_id=record.intent_key,
        observed_actions=record.benefit_observed_actions,
        planned_actions=record.benefit_planned_actions,
    )
    return IntentView(
        intent_key=record.intent_key,
        mode=record.mode,
        destination_screen=record.destination_screen,
        target=record.target,
        requires_user_confirmation=record.requires_user_confirmation,
        risk_decision=record.risk_decision,
        benefit_saved_actions=benefit.saved_actions,
        benefit_level=benefit.level.value,
    )


def _to_suggestion_view(session: Session, record: SuggestionRecord) -> SuggestionView | None:
    intent_record = fetch_shortcut_intent_by_key(session, record.primary_intent_key)
    if intent_record is None:
        return None
    return SuggestionView(
        suggestion_key=record.suggestion_key,
        project_id=record.project_id,
        subject_id=record.subject_id,
        state=record.state,
        reason_codes=record.reason_codes,
        intent=_to_intent_view(intent_record),
        created_at=record.created_at,
        updated_at=record.updated_at,
        dismissed_at=record.dismissed_at,
    )


def list_subject_suggestions(session: Session, project_id: str, subject_id: str) -> list[SuggestionView]:
    records = list_suggestions(session, project_id, subject_id, states=_VISIBLE_STATES)
    views = [_to_suggestion_view(session, record) for record in records]
    return [view for view in views if view is not None]


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


# ==============================================================================
# FILE: src/awe/targeting/__init__.py
# ==============================================================================
from awe.targeting.resolver import resolve_targets

__all__ = ["resolve_targets"]


# ==============================================================================
# FILE: src/awe/targeting/resolver.py
# ==============================================================================
"""Target Resolver (bölüm 6.6): Base Family occurrence'larını target fingerprint ile böler.

Occurrence fingerprint'i `(step_1.target, ..., step_n.target)`. Her exact fingerprint ayrı
bir `TargetVariant` olarak Habit'e gider — böylece `course_42` üç kez tekrar ederken
`course_17` bir kez görülmüşse kanıtlar havuzlanmaz.

`kind` yorumu (belgenin dört durumu net bir eksen üzerinde tanımlamadığı yer): burada bir
fingerprint'in kendi İÇİNDEKİ distinct non-null değer sayısına bakılır — bir occurrence'ın
kendi adımları birden fazla farklı hedefe değiniyorsa (ör. "workspace_1" ve "report_9" aynı
occurrence içinde) bu `VARIABLE_TARGET`'tır ve Shortcut Intent Builder'ın compound-identity
reddi (bölüm 6.12) ile doğrudan örtüşür. İki AYRI occurrence farklı ama kendi içinde tutarlı
hedeflere sahipse (course_42 vs course_17), bunlar zaten farklı fingerprint'ler oldukları için
ayrı ayrı `FIXED_TARGET` variant'lara ayrılır — havuzlanma zaten bu ayrıştırmayla önlenir."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from awe.domain.enums import TargetVariantKind
from awe.domain.episode import EpisodeCandidate
from awe.domain.family import BaseFamily
from awe.domain.target import TargetFingerprint, TargetVariant


def _fingerprint_digest(fingerprint: TargetFingerprint) -> str:
    serialized = "\x1f".join(value if value is not None else "\x00" for value in fingerprint)
    return hashlib.sha1(serialized.encode()).hexdigest()[:12]


def _kind_of(fingerprint: TargetFingerprint, has_unknown: bool) -> TargetVariantKind:
    if has_unknown:
        return TargetVariantKind.UNKNOWN_TARGET
    distinct_non_null = {value for value in fingerprint if value is not None}
    if not distinct_non_null:
        return TargetVariantKind.NO_EXPLICIT_TARGET
    if len(distinct_non_null) == 1:
        return TargetVariantKind.FIXED_TARGET
    return TargetVariantKind.VARIABLE_TARGET


def resolve_targets(family: BaseFamily, candidates_by_id: dict[str, EpisodeCandidate]) -> list[TargetVariant]:
    groups: dict[TargetFingerprint, list[EpisodeCandidate]] = defaultdict(list)
    for occurrence_id in family.occurrence_ids:
        candidate = candidates_by_id[occurrence_id]
        groups[candidate.targets].append(candidate)

    variants: list[TargetVariant] = []
    for fingerprint, members in groups.items():
        has_unknown = any(step.target_unknown for member in members for step in member.steps)
        variants.append(
            TargetVariant(
                variant_id=f"{family.family_id}:{_fingerprint_digest(fingerprint)}",
                family_id=family.family_id,
                kind=_kind_of(fingerprint, has_unknown),
                fingerprint=fingerprint,
                occurrence_ids=[member.candidate_id for member in members],
            )
        )
    return variants


# ==============================================================================
# FILE: src/awe/testing/__init__.py
# ==============================================================================
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


# ==============================================================================
# FILE: src/awe/testing/generators.py
# ==============================================================================
"""Deterministik sentetik event log üretici.

Her profil, gerçek bir kullanıcı davranış deseni için (günlük, haftalık, burst, gürültülü, vb.)
ground-truth bir Habit beklentisiyle birlikte, yeni ham event sözleşmesiyle (bölüm 4:
eventId/projectId/subjectId/sessionId/timestamp/actionKey/effect/trigger/source/screen/target/
status/duration) uyumlu ham event üretir.

Bu modül yalnızca test/evaluation amaçlıdır; üretim koduna (adapter, engine) bağımlılığı yoktur.

Eski tasarımdan kalan iki profil kasıtlı olarak kaldırılmıştır: `widget_rename` (artık `widget`
alanı yok — `screen` sembolün parçası olduğu için "kimlikten hariç tutulan alan" kavramının
analogu kalmadı) ve `parameter_drift` (FieldBinding recent-drift kavramı yeni tasarımda yok;
`target_variable` zaten aynı temel senaryoyu — hedefin değişkenliğini — kapsıyor).
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
    trigger: str = "button",
    screen: str = "app",
    target: str | None = None,
    status: str = "success",
) -> dict:
    return {
        "eventId": event_id,
        "projectId": project_id,
        "subjectId": subject_id,
        "sessionId": session_id,
        "timestamp": timestamp.isoformat(),
        "source": "client",
        "actionKey": action_key,
        "effect": effect,
        "trigger": trigger,
        "screen": screen,
        "target": target,
        "status": status,
        "duration": None,
    }


@dataclass(frozen=True, slots=True)
class _OccurrenceSpec:
    day: int
    minute_offset: int
    session_index: int
    target_ref: str | None = "item_1"
    add_noise: bool = False
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
        events.append(_raw_event(project_id, subject_id, session_id, event_id, ts, action_key, effect, **kwargs))
        step += 1

    if spec.add_noise:
        # effect="none" bölüm 6.2'de koşulsuz IGNORE üretir; temiz action akışına hiç girmez
        # ve Family kimliğini etkilemez.
        emit("app_foreground", "none", trigger="automatic")

    last_index = len(flow) - 1
    for index, (action_key, effect) in enumerate(flow):
        if spec.add_retry and index == last_index:
            # `status` artık sınıflandırmayı etkilemez (bölüm 3 kural 4) — bu iki başarısız
            # deneme normalize edilip sıkıştırılmaz, exact sembol dizisine ayrı adım olarak
            # girer. Bu, retry-ağır bir davranışın "temiz" variant'tan ayrı, daha küçük bir
            # variant'a bölünmesine yol açar (bölüm 9.3 exact fragmentation) — kasıtlı kabul.
            emit(action_key, effect, status="fail")
            emit(action_key, effect, status="fail")

        target = spec.target_ref if (spec.target_ref and effect == "select") else None
        status = spec.final_status if index == last_index else "success"
        emit(action_key, effect, target=target, status=status)

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
        return [_OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_noise=True) for d in range(20)]
    if profile == "retry_heavy":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, add_retry=(d % 2 == 0)) for d in range(20)
        ]
    if profile == "target_variable":
        return [
            _OccurrenceSpec(day=d, minute_offset=0, session_index=0, target_ref=f"item_{d % 7}") for d in range(20)
        ]
    raise ValueError(f"unknown profile: {profile}")


_EXPECTED_DECISION: dict[str, HabitDecision] = {
    "daily_regular": HabitDecision.HABIT_DETECTED,
    "daily_missing_days": HabitDecision.HABIT_DETECTED,
    "daily_high_frequency": HabitDecision.HABIT_DETECTED,
    "weekly_regular": HabitDecision.HABIT_DETECTED,
    "biweekly_regular": HabitDecision.HABIT_DETECTED,
    "monthly_regular": HabitDecision.HABIT_DETECTED,
    "irregular_recurring": HabitDecision.HABIT_DETECTED,
    "short_frequent": HabitDecision.HABIT_DETECTED,
    "long_workflow": HabitDecision.HABIT_DETECTED,
    "one_day_burst": HabitDecision.INSUFFICIENT_EVIDENCE,
    # Yeni MVP kapısı `distinct day >= 2` (bölüm 6.7) — eski `>= 3` eşiğinden düşürüldü. İki
    # farklı günde, sayısı ne olursa olsun, artık HABIT_DETECTED üretir; bu belgenin kendi
    # eşiğinin doğrudan sonucudur (yalnızca tek-gün burst'ü açıkça reddeder, bölüm 9.8).
    "two_day_burst": HabitDecision.HABIT_DETECTED,
    "single_session_repeater": HabitDecision.INSUFFICIENT_EVIDENCE,
    "stale": HabitDecision.HABIT_DETECTED,
    "revived": HabitDecision.HABIT_DETECTED,
    "noisy": HabitDecision.HABIT_DETECTED,
    "retry_heavy": HabitDecision.HABIT_DETECTED,
    "target_variable": HabitDecision.HABIT_DETECTED,
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
    """Aynı kullanıcı için birbirinden bağımsız birden fazla Habit."""

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


# DOSYA SONU -- src/awe altindaki tum paketler bu dosyada mevcuttur (68 dosya).