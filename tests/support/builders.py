"""Test fixture yardımcıları: Observation ve OSeries nesnelerini elle ama tutarlı biçimde üretir.

Bu modül testler tarafından kullanılır, üretim kodunun bir parçası değildir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from awe.config.engine_config import EngineConfig
from awe.domain.enums import (
    FamilyMatchOutcome,
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.domain.family import BehaviorFamily
from awe.domain.observation import Observation, ObservationQuality
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken
from awe.families import accept_series, match_series, seed_family
from awe.series.normalization import normalize_steps


@dataclass(frozen=True, slots=True)
class StepSpec:
    action_key: str
    effect: ObservationEffect = ObservationEffect.ROUTE
    role: ObservationRole = ObservationRole.ACTION
    screen: str | None = "screen"
    widget: str | None = None
    target: str | None = None
    parameters: dict[str, str] = field(default_factory=dict)
    status: ObservationStatus = ObservationStatus.SUCCESS
    trigger: ObservationTrigger = ObservationTrigger.BUTTON


def make_observation(
    action_key: str,
    *,
    event_id: str,
    session_id: str,
    timestamp: datetime,
    subject_id: str = "subject",
    project_id: str = "project",
    effect: ObservationEffect = ObservationEffect.ROUTE,
    status: ObservationStatus = ObservationStatus.SUCCESS,
    role: ObservationRole = ObservationRole.ACTION,
    trigger: ObservationTrigger = ObservationTrigger.BUTTON,
    source: ObservationSource = ObservationSource.CLIENT,
    screen: str | None = "screen",
    widget: str | None = None,
    target: str | None = None,
    parameters: dict[str, str] | None = None,
    breaks_episode: bool = False,
) -> Observation:
    return Observation(
        event_id=event_id,
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        timestamp=timestamp,
        source=source,
        action=action_key,
        role=role,
        effect=effect,
        trigger=trigger,
        screen=screen,
        widget=widget,
        target=target,
        parameters=parameters or {},
        status=status,
        breaks_episode=breaks_episode,
        mapping_version="test-fixture",
        quality=ObservationQuality(
            has_screen=screen is not None, has_widget=widget is not None, has_session_id=True
        ),
    )


def make_series_from_steps(
    session_id: str,
    started_at: datetime,
    steps: list[StepSpec],
    *,
    subject_id: str = "subject",
    project_id: str = "project",
    has_shortcut_trigger: bool = False,
    series_suffix: str = "0",
) -> OSeries:
    raw_observations = []
    raw_behavior_steps = []
    for index, spec in enumerate(steps):
        obs = make_observation(
            spec.action_key,
            event_id=f"{session_id}-{series_suffix}-evt{index}",
            session_id=session_id,
            timestamp=started_at + timedelta(seconds=index * 5),
            subject_id=subject_id,
            project_id=project_id,
            effect=spec.effect,
            role=spec.role,
            status=spec.status,
            trigger=ObservationTrigger.SHORTCUT if has_shortcut_trigger and index == 0 else spec.trigger,
            screen=spec.screen,
            widget=spec.widget,
            target=spec.target,
            parameters=spec.parameters,
        )
        raw_observations.append(obs)
        if spec.role == ObservationRole.NOISE:
            continue
        raw_behavior_steps.append(
            BehaviorStep(
                token=BehaviorToken(action=spec.action_key, effect=spec.effect),
                screen=spec.screen,
                widget=spec.widget,
                status=spec.status,
                observation_index=index,
            )
        )

    normalization = normalize_steps(raw_behavior_steps, 4)

    return OSeries(
        series_id=f"{session_id}#{series_suffix}",
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        started_at=raw_observations[0].timestamp,
        ended_at=raw_observations[-1].timestamp,
        ordering_confidence=OrderingConfidence.HIGH,
        raw_observations=tuple(raw_observations),
        normalized_steps=tuple(normalization.steps),
        retries=tuple(normalization.retries),
        detour_observation_count=normalization.detour_step_count,
        ended_by_breaks_episode=False,
        entry_trigger=raw_observations[0].trigger,
        entry_screen=raw_observations[0].screen,
        has_shortcut_trigger=has_shortcut_trigger,
        final_status=raw_observations[-1].status,
    )


def make_series(
    session_id: str,
    started_at: datetime,
    action_keys: list[str],
    *,
    subject_id: str = "subject",
    project_id: str = "project",
    has_shortcut_trigger: bool = False,
    series_suffix: str = "0",
) -> OSeries:
    steps = [StepSpec(action_key=key) for key in action_keys]
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
    config: EngineConfig,
    *,
    family_id: str = "fam1",
    project_id: str = "project",
    subject_id: str = "subject",
    base_time: datetime | None = None,
) -> tuple[BehaviorFamily, list[OSeries]]:
    """Bir dizi occurrence tanımından tutarlı bir BehaviorFamily + üye OSeries listesi kurar.

    Her occurrence gerçek `match_series`/`accept_series` akışından geçer; bu yüzden testler
    Family eşleştirme algoritmasını atlamış olmaz, yalnızca fixture kurulumunu kısaltır.
    """

    base_time = base_time or datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    series_list: list[OSeries] = []
    family: BehaviorFamily | None = None

    for index, steps in enumerate(steps_per_occurrence):
        started = base_time + timedelta(days=index)
        series = make_series_from_steps(
            session_id=f"sess{index}",
            started_at=started,
            steps=steps,
            subject_id=subject_id,
            project_id=project_id,
            series_suffix=str(index),
        )
        series_list.append(series)
        symbols = series.symbols
        if family is None:
            family = seed_family(
                family_id, project_id, subject_id, series.series_id, symbols, started, config.family
            )
        else:
            decision = match_series(symbols, [family], {}, config.family)
            if decision.outcome not in (FamilyMatchOutcome.MATCH, FamilyMatchOutcome.VARIANT_MATCH):
                raise AssertionError(
                    f"fixture occurrence {index} beklenen family ile eşleşmedi: {decision.outcome}"
                )
            accept_series(family, series.series_id, symbols, started, config.family)

    assert family is not None
    return family, series_list
