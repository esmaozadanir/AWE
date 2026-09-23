"""Subject'e ait suggestion'ların dışa sunulacak görünümü ve dismiss akışı."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from awe.benefit import evaluate_benefit
from awe.config import DeliveryConfig, ProjectConfig
from awe.config.engine_config import LifecycleConfig
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import HabitDecision, IntentState, SelectionOutcome
from awe.domain.episode import EpisodeCandidate
from awe.domain.habit import HabitAssessment
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol
from awe.episodes import build_episode_candidates
from awe.families import group_into_families
from awe.lifecycle import dismiss as dismiss_lifecycle
from awe.ordering import group_by_session, order_session
from awe.persistence.models import HabitEvaluationRecord, ShortcutIntentRecord, SuggestionRecord
from awe.persistence.repository import (
    fetch_all_observations,
    fetch_habit_evaluation_by_variant,
    fetch_shortcut_intent_by_key,
    fetch_suggestion_by_key,
    fetch_suggestion_by_variant,
    list_habit_evaluations,
    list_suggestions,
    mark_suggestion_delivery,
)
from awe.persistence.serialization import dict_to_anchor, dict_to_habit_evidence, dict_to_scope
from awe.planner import build_shortcut_intent, project_scope, resolve_anchor, resolve_destination
from awe.risk import evaluate_risk
from awe.selection import Candidate, select
from awe.series import extract_series
from awe.targeting import resolve_targets

_VISIBLE_STATES = {"active", "stale"}
_RECOMMENDED_STATES = {"active", "stale"}


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
    delivered_at: datetime | None
    delivery_error: str | None


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
        delivered_at=record.delivered_at,
        delivery_error=record.delivery_error,
    )


def list_subject_suggestions(session: Session, project_id: str, subject_id: str) -> list[SuggestionView]:
    records = list_suggestions(session, project_id, subject_id, states=_VISIBLE_STATES)
    views = [_to_suggestion_view(session, record) for record in records]
    return [view for view in views if view is not None]


def list_pending_deliveries(session: Session, project_id: str, subject_id: str) -> list[SuggestionView]:
    """`delivered_at` hiç ayarlanmamış YA DA son güncellemeden (`updated_at`) sonra
    ayarlanmamış (öneri değişmiş ama yeni hali gönderilmemiş) suggestion'lar."""
    views = list_subject_suggestions(session, project_id, subject_id)
    return [view for view in views if view.delivered_at is None or view.updated_at > view.delivered_at]


def record_delivery(
    session: Session,
    project_id: str,
    subject_id: str,
    suggestion_key: str,
    now: datetime,
    error: str | None = None,
) -> SuggestionView | None:
    record = fetch_suggestion_by_key(session, suggestion_key)
    if record is None or record.project_id != project_id or record.subject_id != subject_id:
        return None
    mark_suggestion_delivery(session, suggestion_key, now, error)
    return _to_suggestion_view(session, record)


@dataclass(frozen=True, slots=True)
class PushResult:
    success: bool
    error: str | None = None
    pushed_count: int = 0
    push_failed_count: int = 0


def _delivery_auth_headers(delivery: DeliveryConfig) -> dict[str, str]:
    if delivery.auth_env_var is None:
        return {}
    token = os.environ.get(delivery.auth_env_var)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _suggestion_payload(view: SuggestionView) -> dict:
    """Bizim v1 varsayılan payload şeklimiz -- hedef servisin gerçek kontratı netleşince
    ayarlanması gerekebilir."""
    return {
        "suggestion_key": view.suggestion_key,
        "state": view.state,
        "reason_codes": view.reason_codes,
        "intent": {
            "mode": view.intent.mode,
            "destination_screen": view.intent.destination_screen,
            "target": view.intent.target,
            "requires_user_confirmation": view.intent.requires_user_confirmation,
        },
    }


