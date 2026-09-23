"""Proje bazlı konfigürasyon: hangi Adapter mapping'i, hangi timezone, hangi eşik override'ları.

MVP kapsamında bölüm 97'nin API listesinde bir config-upload endpoint'i bulunmuyor; bu yüzden
proje konfigürasyonları `config_examples/` altında dosya tabanlı olarak tutulur ve
`ProjectRegistry` tarafından yüklenir (IMPLEMENTATION_PLAN.md bölüm 8). Gerçek bir çok-kiracılı
sistemde bu, `_build_mapping`/`_build_engine_overrides` değiştirilerek bir config-upload
API'sine bağlanabilir; bu genişletme noktası bilinçli bir MVP sınırlamasıdır.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml

from awe.adapter.mapping import AdapterMapping, FieldRule, TargetRule
from awe.config.engine_config import EngineConfig, default_engine_config


class ProjectNotFoundError(KeyError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class DeliveryConfig:
    """Önerilerin dış sunucuya geri gönderilmesi (giden yön) için opsiyonel hedef -- `mapping`in
    (gelen yön) simetriği. Varsayılan `enabled=False`: `delivery:` bölümü olmayan projeler
    hiçbir davranış değişikliği görmez."""

    enabled: bool = False
    push_url: str | None = None
    auth_env_var: str | None = None
    """Ayarlıysa, gönderim isteğine `Authorization: Bearer <.env'deki bu değişkenin değeri>`
    eklenir. Hedef servisin gerçek auth şeması netleşene kadarki bilinen bir v1 varsayımı."""


@dataclasses.dataclass(frozen=True, slots=True)
class PullConfig:
    """Dış sunucudan ham veri çekmek için opsiyonel kaynak -- `delivery`nin (giden) simetriği.
    Yalnızca KİMLİK DOĞRULAMA + HAM VERİYİ GETİRME jeneriktir; çekilen ham veriyi AWE'nin
    canonical event şekline çevirme (TRANSFORM) her zaman servise özeldir ve burada YOKTUR --
    bkz. `scripts/external_sync_template.py`."""

    enabled: bool = False
    pull_url: str | None = None
    auth_type: str = "none"
    """"none" | "bearer_env" | "login_then_bearer" """
    auth_env_var: str | None = None
    """`auth_type="bearer_env"` için: token'ın okunacağı .env değişkeninin adı."""
    login_url: str | None = None
    login_email_env_var: str | None = None
    login_password_env_var: str | None = None
    """`auth_type="login_then_bearer"` için: giriş isteğinin adresi ve kimlik bilgilerinin
    .env değişken adları (CompanyHelper'daki email+şifre->JWT akışıyla aynı desen)."""


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectConfig:
    project_id: str
    display_name: str
    mapping: AdapterMapping
    engine: EngineConfig
    delivery: DeliveryConfig = dataclasses.field(default_factory=DeliveryConfig)
    pull: PullConfig = dataclasses.field(default_factory=PullConfig)


def _build_field_rule(data: dict[str, Any] | None) -> FieldRule:
    data = data or {}
    return FieldRule(
        path=data.get("path"),
        value_map=data.get("value_map", {}),
        default=data.get("default", "unknown"),
    )


def _build_mapping(data: dict[str, Any]) -> AdapterMapping:
    target_data = data.get("target", {})
    return AdapterMapping(
        mapping_version=data["mapping_version"],
        event_id_path=data["event_id_path"],
        project_id_path=data["project_id_path"],
        subject_id_path=data["subject_id_path"],
        session_id_path=data["session_id_path"],
        timestamp_path=data["timestamp_path"],
        action_key_path=data["action_key_path"],
        action_key_value_map=data.get("action_key_value_map", {}),
        screen_path=data.get("screen_path"),
        duration_path=data.get("duration_path"),
        source=_build_field_rule(data.get("source")),
        effect=_build_field_rule(data.get("effect")),
        trigger=_build_field_rule(data.get("trigger")),
        status=_build_field_rule(data.get("status")),
        target=TargetRule(ref_path=target_data.get("ref_path")),
    )


def _build_delivery(data: dict[str, Any] | None) -> DeliveryConfig:
    data = data or {}
    return DeliveryConfig(
        enabled=data.get("enabled", False),
        push_url=data.get("push_url"),
        auth_env_var=data.get("auth_env_var"),
    )


def _build_pull(data: dict[str, Any] | None) -> PullConfig:
    data = data or {}
    return PullConfig(
        enabled=data.get("enabled", False),
        pull_url=data.get("pull_url"),
        auth_type=data.get("auth_type", "none"),
        auth_env_var=data.get("auth_env_var"),
        login_url=data.get("login_url"),
        login_email_env_var=data.get("login_email_env_var"),
        login_password_env_var=data.get("login_password_env_var"),
    )


def _build_engine_overrides(data: dict[str, Any] | None, timezone: str) -> EngineConfig:
    base = default_engine_config()
    if not data:
        return dataclasses.replace(base, timezone=timezone)

    section_names = ("episode", "habit", "screen_evidence", "risk", "lifecycle")
    updated_sections: dict[str, Any] = {}
    for section_name in section_names:
        overrides = data.get(section_name)
        if overrides:
            current = getattr(base, section_name)
            updated_sections[section_name] = dataclasses.replace(current, **overrides)
    return dataclasses.replace(base, timezone=timezone, **updated_sections)


def load_project_config(path: Path) -> ProjectConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    timezone = data.get("timezone", "UTC")
    return ProjectConfig(
        project_id=data["project_id"],
        display_name=data.get("display_name", data["project_id"]),
        mapping=_build_mapping(data["mapping"]),
        engine=_build_engine_overrides(data.get("engine_overrides"), timezone),
        delivery=_build_delivery(data.get("delivery")),
        pull=_build_pull(data.get("pull")),
    )


class ProjectRegistry:
    """`config_examples/` altındaki proje YAML dosyalarını yükler ve önbelleğe alır."""

    def __init__(self, config_dir: str | Path) -> None:
        self._config_dir = Path(config_dir)
        self._cache: dict[str, ProjectConfig] = {}

    def get(self, project_id: str) -> ProjectConfig:
        if project_id in self._cache:
            return self._cache[project_id]
        candidate = self._config_dir / f"{project_id}.yaml"
        if not candidate.exists():
            raise ProjectNotFoundError(project_id)
        config = load_project_config(candidate)
        if config.project_id != project_id:
            raise ValueError(
                f"config file '{candidate}' declares project_id '{config.project_id}', expected '{project_id}'"
            )
        self._cache[project_id] = config
        return config

    def known_project_ids(self) -> list[str]:
        return sorted(p.stem for p in self._config_dir.glob("*.yaml"))
