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

from awe.benefit import evaluate_benefit
from awe.config import EngineConfig, ProjectConfig, log_event
from awe.domain.enums import FamilyMatchOutcome, HabitDecision, SuggestionState
from awe.domain.family import BehaviorFamily
from awe.domain.habit import HabitAssessment
from awe.domain.series import OSeries
from awe.families import accept_series, compute_discriminative_weights, match_series, seed_family
from awe.habit import evaluate_habit
from awe.lifecycle import next_state_for_reanalysis
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
from awe.planner import build_plan_candidates
from awe.risk import ResolverContract, evaluate_risk
from awe.selection import (
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
