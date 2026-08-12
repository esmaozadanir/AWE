"""O-Series Builder'ın structural chunk sınırları (bölüm 6.3).

Eski tasarımdan farklı olarak sınır `breaksEpisode` bayrağı ya da "completion effect" tahmini
değil, yalnızca (a) aynı timestamp'te 2+ ACTION-classified event ("ambiguity barrier") ve
(b) `navigation`/`notification`/`deeplink` tetikleyicili bir ACTION'ın akışın ortasında
gelmesiyle çizilir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.domain.enums import ObservationEffect, ObservationTrigger, OrderingConfidence
from awe.series import extract_series
from tests.support.builders import make_observation

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _obs(action, offset_seconds, **kwargs):
    return make_observation(
        action,
        event_id=f"evt-{action}-{offset_seconds}",
        session_id="sess",
        timestamp=_NOW + timedelta(seconds=offset_seconds),
        **kwargs,
    )


def test_empty_input_produces_no_series():
    assert extract_series([], OrderingConfidence.HIGH) == []


def test_sequential_actions_with_no_ties_stay_in_a_single_chunk():
    observations = [
        _obs("open_cart", 0),
        _obs("checkout", 5),
        _obs("confirm", 10, effect=ObservationEffect.CONFIRM),
    ]
    series = extract_series(observations, OrderingConfidence.HIGH)
    assert len(series) == 1
    assert [step.token.action for step in series[0].steps] == ["open_cart", "checkout", "confirm"]
    assert series[0].cut_by_ambiguity is False


def test_context_and_ignore_events_are_kept_in_raw_but_produce_no_steps():
    observations = [
        _obs("open_cart", 0),
        _obs("screen_view", 1, effect=ObservationEffect.VIEW),
        _obs("app_foreground", 2, effect=ObservationEffect.NONE, trigger=ObservationTrigger.AUTOMATIC),
        _obs("checkout", 5),
    ]
    series = extract_series(observations, OrderingConfidence.HIGH)
    assert len(series) == 1
    assert [step.token.action for step in series[0].steps] == ["open_cart", "checkout"]
    assert len(series[0].raw_observations) == 4


def test_same_timestamp_multiple_actions_cut_the_chunk_and_are_excluded_from_steps():
    tie_time = _NOW + timedelta(seconds=5)
    observations = [
        _obs("open_cart", 0),
        make_observation("action_a", event_id="evt-a", session_id="sess", timestamp=tie_time),
        make_observation("action_b", event_id="evt-b", session_id="sess", timestamp=tie_time),
        _obs("checkout", 10),
    ]
    series = extract_series(observations, OrderingConfidence.HIGH)

    assert len(series) == 2
    first, second = series
    assert [step.token.action for step in first.steps] == ["open_cart"]
    assert first.cut_by_ambiguity is True
    # Belirsiz timestamp'teki iki event hiçbir chunk'ın step dizisine girmez ama önceki
    # chunk'ta trailing raw kanıt olarak korunur.
    assert {obs.event_id for obs in first.raw_observations} == {"evt-open_cart-0", "evt-a", "evt-b"}
    assert [step.token.action for step in second.steps] == ["checkout"]
    assert second.cut_by_ambiguity is False


def test_mid_flow_notification_trigger_starts_a_new_chunk():
    observations = [
        _obs("open_cart", 0),
        _obs("open_promo", 5, trigger=ObservationTrigger.NOTIFICATION),
        _obs("apply_promo", 10),
    ]
    series = extract_series(observations, OrderingConfidence.HIGH)

    assert len(series) == 2
    assert [step.token.action for step in series[0].steps] == ["open_cart"]
    assert [step.token.action for step in series[1].steps] == ["open_promo", "apply_promo"]
    assert series[1].entry_trigger == ObservationTrigger.NOTIFICATION


def test_notification_trigger_as_the_very_first_action_does_not_cut():
    observations = [
        _obs("open_promo", 0, trigger=ObservationTrigger.NOTIFICATION),
        _obs("apply_promo", 5),
    ]
    series = extract_series(observations, OrderingConfidence.HIGH)

    assert len(series) == 1
    assert [step.token.action for step in series[0].steps] == ["open_promo", "apply_promo"]


def test_has_shortcut_trigger_reflects_any_shortcut_triggered_observation_in_the_chunk():
    observations = [
        _obs("open_cart", 0, trigger=ObservationTrigger.SHORTCUT),
        _obs("checkout", 5),
    ]
    series = extract_series(observations, OrderingConfidence.HIGH)
    assert series[0].has_shortcut_trigger is True


def test_different_sessions_are_not_mixed_by_this_function():
    """`extract_series` tek bir session'ın zaten sıralanmış listesini işler; session ayrımı
    çağıranın (services/analysis.py) sorumluluğudur — burada yalnızca girdi tek session'lıkken
    doğru davranıldığı doğrulanır (bkz. entry_screen/session_id tutarlılığı)."""
    observations = [_obs("open_cart", 0), _obs("checkout", 5)]
    series = extract_series(observations, OrderingConfidence.HIGH)
    assert all(s.session_id == "sess" for s in series)
