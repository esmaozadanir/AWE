"""Test fixture yardımcıları: Observation, OSeries ve BaseFamily nesnelerini elle ama
tutarlı biçimde üretir.

Bu modül testler tarafından kullanılır, üretim kodunun bir parçası değildir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from awe.domain.enums import (
    EpisodeCandidateKind,
    ObservationEffect,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.domain.episode import EpisodeCandidate
from awe.domain.family import BaseFamily
from awe.domain.observation import Observation, ObservationQuality
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken
from awe.families import group_into_families


def make_observation(
    action: str,
    *,
    event_id: str,
    session_id: str,
    timestamp: datetime,
    subject_id: str = "subject",
    project_id: str = "project",
    effect: ObservationEffect = ObservationEffect.ROUTE,
    status: ObservationStatus = ObservationStatus.SUCCESS,
    trigger: ObservationTrigger = ObservationTrigger.BUTTON,
    source: ObservationSource = ObservationSource.CLIENT,
    screen: str | None = "screen",
    target: str | None = None,
    duration_ms: int | None = None,
    missing_target_field: bool = False,
    invalid_duration: bool = False,
    mapping_version: str = "test-fixture",
) -> Observation:
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
        mapping_version=mapping_version,
        quality=ObservationQuality(
            has_screen=screen is not None,
            missing_target_field=missing_target_field,
            invalid_duration=invalid_duration,
        ),
    )


@dataclass(frozen=True, slots=True)
class StepSpec:
    action: str
    effect: ObservationEffect = ObservationEffect.ROUTE
    screen: str | None = "screen"
    target: str | None = None
    target_unknown: bool = False
    status: ObservationStatus = ObservationStatus.SUCCESS
    trigger: ObservationTrigger = ObservationTrigger.BUTTON


def make_series_from_steps(
    session_id: str,
    started_at: datetime,
    steps: list[StepSpec],
    *,
    subject_id: str = "subject",
    project_id: str = "project",
    has_shortcut_trigger: bool = False,
    series_suffix: str = "0",
    mapping_version: str = "test-fixture",
    cut_by_ambiguity: bool = False,
    views_after: dict[int, list[str]] | None = None,
) -> OSeries:
    """ACTION-classified `BehaviorStep` dizisini doğrudan kurar — `extract_series` çağırmaz,
    bu yüzden testler O-Series Builder'ın chunk-bölme kurallarından izole olur (bu kurallar
    kendi adanmış testlerinde doğrulanır).

    `views_after[step_index]`: o adımdan hemen sonra, CONTEXT-classified (effect=view) ekstra
    raw observation'lar olarak eklenecek screen adları — Screen Transition Evidence / Anchor
    WEAK / Destination testleri için gereklidir (bu kanıt yalnızca raw_observations'ta yaşar,
    ACTION-only `steps` dizisinde değil)."""

    views_after = views_after or {}
    raw_observations: list[Observation] = []
    behavior_steps: list[BehaviorStep] = []
    clock = 0

    for index, spec in enumerate(steps):
        obs = make_observation(
            spec.action,
            event_id=f"{session_id}-{series_suffix}-evt{index}",
            session_id=session_id,
            timestamp=started_at + timedelta(seconds=clock),
            subject_id=subject_id,
            project_id=project_id,
            effect=spec.effect,
            status=spec.status,
            trigger=ObservationTrigger.SHORTCUT if has_shortcut_trigger and index == 0 else spec.trigger,
            screen=spec.screen,
            target=spec.target,
            missing_target_field=spec.target_unknown,
            mapping_version=mapping_version,
        )
        step_observation_index = len(raw_observations)
        raw_observations.append(obs)
        clock += 5
        behavior_steps.append(
            BehaviorStep(
                token=BehaviorToken(
                    action=spec.action, effect=spec.effect, screen=spec.screen, mapping_version=mapping_version
                ),
                target=spec.target,
                target_unknown=spec.target_unknown,
                status=spec.status,
                observation_index=step_observation_index,
            )
        )

        for view_index, screen in enumerate(views_after.get(index, [])):
            view_obs = make_observation(
                f"{spec.action}_view_{view_index}",
                event_id=f"{session_id}-{series_suffix}-evt{index}-view{view_index}",
                session_id=session_id,
                timestamp=started_at + timedelta(seconds=clock),
                subject_id=subject_id,
                project_id=project_id,
                effect=ObservationEffect.VIEW,
                status=ObservationStatus.SUCCESS,
                trigger=ObservationTrigger.AUTOMATIC,
                screen=screen,
                mapping_version=mapping_version,
            )
            raw_observations.append(view_obs)
            clock += 1

    return OSeries(
        series_id=f"{session_id}#{series_suffix}",
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        started_at=raw_observations[0].timestamp,
        ended_at=raw_observations[-1].timestamp,
        ordering_confidence=OrderingConfidence.HIGH,
        raw_observations=tuple(raw_observations),
        steps=tuple(behavior_steps),
        entry_trigger=raw_observations[0].trigger,
        entry_screen=raw_observations[0].screen,
        has_shortcut_trigger=has_shortcut_trigger,
        final_status=raw_observations[-1].status,
        cut_by_ambiguity=cut_by_ambiguity,
    )


def make_series(
    session_id: str,
    started_at: datetime,
    actions: list[str],
    *,
    subject_id: str = "subject",
    project_id: str = "project",
    has_shortcut_trigger: bool = False,
    series_suffix: str = "0",
) -> OSeries:
    steps = [StepSpec(action=action) for action in actions]
    return make_series_from_steps(
        session_id,
        started_at,
        steps,
        subject_id=subject_id,
        project_id=project_id,
        has_shortcut_trigger=has_shortcut_trigger,
        series_suffix=series_suffix,
    )


def build_family_from_steps(
    steps_per_occurrence: list[list[StepSpec]],
    *,
    project_id: str = "project",
    subject_id: str = "subject",
    base_time: datetime | None = None,
    has_shortcut_trigger_at: frozenset[int] = frozenset(),
) -> tuple[BaseFamily, list[OSeries], dict[str, EpisodeCandidate]]:
    """Bir dizi occurrence tanımından tek bir `BaseFamily` + üye `OSeries` listesi + candidate
    haritası kurar. Her occurrence'ın exact sembol dizisi AYNI olmalıdır (aksi halde gerçek
    `group_into_families` onları ayrı family'lere böler ve bu fonksiyon assertion ile durur) —
    Family eşleştirmesi artık deterministik olduğu için gerçek üretim kodundan geçirilir."""

    base_time = base_time or datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    series_list: list[OSeries] = []
    candidates: list[EpisodeCandidate] = []
    candidates_by_id: dict[str, EpisodeCandidate] = {}

    for index, steps in enumerate(steps_per_occurrence):
        started = base_time + timedelta(days=index)
        series = make_series_from_steps(
            session_id=f"sess{index}",
            started_at=started,
            steps=steps,
            subject_id=subject_id,
            project_id=project_id,
            series_suffix=str(index),
            has_shortcut_trigger=index in has_shortcut_trigger_at,
        )
        series_list.append(series)
        candidate = EpisodeCandidate(
            candidate_id=f"{series.series_id}:full",
            project_id=project_id,
            subject_id=subject_id,
            session_id=series.session_id,
            series_id=series.series_id,
            kind=EpisodeCandidateKind.FULL_CHUNK,
            steps=series.steps,
            step_indices=tuple(range(len(series.steps))),
            observed_at=series.started_at,
            entry_trigger=series.entry_trigger,
            has_shortcut_trigger=series.has_shortcut_trigger,
            final_status=series.final_status,
        )
        candidates.append(candidate)
        candidates_by_id[candidate.candidate_id] = candidate

    families = group_into_families(candidates)
    if len(families) != 1:
        raise AssertionError(
            f"fixture occurrence'ları tek bir exact family'de toplanmadı: {len(families)} family bulundu"
        )
    return families[0], series_list, candidates_by_id
