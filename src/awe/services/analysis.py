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
    all_series: list[OSeries],
    engine_config: EngineConfig,
    project_id: str,
    subject_id: str,
) -> tuple[HabitAssessment, Candidate | None]:
    assessment = evaluate_habit(variant, candidates_by_id, all_series, engine_config.timezone, engine_config.habit)
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
                variant, family, candidates_by_id, series_by_id, all_series, engine_config, project_id, subject_id
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
