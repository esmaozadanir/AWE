"""Raw event → canonical Observation dönüşümü.

AWE Core, bu modülden sonra hiçbir yerde müşterinin ham telemetry alan adlarını görmez
(bölüm 31: "AWE Core müşterinin özel telemetry formatını bilmemelidir").
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from awe.adapter.mapping import AdapterMapping, resolve_path
from awe.domain.enums import (
    ObservationEffect,
    ObservationRole,
    ObservationSource,
    ObservationStatus,
    ObservationTrigger,
)
from awe.domain.observation import Observation, ObservationQuality


class AdapterValidationError(ValueError):
    """Raw event, mapping ile zorunlu alanları üretemeyecek kadar eksik/bozuk."""


def _require_str(raw: dict, path: str, *, field_name: str) -> str:
    value = resolve_path(raw, path)
    if value is None or str(value).strip() == "":
        raise AdapterValidationError(f"required field '{field_name}' missing at path '{path}'")
    return str(value).strip()


def _parse_timestamp(raw_value: str, mapping: AdapterMapping, warnings: list[str]) -> datetime:
    normalized = raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AdapterValidationError(f"unparseable timestamp: {raw_value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(mapping.assume_timezone))
        warnings.append(f"naive_timestamp_assumed_{mapping.assume_timezone}")
    return parsed.astimezone(UTC)


def _resolve_target(raw: dict, mapping: AdapterMapping) -> str | None:
    """Mapping target'ı hiç izlemiyorsa `None` (bilinmiyor), izliyor ama bu event'in raw
    değeri boşsa `""` (açıkça hedef yok), aksi halde ref string'i döner (bkz.
    `Observation.target` docstring'i)."""

    if mapping.target.ref_path is None:
        return None
    ref_value = resolve_path(raw, mapping.target.ref_path)
    return str(ref_value) if ref_value is not None else ""


def _resolve_action(raw: dict, mapping: AdapterMapping) -> str:
    raw_value = _require_str(raw, mapping.action_key_path, field_name="action")
    return mapping.action_key_value_map.get(raw_value, raw_value)


def _resolve_field_rule(
    raw: dict, rule_name: str, mapping: AdapterMapping, enum_type: type[StrEnum], warnings: list[str]
) -> str:
    rule = getattr(mapping, rule_name)
    raw_value = resolve_path(raw, rule.path) if rule.path else None
    if raw_value is None:
        return rule.default
    raw_value = str(raw_value).strip().lower()
    if rule.value_map:
        if raw_value in rule.value_map:
            return rule.value_map[raw_value]
        warnings.append(f"unmapped_{rule_name}_raw_value:{raw_value}")
        return rule.default
    if raw_value in {member.value for member in enum_type}:
        return raw_value
    warnings.append(f"unmapped_{rule_name}_raw_value:{raw_value}")
    return rule.default


def build_observation(raw: dict, mapping: AdapterMapping) -> Observation:
    warnings: list[str] = []

    event_id = _require_str(raw, mapping.event_id_path, field_name="event_id")
    project_id = _require_str(raw, mapping.project_id_path, field_name="project_id")
    subject_id = _require_str(raw, mapping.subject_id_path, field_name="subject_id")

    session_id = resolve_path(raw, mapping.session_id_path)
    has_session_id = session_id is not None and str(session_id).strip() != ""
    session_id = str(session_id).strip() if has_session_id else f"synthetic:{event_id}"

    raw_timestamp = _require_str(raw, mapping.timestamp_path, field_name="timestamp")
    timestamp = _parse_timestamp(raw_timestamp, mapping, warnings)

    action = _resolve_action(raw, mapping)

    source = ObservationSource(_resolve_field_rule(raw, "source", mapping, ObservationSource, warnings))
    role = ObservationRole(_resolve_field_rule(raw, "role", mapping, ObservationRole, warnings))
    effect = ObservationEffect(_resolve_field_rule(raw, "effect", mapping, ObservationEffect, warnings))
    trigger = ObservationTrigger(
        _resolve_field_rule(raw, "trigger", mapping, ObservationTrigger, warnings)
    )
    status = ObservationStatus(_resolve_field_rule(raw, "status", mapping, ObservationStatus, warnings))

    screen = resolve_path(raw, mapping.screen_path) if mapping.screen_path else None
    screen = str(screen).strip() if screen is not None else None
    widget = resolve_path(raw, mapping.widget_path) if mapping.widget_path else None
    widget = str(widget).strip() if widget is not None else None

    target = _resolve_target(raw, mapping)

    parameters: dict[str, str] = {}
    for canonical_name, path in mapping.parameter_fields.items():
        value = resolve_path(raw, path)
        if value is not None:
            parameters[canonical_name] = str(value)

    breaks_episode = False
    if mapping.breaks_episode_path is not None:
        breaks_episode = bool(resolve_path(raw, mapping.breaks_episode_path))
    if action in mapping.breaks_episode_action_keys:
        breaks_episode = True

    app_version = resolve_path(raw, mapping.app_version_path) if mapping.app_version_path else None
    app_version = str(app_version) if app_version is not None else None

    quality = ObservationQuality(
        has_screen=screen is not None,
        has_widget=widget is not None,
        has_session_id=has_session_id,
        is_synthetic_session=not has_session_id,
        mapping_warnings=tuple(warnings),
    )

    return Observation(
        event_id=event_id,
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        timestamp=timestamp,
        source=source,
        action=action,
        role=role,
        effect=effect,
        trigger=trigger,
        screen=screen,
        widget=widget,
        target=target,
        parameters=parameters,
        status=status,
        breaks_episode=breaks_episode,
        app_version=app_version,
        mapping_version=mapping.mapping_version,
        quality=quality,
    )
