"""Risk Evaluator (bölüm 6.13): açıklanabilir vektör + ALLOW/BLOCK kapısı.

MVP kuralları: delete bağlamı BLOCK; unknown effect BLOCK; kritik quality flag BLOCK; unknown
anchor status BLOCK; fail/cancel karışımı tek başına block nedeni değildir.
"""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config.engine_config import RiskConfig, ScreenEvidenceConfig
from awe.domain.enums import EpisodeCandidateKind, ObservationEffect, ObservationStatus, ReasonCode, RiskDecision
from awe.domain.episode import EpisodeCandidate
from awe.families import group_into_families
from awe.planner import build_shortcut_intent, project_scope, resolve_anchor, resolve_destination
from awe.risk import evaluate_risk
from awe.targeting import resolve_targets
from tests.support.builders import StepSpec, make_observation, make_series_from_steps

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_SCREEN_CONFIG = ScreenEvidenceConfig(min_supporting_sessions=2)
_RISK_CONFIG = RiskConfig()


def _candidate_from(series, suffix="full") -> EpisodeCandidate:
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:{suffix}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=EpisodeCandidateKind.FULL_CHUNK,
        steps=series.steps,
        start_index=0,
        observed_at=series.started_at,
        entry_trigger=series.entry_trigger,
        has_shortcut_trigger=series.has_shortcut_trigger,
        final_status=series.final_status,
    )


def _prepare(steps: list[StepSpec], repeats: int, *, status_cycle: list[ObservationStatus] | None = None):
    occurrences = []
    for index in range(repeats):
        occurrence_steps = steps
        if status_cycle is not None:
            occurrence_steps = [
                StepSpec(
                    action=s.action,
                    effect=s.effect,
                    screen=s.screen,
                    target=s.target,
                    status=status_cycle[index % len(status_cycle)] if i == len(steps) - 1 else s.status,
                    trigger=s.trigger,
                )
                for i, s in enumerate(steps)
            ]
        occurrences.append(occurrence_steps)

    series_list = [
        make_series_from_steps(f"sess{i}", _NOW, occ, series_suffix=str(i)) for i, occ in enumerate(occurrences)
    ]
    candidates = [_candidate_from(series) for series in series_list]
    candidates_by_id = {c.candidate_id: c for c in candidates}
    series_by_id = {series.series_id: series for series in series_list}

    families = group_into_families(candidates)
    assert len(families) == 1
    family = families[0]
    variants = resolve_targets(family, candidates_by_id)
    assert len(variants) == 1
    variant = variants[0]

    anchor = resolve_anchor(family.symbols, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    scope = project_scope(family.symbols, variant.variant_id, anchor)
    destination = resolve_destination(anchor, variant, candidates_by_id, series_by_id, _SCREEN_CONFIG)
    intent = build_shortcut_intent(variant, anchor, scope, destination)
    return intent, variant, scope, candidates_by_id, series_by_id


def test_delete_effect_anchor_is_blocked():
    steps = [StepSpec(action="delete_item", effect=ObservationEffect.DELETE)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(steps, 3)

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert risk.decision == RiskDecision.BLOCK
    assert ReasonCode.EXECUTE_BLOCKED_EFFECT in risk.reason_codes


def test_unknown_effect_anchor_is_blocked():
    steps = [StepSpec(action="mystery_action", effect=ObservationEffect.UNKNOWN)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(steps, 3)

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert risk.decision == RiskDecision.BLOCK
    assert ReasonCode.UNKNOWN_EFFECT in risk.reason_codes


def test_safe_effect_with_successes_is_allowed():
    steps = [StepSpec(action="open_reports", effect=ObservationEffect.SELECT)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(steps, 3)

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert risk.decision == RiskDecision.ALLOW


def test_state_changing_effect_is_not_auto_blocked_since_shortcut_never_executes_it():
    """Bölüm 6.13: state-changing gözlenen akış, kısayol onu execute etmediği sürece otomatik
    block edilmez (EXECUTE modu hiç yoktur)."""
    steps = [StepSpec(action="update_profile", effect=ObservationEffect.UPDATE)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(steps, 3)

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert risk.decision == RiskDecision.ALLOW
    assert risk.evidence.execution_exposure.value == "none"


def test_all_unknown_status_occurrences_are_blocked():
    steps = [StepSpec(action="open_reports", effect=ObservationEffect.ROUTE, status=ObservationStatus.UNKNOWN)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(steps, 3)

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert risk.decision == RiskDecision.BLOCK
    assert ReasonCode.UNKNOWN_ANCHOR_STATUS in risk.reason_codes


def test_mixed_fail_outcomes_are_flagged_but_do_not_block_alone():
    steps = [StepSpec(action="open_reports", effect=ObservationEffect.SELECT)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(
        steps, 4, status_cycle=[ObservationStatus.SUCCESS, ObservationStatus.FAIL]
    )

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert ReasonCode.MIXED_OBSERVED_OUTCOMES in risk.reason_codes
    assert risk.decision == RiskDecision.ALLOW


def test_critical_quality_flag_blocks():
    steps = [StepSpec(action="open_reports", effect=ObservationEffect.SELECT)]
    intent, variant, scope, candidates_by_id, series_by_id = _prepare(steps, 3)

    # Anchor'a giden tüm ham observation'ları kalite bayraklı sürümle değiştir.
    for series in series_by_id.values():
        dirty_observations = tuple(
            make_observation(
                obs.action,
                event_id=obs.event_id,
                session_id=obs.session_id,
                timestamp=obs.timestamp,
                effect=obs.effect,
                status=obs.status,
                trigger=obs.trigger,
                screen=obs.screen,
                target=obs.target,
                missing_target_field=True,
            )
            for obs in series.raw_observations
        )
        object.__setattr__(series, "raw_observations", dirty_observations)

    risk = evaluate_risk(intent, variant, scope, candidates_by_id, series_by_id, _RISK_CONFIG)

    assert risk.decision == RiskDecision.BLOCK
    assert ReasonCode.CRITICAL_QUALITY_FLAG in risk.reason_codes
