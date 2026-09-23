"""Suggestion delivery: durum takibi (awe.services.suggestions.list_pending_deliveries /
record_delivery) + gerçek gönderim (push_pending). Gönderim testleri için gerçek bir dış
sunucu olmadığı için `httpx.MockTransport` kullanılır (bkz. tests/unit/test_pull_client.py) --
kendi kodumuz mock'lanmaz, yalnızca ağ katmanı sahte."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig
from awe.config.project_config import DeliveryConfig, ProjectConfig
from awe.domain.benefit import BenefitEvidence
from awe.domain.enums import (
    AnchorStatus,
    AnchorStrength,
    AutomaticAction,
    EffectPolicy,
    ExecutionExposure,
    FinalActionOwner,
    IntentState,
    PlanMode,
    RiskDecision,
)
from awe.domain.plan import Scope, ShortcutAnchor, ShortcutIntent
from awe.domain.risk import ReliabilityEvidence, RiskAssessment, RiskEvidence
from awe.persistence import Base, create_database_engine, create_session_factory
from awe.persistence.repository import replace_shortcut_intents, upsert_suggestion
from awe.services import list_pending_deliveries, push_pending, record_delivery

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_INTENT_KEY = "intent_test1"
_MAPPING = AdapterMapping(
    mapping_version="delivery-test-v1",
    event_id_path="eventId",
    project_id_path="projectId",
    subject_id_path="subjectId",
    session_id_path="sessionId",
    timestamp_path="timestamp",
    action_key_path="actionKey",
    source=FieldRule(path="source", default="unknown"),
    effect=FieldRule(path="effect", default="unknown"),
    trigger=FieldRule(path="trigger", default="unknown"),
    status=FieldRule(path="status", default="unknown"),
    target=TargetRule(ref_path="target"),
)


def _session():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)()


def _seed_suggestion(session, now: datetime = _NOW) -> str:
    """`proj`/`subj` için gerçek servis/repository fonksiyonlarıyla (mock yok) minimal ama
    geçerli bir SuggestionRecord + ShortcutIntentRecord kurar; üretilen `suggestion_key`i
    döner."""
    anchor = ShortcutAnchor(
        symbol=("open_item", "route", "detail", "v1"),
        position=0,
        strength=AnchorStrength.STRONG,
        status=AnchorStatus.RESOLVED,
    )
    intent = ShortcutIntent(
        intent_id=_INTENT_KEY,
        variant_id="var1",
        anchor=anchor,
        state=IntentState.READY,
        mode=PlanMode.PREFILL,
        destination_screen="detail",
        target="item_1",
        requires_user_confirmation=True,
        automatic_action=AutomaticAction.NONE,
        final_action_owner=FinalActionOwner.USER,
        supporting_occurrences=3,
    )
    scope = Scope(variant_id="var1", included=(anchor.symbol,), excluded_trailing=())
    risk = RiskAssessment(
        intent_id=_INTENT_KEY,
        decision=RiskDecision.ALLOW,
        evidence=RiskEvidence(
            policy=EffectPolicy.SAFE,
            plan_surface=PlanMode.PREFILL,
            execution_exposure=ExecutionExposure.NONE,
            interaction_guard_intact=True,
            observed_goal_sensitivity=EffectPolicy.SAFE,
            reliability=ReliabilityEvidence(completion_rate=1.0, failure_rate=0.0, cancel_rate=0.0, sample_size=3),
            data_quality_ok=True,
        ),
    )
    benefit = BenefitEvidence(intent_id=_INTENT_KEY, observed_actions=3, planned_actions=1)

    replace_shortcut_intents(
        session, "proj", "subj", [(intent, scope, "fam1", risk, benefit, "selected", [])], now
    )
    record = upsert_suggestion(session, "proj", "subj", "fam1", "var1", _INTENT_KEY, "active", [], now, None, None)
    session.commit()
    return record.suggestion_key


def test_new_suggestion_is_pending_delivery():
    session = _session()
    _seed_suggestion(session)

    pending = list_pending_deliveries(session, "proj", "subj")

    assert len(pending) == 1
    assert pending[0].delivered_at is None


def test_record_delivery_success_removes_it_from_pending():
    session = _session()
    suggestion_key = _seed_suggestion(session)
    delivered_at = _NOW + timedelta(minutes=5)

    view = record_delivery(session, "proj", "subj", suggestion_key, delivered_at)
    session.commit()

    assert view is not None
    assert view.delivered_at == delivered_at
    assert view.delivery_error is None
    assert list_pending_deliveries(session, "proj", "subj") == []


def test_record_delivery_error_keeps_it_pending_and_records_the_message():
    session = _session()
    suggestion_key = _seed_suggestion(session)

    view = record_delivery(
        session, "proj", "subj", suggestion_key, _NOW + timedelta(minutes=5), error="connection refused"
    )
    session.commit()

    assert view is not None
    assert view.delivered_at is None
    assert view.delivery_error == "connection refused"
    pending = list_pending_deliveries(session, "proj", "subj")
    assert len(pending) == 1
    assert pending[0].suggestion_key == suggestion_key


def test_suggestion_becomes_pending_again_after_being_updated():
    session = _session()
    suggestion_key = _seed_suggestion(session)
    record_delivery(session, "proj", "subj", suggestion_key, _NOW + timedelta(minutes=5))
    session.commit()
    assert list_pending_deliveries(session, "proj", "subj") == []

    later = _NOW + timedelta(hours=1)
    upsert_suggestion(session, "proj", "subj", "fam1", "var1", _INTENT_KEY, "active", [], later, None, None)
    session.commit()

    pending = list_pending_deliveries(session, "proj", "subj")
    assert len(pending) == 1
    assert pending[0].suggestion_key == suggestion_key


def test_record_delivery_unknown_key_returns_none():
    session = _session()
    _seed_suggestion(session)

    assert record_delivery(session, "proj", "subj", "does-not-exist", _NOW) is None


def test_push_pending_fails_fast_when_delivery_disabled():
    project_config = ProjectConfig(
        project_id="proj",
        display_name="Test",
        mapping=_MAPPING,
        engine=EngineConfig(),
        delivery=DeliveryConfig(enabled=False),
    )
    result = push_pending(_session(), project_config, "proj", "subj", _NOW)

    assert result.success is False
    assert "delivery.enabled" in result.error


def test_push_pending_fails_when_push_url_missing():
    project_config = ProjectConfig(
        project_id="proj",
        display_name="Test",
        mapping=_MAPPING,
        engine=EngineConfig(),
        delivery=DeliveryConfig(enabled=True, push_url=None),
    )
    result = push_pending(_session(), project_config, "proj", "subj", _NOW)

    assert result.success is False
    assert "push_url" in result.error


def test_push_pending_sends_pending_suggestion_and_marks_it_delivered():
    session = _session()
    _seed_suggestion(session)

    sent_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/suggestions"
        sent_payloads.append(request.content)
        return httpx.Response(200, json={"ok": True})

    project_config = ProjectConfig(
        project_id="proj",
        display_name="Test",
        mapping=_MAPPING,
        engine=EngineConfig(),
        delivery=DeliveryConfig(enabled=True, push_url="https://fake.example.com/suggestions"),
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = push_pending(session, project_config, "proj", "subj", _NOW + timedelta(minutes=5), client=client)

    assert result.success is True
    assert result.pushed_count == 1
    assert result.push_failed_count == 0
    assert len(sent_payloads) == 1
    assert list_pending_deliveries(session, "proj", "subj") == []


def test_push_pending_records_failure_and_leaves_it_pending():
    session = _session()
    _seed_suggestion(session)

    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    project_config = ProjectConfig(
        project_id="proj",
        display_name="Test",
        mapping=_MAPPING,
        engine=EngineConfig(),
        delivery=DeliveryConfig(enabled=True, push_url="https://fake.example.com/suggestions"),
    )
    client = httpx.Client(transport=httpx.MockTransport(failing_handler))

    result = push_pending(session, project_config, "proj", "subj", _NOW + timedelta(minutes=5), client=client)

    assert result.success is True
    assert result.pushed_count == 0
    assert result.push_failed_count == 1
    pending = list_pending_deliveries(session, "proj", "subj")
    assert len(pending) == 1
    assert pending[0].delivery_error is not None
