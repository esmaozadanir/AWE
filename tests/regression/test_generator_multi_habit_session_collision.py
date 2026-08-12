"""Regresyon: `generate_multi_habit_subject`, farklı bileşenlerin aynı gün/session_index
kombinasyonuna düşüp aynı session_id'yi paylaşması ve event akışlarının birbirine karışması.

Bulunan hata: `_OccurrenceSpec.session_prefix` eklenmeden önce, örn. `daily_regular` bileşeninin
0. günü ile `weekly_regular` bileşeninin 0. günü aynı `sess-<subject>-0-0` session_id'sini
üretiyordu; bu da tek bir session içinde iki farklı davranışın event'lerinin karışmasına ve
4 bağımsız Habit yerine ~19 parçalanmış family oluşmasına yol açıyordu.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from awe.config import ProjectRegistry
from awe.domain.enums import HabitDecision
from awe.persistence import Base, create_database_engine, create_session_factory, session_scope
from awe.risk import ResolverContract
from awe.services import analyze_subject, ingest_batch
from awe.testing import generate_multi_habit_subject

_BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)


def test_multi_habit_components_do_not_share_sessions_or_fragment_families():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    project_config = ProjectRegistry("config_examples").get("shopwave")

    generated = generate_multi_habit_subject("shopwave", "multi_regression", seed=7, base_time=_BASE)

    with session_scope(factory) as session:
        outcomes = ingest_batch(session, project_config, "shopwave", generated.events, _BASE)
        assert all(o.accepted for o in outcomes)

    now = _BASE + timedelta(days=200)
    with session_scope(factory) as session:
        summary = analyze_subject(
            session, project_config, "shopwave", "multi_regression", ResolverContract.permissive(), now
        )

    assert len(summary.families) == len(generated.component_profiles)
    assert all(f.habit_decision == HabitDecision.PASS for f in summary.families)
