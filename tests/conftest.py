from __future__ import annotations

from pathlib import Path

import pytest

from awe.config import ProjectRegistry
from awe.persistence import Base, create_database_engine, create_session_factory

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config_examples"


@pytest.fixture
def session_factory():
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


@pytest.fixture
def project_registry() -> ProjectRegistry:
    return ProjectRegistry(_CONFIG_DIR)
