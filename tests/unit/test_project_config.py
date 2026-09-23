"""ProjectConfig / delivery config parsing (bkz. awe.config.project_config)."""

from __future__ import annotations

from pathlib import Path

from awe.config import ProjectRegistry
from awe.config.project_config import load_project_config

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config_examples"

_MINIMAL_YAML = """
project_id: testproj
display_name: "Test"
timezone: "UTC"
mapping:
  mapping_version: "test-v1"
  event_id_path: eventId
  project_id_path: projectId
  subject_id_path: subjectId
  session_id_path: sessionId
  timestamp_path: timestamp
  action_key_path: actionKey
"""


def test_known_config_examples_load_with_delivery_disabled_by_default():
    """Geriye dönük uyumluluk regresyonu: `delivery:` bölümü hiçbir mevcut config'te yok --
    hepsi hâlâ hatasız yüklenmeli ve varsayılan olarak `enabled=False` dönmeli."""
    registry = ProjectRegistry(_CONFIG_DIR)
    project_ids = registry.known_project_ids()
    assert len(project_ids) > 0

    for project_id in project_ids:
        config = registry.get(project_id)
        assert config.delivery.enabled is False
        assert config.delivery.push_url is None
        assert config.delivery.auth_env_var is None
        assert config.pull.enabled is False
        assert config.pull.pull_url is None
        assert config.pull.auth_type == "none"


def test_delivery_section_defaults_to_disabled_when_absent(tmp_path):
    config_path = tmp_path / "testproj.yaml"
    config_path.write_text(_MINIMAL_YAML, encoding="utf-8")

    config = load_project_config(config_path)

    assert config.delivery.enabled is False
    assert config.delivery.push_url is None


def test_delivery_section_parses_when_present(tmp_path):
    yaml_text = (
        _MINIMAL_YAML
        + """delivery:
  enabled: true
  push_url: "https://example.com/suggestions"
  auth_env_var: "TESTPROJ_PUSH_TOKEN"
"""
    )
    config_path = tmp_path / "testproj.yaml"
    config_path.write_text(yaml_text, encoding="utf-8")

    config = load_project_config(config_path)

    assert config.delivery.enabled is True
    assert config.delivery.push_url == "https://example.com/suggestions"
    assert config.delivery.auth_env_var == "TESTPROJ_PUSH_TOKEN"


def test_pull_section_defaults_to_disabled_when_absent(tmp_path):
    config_path = tmp_path / "testproj.yaml"
    config_path.write_text(_MINIMAL_YAML, encoding="utf-8")

    config = load_project_config(config_path)

    assert config.pull.enabled is False
    assert config.pull.pull_url is None
    assert config.pull.auth_type == "none"


def test_pull_section_parses_login_then_bearer(tmp_path):
    yaml_text = (
        _MINIMAL_YAML
        + """pull:
  enabled: true
  pull_url: "https://example.com/api/data/export"
  auth_type: "login_then_bearer"
  login_url: "https://example.com/auth/login"
  login_email_env_var: "TESTPROJ_EMAIL"
  login_password_env_var: "TESTPROJ_PASSWORD"
"""
    )
    config_path = tmp_path / "testproj.yaml"
    config_path.write_text(yaml_text, encoding="utf-8")

    config = load_project_config(config_path)

    assert config.pull.enabled is True
    assert config.pull.pull_url == "https://example.com/api/data/export"
    assert config.pull.auth_type == "login_then_bearer"
    assert config.pull.login_url == "https://example.com/auth/login"
    assert config.pull.login_email_env_var == "TESTPROJ_EMAIL"
    assert config.pull.login_password_env_var == "TESTPROJ_PASSWORD"
