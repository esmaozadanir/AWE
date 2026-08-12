"""Raw event dict'ini canonical Observation'a çeviren tek yer (bölüm 6.1).

Zorunlu bir alan üretilemediğinde veya timestamp naive geldiğinde event reddedilir
(`AdapterValidationError`) — bölüm 6.1: "Zorunlu alan eksikse event reject edilir. Naive
timestamp reject edilir." Eksik/geçersiz opsiyonel alanlar reddetmez; canonical `unknown`'a
düşer ve `ObservationQuality` üzerinde bir kanıt/flag bırakır. Adapter alışkanlık, anchor
veya risk kararı vermez — yalnızca canonicalization yapar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from awe.adapter.mapping import AdapterMapping, FieldRule, resolve_path, resolve_path_with_presence
from awe.domain.enums import ObservationEffect, ObservationSource, ObservationStatus, ObservationTrigger
from awe.domain.observation import Observation, ObservationQuality


class AdapterValidationError(ValueError):
    """Zorunlu bir alan üretilemediğinde veya timestamp naive geldiğinde fırlatılır."""


def _require_str(raw: dict[str, Any], path: str, *, field_name: str) -> str:
    value = resolve_path(raw, path)
    if value is None:
        raise AdapterValidationError(f"required field '{field_name}' is missing")
    text = str(value).strip()
    if not text:
        raise AdapterValidationError(f"required field '{field_name}' is empty")
    return text


def _parse_timestamp(raw: dict[str, Any], mapping: AdapterMapping) -> datetime:
    text = _require_str(raw, mapping.timestamp_path, field_name="timestamp")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AdapterValidationError(f"invalid timestamp: {text!r}") from exc
    if parsed.tzinfo is None:
        raise AdapterValidationError(f"naive timestamp not allowed: {text!r}")
    return parsed.astimezone(UTC)


def _resolve_action(raw: dict[str, Any], mapping: AdapterMapping) -> str:
    raw_action = _require_str(raw, mapping.action_key_path, field_name="action")
    return mapping.action_key_value_map.get(raw_action, raw_action)


def _resolve_field_rule(
    raw: dict[str, Any],
    rule_name: str,
    rule: FieldRule,
    enum_type: type[StrEnum],
    warnings: list[str],
) -> str:
    if rule.path is None:
        return rule.default
    raw_value = resolve_path(raw, rule.path)
    if raw_value is None:
        return rule.default
    text = str(raw_value).strip().lower()
    if rule.value_map:
        if text in rule.value_map:
            return rule.value_map[text]
        warnings.append(f"unmapped_{rule_name}_raw_value:{text}")
        return rule.default
    valid_values = {member.value for member in enum_type}
    if text in valid_values:
        return text
    warnings.append(f"unmapped_{rule_name}_raw_value:{text}")
    return rule.default


def _resolve_screen(raw: dict[str, Any], mapping: AdapterMapping) -> str | None:
    if mapping.screen_path is None:
        return None
    value = resolve_path(raw, mapping.screen_path)
    return str(value) if value is not None else None


def _resolve_target(raw: dict[str, Any], mapping: AdapterMapping) -> tuple[str | None, bool]:
    """`(target, missing_target_field)` döner. `ref_path` konfigüre edilmemişse bu bir veri
    kalitesi sorunu değildir (mapping bilinçli olarak target izlemiyor): `(None, False)`.
    `ref_path` konfigüre edilmiş ama raw payload'da anahtar hiç yoksa: `(None, True)` — "hedef
    verisi bilinmiyor" (bölüm 3 kural 6). Anahtar var ve değeri `null`: `(None, False)` —
    "açıkça hedef yok". Anahtar var ve değeri doluysa: `(str(value), False)`."""

    if mapping.target.ref_path is None:
        return None, False
    value, present = resolve_path_with_presence(raw, mapping.target.ref_path)
    if not present:
        return None, True
    if value is None:
        return None, False
    return str(value), False


def _resolve_duration_ms(raw: dict[str, Any], mapping: AdapterMapping) -> tuple[int | None, bool]:
    """`(duration_ms, invalid)` döner. Negatif veya sayısal olmayan değerler `None` yapılır
    ve `invalid=True` işaretlenir (bölüm 6.1). `duration_ms` yalnızca audit amaçlıdır."""

    if mapping.duration_path is None:
        return None, False
    value = resolve_path(raw, mapping.duration_path)
    if value is None:
        return None, False
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return None, True
    if duration < 0:
        return None, True
    return duration, False


def build_observation(raw: dict[str, Any], mapping: AdapterMapping) -> Observation:
    event_id = _require_str(raw, mapping.event_id_path, field_name="event_id")
    project_id = _require_str(raw, mapping.project_id_path, field_name="project_id")
    subject_id = _require_str(raw, mapping.subject_id_path, field_name="subject_id")
    session_id = _require_str(raw, mapping.session_id_path, field_name="session_id")
    timestamp = _parse_timestamp(raw, mapping)
    action = _resolve_action(raw, mapping)

    warnings: list[str] = []
    source = ObservationSource(_resolve_field_rule(raw, "source", mapping.source, ObservationSource, warnings))
    trigger = ObservationTrigger(
        _resolve_field_rule(raw, "trigger", mapping.trigger, ObservationTrigger, warnings)
    )
    effect = ObservationEffect(_resolve_field_rule(raw, "effect", mapping.effect, ObservationEffect, warnings))
    status = ObservationStatus(_resolve_field_rule(raw, "status", mapping.status, ObservationStatus, warnings))

    screen = _resolve_screen(raw, mapping)
    target, missing_target_field = _resolve_target(raw, mapping)
    duration_ms, invalid_duration = _resolve_duration_ms(raw, mapping)

    quality = ObservationQuality(
        has_screen=screen is not None,
        missing_target_field=missing_target_field,
        invalid_duration=invalid_duration,
        warnings=tuple(warnings),
    )

    return Observation(
        event_id=event_id,
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        timestamp=timestamp,
        action=action,
        source=source,
        trigger=trigger,
        effect=effect,
        status=status,
        screen=screen,
        target=target,
        duration_ms=duration_ms,
        mapping_version=mapping.mapping_version,
        quality=quality,
    )
