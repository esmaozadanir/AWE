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
