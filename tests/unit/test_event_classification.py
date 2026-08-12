"""`classify_event`in ACTION/CONTEXT/IGNORE kararı: yalnızca trigger/effect/status'a dayanır.

`role` alanına ya da müşteriye özel `action`/`screen`/`widget` string'lerine hiçbir zaman
bakılmadığını (bkz. `awe.adapter.classification`) doğrudan doğrular.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from awe.adapter.classification import classify_event
from awe.config import default_engine_config
from awe.domain.enums import (
    EventClassification,
    ObservationEffect,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.ordering import order_session
from awe.series import extract_series
from tests.support.builders import make_observation

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_FAMILY_CONFIG = default_engine_config().family


def _classify(
    *,
    trigger: ObservationTrigger,
    effect: ObservationEffect,
    status: ObservationStatus = ObservationStatus.SUCCESS,
    source: ObservationSource = ObservationSource.CLIENT,
    screen: str | None = "screen",
    target: str | None = None,
) -> EventClassification:
    observation = make_observation(
        "some_action",
        event_id="evt1",
        session_id="sess",
        timestamp=_NOW,
        trigger=trigger,
        effect=effect,
        status=status,
        source=source,
        screen=screen,
        target=target,
    )
    return classify_event(observation)


_TRIGGER_EFFECT_CASE_IDS = [
    "1_button_route",
    "2_button_view",
    "3_automatic_view",
    "4_automatic_route",
    "5_automatic_update",
    "6_swipe_delete",
    "7_swipe_view",
    "8_scroll_query",
    "9_hover_open_modal",
    "10_api_route",
    "11_webhook_update",
    "12_admin_create",
    "13_shortcut_route",
    "17_notification_route",
    "18_deeplink_route",
]
_TRIGGER_EFFECT_CASES = [
    (ObservationTrigger.BUTTON, ObservationEffect.ROUTE, EventClassification.ACTION),
    (ObservationTrigger.BUTTON, ObservationEffect.VIEW, EventClassification.CONTEXT),
    (ObservationTrigger.AUTOMATIC, ObservationEffect.VIEW, EventClassification.CONTEXT),
    (ObservationTrigger.AUTOMATIC, ObservationEffect.ROUTE, EventClassification.CONTEXT),
    (ObservationTrigger.AUTOMATIC, ObservationEffect.UPDATE, EventClassification.IGNORE),
    (ObservationTrigger.SWIPE, ObservationEffect.DELETE, EventClassification.ACTION),
    (ObservationTrigger.SWIPE, ObservationEffect.VIEW, EventClassification.IGNORE),
    (ObservationTrigger.SCROLL, ObservationEffect.QUERY, EventClassification.IGNORE),
    (ObservationTrigger.HOVER, ObservationEffect.OPEN_MODAL, EventClassification.IGNORE),
    (ObservationTrigger.API, ObservationEffect.ROUTE, EventClassification.IGNORE),
    (ObservationTrigger.WEBHOOK, ObservationEffect.UPDATE, EventClassification.IGNORE),
    (ObservationTrigger.ADMIN, ObservationEffect.CREATE, EventClassification.IGNORE),
    (ObservationTrigger.SHORTCUT, ObservationEffect.ROUTE, EventClassification.IGNORE),
    (ObservationTrigger.NOTIFICATION, ObservationEffect.ROUTE, EventClassification.ACTION),
    (ObservationTrigger.DEEPLINK, ObservationEffect.ROUTE, EventClassification.ACTION),
]


@pytest.mark.parametrize(("trigger", "effect", "expected"), _TRIGGER_EFFECT_CASES, ids=_TRIGGER_EFFECT_CASE_IDS)
def test_classification_by_trigger_and_effect(trigger, effect, expected):
    assert _classify(trigger=trigger, effect=effect) == expected


@pytest.mark.parametrize(
    "effect",
    [ObservationEffect.NONE, ObservationEffect.UNKNOWN],
    ids=["none", "unknown"],
)
def test_case_14_empty_effect_is_always_ignored(effect):
    assert _classify(trigger=ObservationTrigger.BUTTON, effect=effect) == EventClassification.IGNORE


@pytest.mark.parametrize(
    "status",
    [ObservationStatus.FAIL, ObservationStatus.CANCEL, ObservationStatus.PARTIAL, ObservationStatus.UNKNOWN],
    ids=["failed", "cancelled", "pending", "unknown"],
)
def test_case_15_non_success_status_is_always_ignored_even_for_an_otherwise_actionable_event(status):
    assert (
        _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.ROUTE, status=status)
        == EventClassification.IGNORE
    )


def test_case_16_server_source_does_not_exclude_a_real_user_action():
    result = _classify(
        trigger=ObservationTrigger.BUTTON,
        effect=ObservationEffect.SUBMIT,
        source=ObservationSource.SERVER,
    )
    assert result == EventClassification.ACTION


@pytest.mark.parametrize("target", [None, "opaque_ref_1"], ids=["no_target", "with_target"])
def test_case_19_target_presence_never_changes_classification(target):
    result = _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.ROUTE, target=target)
    assert result == EventClassification.ACTION


@pytest.mark.parametrize("screen", [None, "checkout"], ids=["no_screen", "with_screen"])
def test_case_20_screen_presence_never_changes_classification(screen):
    result = _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.ROUTE, screen=screen)
    assert result == EventClassification.ACTION


def test_case_21_two_sessions_action_flows_never_merge():
    session_a = [
        make_observation("open_cart", event_id="a1", session_id="sess-a", timestamp=_NOW),
        make_observation(
            "checkout", event_id="a2", session_id="sess-a", timestamp=_NOW + timedelta(seconds=1)
        ),
    ]
    session_b = [
        make_observation(
            "open_settings", event_id="b1", session_id="sess-b", timestamp=_NOW + timedelta(seconds=2)
        ),
    ]

    series_a = extract_series(session_a, OrderingConfidence.HIGH, _FAMILY_CONFIG)
    series_b = extract_series(session_b, OrderingConfidence.HIGH, _FAMILY_CONFIG)

    assert {s.session_id for s in series_a} == {"sess-a"}
    assert {s.session_id for s in series_b} == {"sess-b"}
    assert series_a[0].symbols == (("open_cart", "route"), ("checkout", "route"))
    assert series_b[0].symbols == (("open_settings", "route"),)


def test_case_22_identical_timestamps_do_not_crash_and_stay_deterministic():
    observations = [
        make_observation("C", event_id="evt-c", session_id="sess", timestamp=_NOW),
        make_observation("A", event_id="evt-a", session_id="sess", timestamp=_NOW),
        make_observation("B", event_id="evt-b", session_id="sess", timestamp=_NOW),
    ]

    ordered_first, confidence_first = order_session(observations)
    ordered_second, confidence_second = order_session(list(reversed(observations)))

    assert [o.event_id for o in ordered_first] == [o.event_id for o in ordered_second]
    assert confidence_first == confidence_second