def push_pending(
    session: Session,
    project_config: ProjectConfig,
    project_id: str,
    subject_id: str,
    now: datetime,
    client: httpx.Client | None = None,
) -> PushResult:
    """Bekleyen (henüz gönderilmemiş/güncellenmiş) önerileri `project_config.delivery.push_url`e
    gönderir -- `awe.services.ingest_sync.pull_and_analyze`den TAMAMEN bağımsızdır, ayrı
    tetiklenebilir, ayrı config anahtarına (`delivery:`) bağlıdır. `client` yalnızca testlerde
    `httpx.MockTransport` ile sahte bir sunucuya bağlamak için opsiyoneldir."""
    if not project_config.delivery.enabled:
        return PushResult(success=False, error="delivery.enabled=False")
    if not project_config.delivery.push_url:
        return PushResult(success=False, error="delivery.push_url ayarlı değil")

    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        pending = list_pending_deliveries(session, project_id, subject_id)
        headers = _delivery_auth_headers(project_config.delivery)
        pushed = failed = 0
        for view in pending:
            try:
                response = http_client.post(
                    project_config.delivery.push_url, json=_suggestion_payload(view), headers=headers, timeout=15.0
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                record_delivery(session, project_id, subject_id, view.suggestion_key, now, error=str(exc))
                failed += 1
            else:
                record_delivery(session, project_id, subject_id, view.suggestion_key, now)
                pushed += 1
        session.commit()
    finally:
        if owns_client:
            http_client.close()

    return PushResult(success=True, pushed_count=pushed, push_failed_count=failed)


@dataclass(frozen=True, slots=True)
class SuggestionExplanationView:
    suggestion_key: str
    steps: list[str]
    repeat_count: int
    saved_steps: int
    target: str | None
    anchor: str


def explain_suggestion(
    session: Session, project_id: str, subject_id: str, suggestion_key: str
) -> SuggestionExplanationView | None:
    record = fetch_suggestion_by_key(session, suggestion_key)
    if record is None or record.project_id != project_id or record.subject_id != subject_id:
        return None

    intent_record = fetch_shortcut_intent_by_key(session, record.primary_intent_key)
    if intent_record is None:
        return None

    habit_record = fetch_habit_evaluation_by_variant(session, record.variant_key)
    assert habit_record is not None and habit_record.evidence is not None

    scope = dict_to_scope(intent_record.scope)
    anchor = dict_to_anchor(intent_record.anchor)
    habit_evidence = dict_to_habit_evidence(habit_record.evidence)
    benefit = BenefitEvidence(
        intent_id=intent_record.intent_key,
        observed_actions=intent_record.benefit_observed_actions,
        planned_actions=intent_record.benefit_planned_actions,
    )
    return SuggestionExplanationView(
        suggestion_key=record.suggestion_key,
        steps=[symbol[0] for symbol in scope.included],
        repeat_count=habit_evidence.distinct_sessions,
        saved_steps=benefit.saved_actions,
        target=intent_record.target,
        anchor=anchor.symbol[0],
    )


@dataclass(frozen=True, slots=True)
class PatternStep:
    action: str
    effect: str
    screen: str | None


@dataclass(frozen=True, slots=True)
class VariantPatternView:
    """Bir variant için, önerilip önerilmediğinden bağımsız olarak motorun bulduğu davranış
    dizisi ve kararının açıklaması. `explain_suggestion`'dan farkı: yalnızca ACTIVE/STALE
    suggestion'lar için değil, `habit_evaluations`'a giren HER variant için üretilir --
    böylece 'neden önerilmedi' de aynı pattern kanıtıyla gösterilebilir."""

    variant_key: str
    family_key: str
    pattern: list[PatternStep]
    decision: str
    reason_codes: list[str]
    recommended: bool
    suggestion_state: str | None
    repeat_count: int | None
    distinct_days: int | None
    mode: str | None
    destination_screen: str | None
    target: str | None
    saved_steps: int | None


@dataclass(frozen=True, slots=True)
class _RecomputedContext:
    """Yalnızca `family.symbols` + `TargetVariant`larını yeniden türetmek için pipeline'ın
    ucuz/deterministik baş kısmını (Habit Evaluator'a kadar) tekrar çalıştırır -- hiçbir şey
    kalıcı hale getirmez. `analyze_subject`'in kendi hesapladığı `family_id`/`variant_id`
    değerleri exact sembol dizisinden türeyen deterministik hash'ler olduğundan (bkz.
    `awe.families.matching`), burada yeniden hesaplananlar önceki `/analyze` çağrısının
    kalıcı `habit_evaluations`/`suggestions` kayıtlarındaki key'lerle birebir eşleşir."""

    symbols_by_family: dict[str, tuple[Symbol, ...]]
    variants_by_key: dict[str, TargetVariant]
    candidates_by_id: dict[str, EpisodeCandidate]
    series_by_id: dict[str, OSeries]


def _recompute_context(
    session: Session, project_config: ProjectConfig, project_id: str, subject_id: str
) -> _RecomputedContext:
    observations = fetch_all_observations(session, project_id, subject_id)
    all_series = []
    for _session_id, session_observations in group_by_session(observations).items():
        ordered, confidence = order_session(session_observations)
        all_series.extend(extract_series(ordered, confidence))
    series_by_id = {series.series_id: series for series in all_series}

    episode_candidates = build_episode_candidates(all_series, project_config.engine.episode)
    candidates_by_id = {candidate.candidate_id: candidate for candidate in episode_candidates}
    families = group_into_families(episode_candidates)

    symbols_by_family: dict[str, tuple[Symbol, ...]] = {}
    variants_by_key: dict[str, TargetVariant] = {}
    for family in families:
        symbols_by_family[family.family_id] = family.symbols
        for variant in resolve_targets(family, candidates_by_id):
            variants_by_key[variant.variant_id] = variant

    return _RecomputedContext(symbols_by_family, variants_by_key, candidates_by_id, series_by_id)


def _reason_codes_for_undetected_intent(
    context: _RecomputedContext,
    project_config: ProjectConfig,
    project_id: str,
    subject_id: str,
    record: HabitEvaluationRecord,
) -> list[str]:
    """`habit_detected` olduğu halde hiç `SuggestionRecord`'a dönüşmemiş bir variant için
    (ör. anchor/hedef çözülemedi, Risk BLOCK dedi ya da Benefit yetersizdi), motorun asıl
    Selector'ını (`awe.selection.select`) TEK adaylık bir listeyle tekrar çalıştırıp gerçek
    red gerekçesini döndürür -- burada tahmini bir kod uydurmak yerine, motorun kendi
    `_is_eligible`/`select` mantığını birebir kullanır."""

    variant = context.variants_by_key.get(record.variant_key)
    family_symbols = context.symbols_by_family.get(record.family_key)
    if variant is None or family_symbols is None or record.evidence is None:
        return []

    engine_config = project_config.engine
    anchor = resolve_anchor(
        family_symbols, variant, context.candidates_by_id, context.series_by_id, engine_config.screen_evidence
    )
    scope = project_scope(family_symbols, variant.variant_id, anchor)
    destination = resolve_destination(
        anchor, variant, context.candidates_by_id, context.series_by_id, engine_config.screen_evidence
    )
    intent = build_shortcut_intent(variant, anchor, scope, destination)

    if intent.state != IntentState.READY:
        return [code.value for code in intent.reason_codes]

    risk = evaluate_risk(
        intent, variant, scope, context.candidates_by_id, context.series_by_id, engine_config.risk
    )
    benefit = evaluate_benefit(intent, len(scope.included))
    habit_assessment = HabitAssessment(
        variant_id=record.variant_key,
        decision=HabitDecision.HABIT_DETECTED,
        evidence=dict_to_habit_evidence(record.evidence),
    )
    candidate = Candidate(intent=intent, scope=scope, habit=habit_assessment, risk=risk, benefit=benefit)
    results = select([candidate], project_id, subject_id)
    if results and results[0].outcome != SelectionOutcome.SELECTED:
        return [code.value for code in results[0].reason_codes]
    return []


def list_variant_patterns(
    session: Session, project_config: ProjectConfig, project_id: str, subject_id: str
) -> list[VariantPatternView]:
    context = _recompute_context(session, project_config, project_id, subject_id)

    views: list[VariantPatternView] = []
    for record in list_habit_evaluations(session, project_id, subject_id):
        suggestion = fetch_suggestion_by_variant(session, record.variant_key)
        intent = fetch_shortcut_intent_by_key(session, suggestion.primary_intent_key) if suggestion else None

        reason_codes = list(record.reason_codes)
        if suggestion is not None:
            reason_codes = [*reason_codes, *suggestion.reason_codes]
        elif record.decision == HabitDecision.HABIT_DETECTED.value:
            reason_codes += _reason_codes_for_undetected_intent(
                context, project_config, project_id, subject_id, record
            )

        family_symbols = context.symbols_by_family.get(record.family_key, ())
        evidence = record.evidence or {}
        views.append(
            VariantPatternView(
                variant_key=record.variant_key,
                family_key=record.family_key,
                pattern=[PatternStep(action=s[0], effect=s[1], screen=s[2]) for s in family_symbols],
                decision=record.decision,
                reason_codes=reason_codes,
                recommended=suggestion is not None and suggestion.state in _RECOMMENDED_STATES,
                suggestion_state=suggestion.state if suggestion else None,
                repeat_count=evidence.get("distinct_sessions"),
                distinct_days=evidence.get("distinct_days"),
                mode=intent.mode if intent else None,
                destination_screen=intent.destination_screen if intent else None,
                target=intent.target if intent else None,
                saved_steps=(intent.benefit_observed_actions - intent.benefit_planned_actions if intent else None),
            )
        )
    return views


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
