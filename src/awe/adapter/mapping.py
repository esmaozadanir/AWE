"""Adapter mapping sözleşmesi: müşteriye özel raw event alanlarının canonical alanlara
deklaratif olarak eşlenmesi (bölüm 31-32).

AWE Core, bu modülü kullanarak hiçbir müşteriye özel Python kodu yazmadan farklı raw
telemetry formatlarını canonical Observation'a çevirir. Yeni bir müşteri entegrasyonu,
yeni kod değil yeni bir `AdapterMapping` konfigürasyonu demektir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def resolve_path(raw: dict[str, Any], path: str) -> Any:
    """Nokta ayraçlı bir path ile iç içe sözlükten değer okur (ör. 'data.screen')."""

    current: Any = raw
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


@dataclass(frozen=True, slots=True)
class FieldRule:
    """Bir canonical alanın raw veriden nasıl türetileceğini tanımlar.

    `path` verilmemişse alan her zaman `default` değerini alır. `value_map` verilmişse
    okunan ham değer önce oradan geçirilir; eşleşme yoksa `default`'a düşer — engine hiçbir
    zaman bilinmeyen bir ham değeri kendi kendine yorumlamaz.
    """

    path: str | None = None
    value_map: dict[str, str] = field(default_factory=dict)
    default: str = "unknown"

    def resolve(self, raw: dict[str, Any]) -> str:
        if self.path is None:
            return self.default
        raw_value = resolve_path(raw, self.path)
        if raw_value is None:
            return self.default
        raw_value = str(raw_value)
        if self.value_map:
            return self.value_map.get(raw_value, self.default)
        return raw_value


@dataclass(frozen=True, slots=True)
class TargetRule:
    ref_path: str | None = None


@dataclass(frozen=True, slots=True)
class AdapterMapping:
    mapping_version: str

    event_id_path: str
    project_id_path: str
    subject_id_path: str
    session_id_path: str
    timestamp_path: str
    action_key_path: str
    action_key_value_map: dict[str, str] = field(default_factory=dict)
    """Ham action string'ini normalize etmek için opsiyonel eşleme (bölüm 31: action normalization).
    Eşleşme yoksa ham değer aynen action_key olarak kullanılır — engine action_key'in kendi
    business anlamını tahmin etmez (bölüm 17)."""

    screen_path: str | None = None
    widget_path: str | None = None
    app_version_path: str | None = None
    duration_ms_path: str | None = None

    source: FieldRule = field(default_factory=lambda: FieldRule(default="client"))
    role: FieldRule = field(default_factory=lambda: FieldRule(default="action"))
    effect: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    trigger: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    status: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))

    target: TargetRule = field(default_factory=TargetRule)

    parameter_fields: dict[str, str] = field(default_factory=dict)
    """canonical parametre adı -> raw path. Metadata'dan yalnızca burada açıkça
    whitelist'lenen alanlar okunur (bölüm 29)."""

    breaks_episode_path: str | None = None
    breaks_episode_action_keys: frozenset[str] = frozenset()

    assume_timezone: str = "UTC"
    """Ham timestamp naive geldiğinde varsayılan olarak atanacak timezone."""
