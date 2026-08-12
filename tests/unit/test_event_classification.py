"""`classify_event`in ACTION/CONTEXT/IGNORE kararı (bölüm 6.2).

Yalnızca `effect`/`source`/`trigger` üçlüsüne dayanır. `status` hiçbir zaman sınıflandırmayı
etkilemez (bölüm 3 kural 4); `target`/`screen` varlığı da etkilemez.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from awe.adapter.classification import classify_event
from awe.domain.enums import (
    EventClassification,
    ObservationEffect,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)
from tests.support.builders import make_observation

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)


def _classify(
    *,
    trigger: ObservationTrigger,
    effect: ObservationEffect,
    source: ObservationSource = ObservationSource.CLIENT,
    status: ObservationStatus = ObservationStatus.SUCCESS,
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
        source=source,
        status=status,
        screen=screen,
        target=target,
    )
    return classify_event(observation)


def test_case_1_empty_effect_is_always_ignored():
    assert (
        _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.NONE) == EventClassification.IGNORE
    )


@pytest.mark.parametrize(
    "trigger",
    [ObservationTrigger.BUTTON, ObservationTrigger.AUTOMATIC, ObservationTrigger.SWIPE],
    ids=["user_trigger", "automatic_trigger", "gesture_trigger"],
)
def test_case_2_view_effect_is_always_context_regardless_of_trigger(trigger):
    assert _classify(trigger=trigger, effect=ObservationEffect.VIEW) == EventClassification.CONTEXT


@pytest.mark.parametrize("source", [ObservationSource.SERVER, ObservationSource.SYSTEM])
def test_case_3_non_client_source_is_always_context_even_for_an_otherwise_actionable_event(source):
    """Bilinçli davranış: önceki tasarımın tersine, `source != client` artık her zaman CONTEXT
    üretir (bölüm 6.2) — final raporda bu tersine dönüş açıkça belirtilir."""
    result = _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.SUBMIT, source=source)
    assert result == EventClassification.CONTEXT


def test_case_4_automatic_trigger_is_context_even_for_a_non_view_effect():
    result = _classify(trigger=ObservationTrigger.AUTOMATIC, effect=ObservationEffect.UPDATE)
    assert result == EventClassification.CONTEXT


@pytest.mark.parametrize(
    "trigger",
    [
        ObservationTrigger.BUTTON,
        ObservationTrigger.KEYBOARD,
        ObservationTrigger.VOICE,
        ObservationTrigger.LONG_PRESS,
        ObservationTrigger.HARDWARE,
        ObservationTrigger.BIOMETRIC,
        ObservationTrigger.SWIPE,
        ObservationTrigger.DRAG,
        ObservationTrigger.NAVIGATION,
        ObservationTrigger.NOTIFICATION,
        ObservationTrigger.DEEPLINK,
    ],
)
def test_case_5_user_triggers_produce_action_for_a_non_view_effect(trigger):
    assert _classify(trigger=trigger, effect=ObservationEffect.SUBMIT) == EventClassification.ACTION


def test_case_6_shortcut_trigger_produces_action():
    """`shortcut` belgenin trigger sözlüğünde yok (bkz. `ObservationTrigger.SHORTCUT`
    docstring'i) — kasıtlı ek: bir kısayolun tetiklediği event de gerçek bir ACTION'dır."""
    assert (
        _classify(trigger=ObservationTrigger.SHORTCUT, effect=ObservationEffect.ROUTE)
        == EventClassification.ACTION
    )


def test_case_7_unknown_trigger_falls_through_to_context():
    assert (
        _classify(trigger=ObservationTrigger.UNKNOWN, effect=ObservationEffect.SUBMIT)
        == EventClassification.CONTEXT
    )


@pytest.mark.parametrize(
    "status",
    [ObservationStatus.FAIL, ObservationStatus.CANCEL, ObservationStatus.UNKNOWN],
)
def test_case_8_status_never_changes_classification(status):
    """Bölüm 3 kural 4: status=fail/cancel olan kullanıcı ACTION'ları diziden atılmaz."""
    result = _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.ROUTE, status=status)
    assert result == EventClassification.ACTION


@pytest.mark.parametrize("target", [None, "opaque_ref_1"], ids=["no_target", "with_target"])
def test_case_9_target_presence_never_changes_classification(target):
    result = _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.ROUTE, target=target)
    assert result == EventClassification.ACTION


@pytest.mark.parametrize("screen", [None, "checkout"], ids=["no_screen", "with_screen"])
def test_case_10_screen_presence_never_changes_classification(screen):
    result = _classify(trigger=ObservationTrigger.BUTTON, effect=ObservationEffect.ROUTE, screen=screen)
    assert result == EventClassification.ACTION
