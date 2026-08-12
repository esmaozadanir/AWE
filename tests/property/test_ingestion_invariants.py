"""Bölüm 123: property-based invariant testleri — Duplicate batch idempotency."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from awe.config import ProjectRegistry
from awe.persistence import Base, create_database_engine, create_session_factory, session_scope
from awe.services import ingest_batch

_BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)
_REGISTRY = ProjectRegistry("config_examples")
_PROJECT_CONFIG = _REGISTRY.get("shopwave")


def _events(day_count: int) -> list[dict]:
    events = []
    for day in range(day_count):
        ts = (_BASE + timedelta(days=day)).isoformat()
        events.append(
            {
                "eventId": f"evt-{day}",
                "projectId": "shopwave",
                "subjectId": "user_1",
                "sessionId": f"sess-{day}",
                "timestamp": ts,
                "source": "client",
                "actionKey": "open_settings",
                "role": "action",
                "effect": "route",
                "trigger": "button",
                "screen": "settings",
                "widget": None,
                "target": None,
                "status": "success",
                "breaksEpisode": False,
                "metadata": {},
            }
        )
    return events


@given(day_count=st.integers(min_value=1, max_value=10))
@settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_ingesting_the_same_batch_twice_never_doubles_accepted_events(day_count):
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)

    events = _events(day_count)

    with session_scope(factory) as session:
        first_pass = ingest_batch(session, _PROJECT_CONFIG, "shopwave", events, _BASE)
    with session_scope(factory) as session:
        second_pass = ingest_batch(session, _PROJECT_CONFIG, "shopwave", events, _BASE)

    first_accepted = sum(1 for o in first_pass if o.accepted and not o.duplicate)
    second_accepted = sum(1 for o in second_pass if o.accepted and not o.duplicate)
    second_duplicates = sum(1 for o in second_pass if o.duplicate)

    assert first_accepted == day_count
    assert second_accepted == 0
    assert second_duplicates == day_count
