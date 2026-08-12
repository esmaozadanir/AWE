"""Bölüm 100-113'teki tüm profil matrisinin sentetik üretici + gerçek pipeline üzerinden
uçtan uca doğrulaması. Bu test, katmanların izole testlerinden farklı olarak ingestion'dan
suggestion'a kadar tüm zincirin, üretici tarafından etiketlenen ground truth ile eşleştiğini
doğrular.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from awe.config import ProjectRegistry
from awe.persistence import Base, create_database_engine, create_session_factory, session_scope
from awe.risk import ResolverContract
from awe.services import analyze_subject, ingest_batch
from awe.testing import PROFILE_NAMES, generate_subject

_BASE = datetime(2026, 1, 1, 9, tzinfo=UTC)


@pytest.fixture
def session_factory():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


@pytest.mark.parametrize("profile", PROFILE_NAMES)
def test_synthetic_profile_matches_expected_habit_decision(session_factory, profile):
    project_config = ProjectRegistry("config_examples").get("shopwave")
    generated = generate_subject(profile, "shopwave", f"subj_{profile}", seed=42, base_time=_BASE)

    with session_scope(session_factory) as session:
        outcomes = ingest_batch(session, project_config, "shopwave", generated.events, _BASE)
        assert all(o.accepted for o in outcomes), [o for o in outcomes if not o.accepted]

    now = _BASE + timedelta(days=200)
    with session_scope(session_factory) as session:
        summary = analyze_subject(
            session, project_config, "shopwave", f"subj_{profile}", ResolverContract.permissive(), now
        )

    assert len(summary.families) >= 1, f"{profile}: hicbir family olusmadi"
    actual = summary.families[0].habit_decision
    assert actual == generated.expected_habit_decision, (
        f"{profile}: beklenen={generated.expected_habit_decision.value} gercek={actual.value}"
    )
