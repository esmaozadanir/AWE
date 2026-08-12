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
    HabitCadence,
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
        "active_days_total": evidence.active_days_total,
        "support_ratio": evidence.support_ratio,
        "mean_gap_days": evidence.mean_gap_days,
        "gap_regularity": evidence.gap_regularity,
        "cadence": evidence.cadence.value,
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
        active_days_total=data["active_days_total"],
        support_ratio=data["support_ratio"],
        mean_gap_days=data["mean_gap_days"],
        gap_regularity=data["gap_regularity"],
        cadence=HabitCadence(data["cadence"]),
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
