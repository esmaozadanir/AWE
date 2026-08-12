from datetime import UTC, datetime, timedelta

from awe.config import default_engine_config
from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.domain.observation import Observation, ObservationQuality
from awe.series import extract_series

_BASE_TIME = datetime(2026, 8, 5, 10, 0, 0, tzinfo=UTC)


def _observation(
    action_key: str,
    *,
    index: int,
    effect: ObservationEffect = ObservationEffect.ROUTE,
    status: ObservationStatus = ObservationStatus.SUCCESS,
    role: ObservationRole = ObservationRole.ACTION,
    trigger: ObservationTrigger = ObservationTrigger.BUTTON,
    breaks_episode: bool = False,
) -> Observation:
    return Observation(
        event_id=f"evt{index}",
        project_id="proj",
        subject_id="subj",
        session_id="sess",
        timestamp=_BASE_TIME + timedelta(seconds=index),
        source=ObservationSource.CLIENT,
        action=action_key,
        role=role,
        effect=effect,
        trigger=trigger,
        screen="scr",
        widget=None,
        target=None,
        status=status,
        breaks_episode=breaks_episode,
        mapping_version="v1",
        quality=ObservationQuality(has_screen=True, has_widget=False, has_session_id=True),
    )


def test_bounded_detour_after_explicit_back_signal_is_collapsed():
    observations = [
        _observation("A", index=0),
        _observation("B", index=1),
        _observation("X", index=2),
        _observation("back_button", index=3, effect=ObservationEffect.NAVIGATE_BACK),
        _observation("B", index=4),
        _observation("C", index=5),
        _observation("D", index=6),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, default_engine_config().family)

    assert len(series) == 1
    assert series[0].symbols == (("A", "route"), ("B", "route"), ("C", "route"), ("D", "route"))
    assert series[0].detour_observation_count == 2


def test_repeated_action_without_back_signal_is_preserved_as_loop():
    observations = [
        _observation("A", index=0),
        _observation("B", index=1),
        _observation("C", index=2),
        _observation("B", index=3),
        _observation("D", index=4),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, default_engine_config().family)

    assert len(series) == 1
    assert series[0].symbols == (
        ("A", "route"),
        ("B", "route"),
        ("C", "route"),
        ("B", "route"),
        ("D", "route"),
    )


def test_failed_attempts_are_excluded_from_the_action_flow_and_leave_a_single_symbol():
    # `classify_event` başarısız (status != success) her event'i IGNORE sayar (bkz.
    # awe.adapter.classification); bu yüzden başarısız denemeler temiz action akışına hiç
    # girmez ve normalize_steps'e yalnızca son (başarılı) deneme ulaşır. Sonuç, eski
    # retry-collapse mekanizmasıyla AYNI sembol dizisidir (tek "C"), ama artık ortada
    # sıkıştırılacak ardışık bir tekrar olmadığından RetryEvidence üretilmez — bu, motorun
    # hiçbir yerinde kullanılmayan salt açıklayıcı bir metadata kaybıdır (bkz. rapor).
    observations = [
        _observation("A", index=0),
        _observation("B", index=1),
        _observation("C", index=2, status=ObservationStatus.FAIL),
        _observation("C", index=3, status=ObservationStatus.FAIL),
        _observation("C", index=4, status=ObservationStatus.SUCCESS),
        _observation("D", index=5),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, default_engine_config().family)

    assert len(series) == 1
    assert series[0].symbols == (("A", "route"), ("B", "route"), ("C", "route"), ("D", "route"))
    assert series[0].retries == ()
    assert len(series[0].raw_observations) == 6


def test_successful_submit_marks_a_natural_occurrence_boundary():
    observations = [
        _observation("A", index=0),
        _observation("B", index=1, effect=ObservationEffect.SUBMIT, status=ObservationStatus.SUCCESS),
        _observation("C", index=2),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, default_engine_config().family)

    assert len(series) == 2
    assert series[0].symbols == (("A", "route"), ("B", "submit"))
    assert series[1].symbols == (("C", "route"),)


def test_breaks_episode_is_a_hard_boundary_even_without_completion():
    observations = [
        _observation("A", index=0),
        _observation("logout", index=1, breaks_episode=True),
        _observation("A", index=2),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, default_engine_config().family)

    assert len(series) == 2
    assert series[0].ended_by_breaks_episode is True
    assert series[1].symbols == (("A", "route"),)


def test_ignore_classified_step_is_dropped_from_normalized_projection_but_kept_in_raw():
    # trigger=scroll her zaman IGNORE sayılır (PASSIVE_TRIGGERS, bkz. awe.adapter.classification)
    # — motor bu ayrımı role alanına değil yapısal trigger/effect/status'a dayandırır.
    observations = [
        _observation("A", index=0),
        _observation("spinner", index=1, trigger=ObservationTrigger.SCROLL),
        _observation("B", index=2),
    ]

    series = extract_series(observations, OrderingConfidence.HIGH, default_engine_config().family)

    assert len(series) == 1
    assert series[0].symbols == (("A", "route"), ("B", "route"))
    assert len(series[0].raw_observations) == 3
