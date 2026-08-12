"""Adapter mapping sözleşmesi: müşteriye özel raw event alanlarının canonical alanlara
deklaratif olarak eşlenmesi (bölüm 6.1, 8).

AWE Core, bu modülü kullanarak hiçbir müşteriye özel Python kodu yazmadan farklı raw
telemetry formatlarını canonical Observation'a çevirir. Yeni bir müşteri entegrasyonu,
yeni kod değil yeni bir `AdapterMapping` konfigürasyonu demektir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def resolve_path(raw: dict[str, Any], path: str) -> Any:
    """Nokta ayraçlı bir path ile iç içe sözlükten değer okur (ör. 'data.screen')."""

    value, _ = resolve_path_with_presence(raw, path)
    return value


def resolve_path_with_presence(raw: dict[str, Any], path: str) -> tuple[Any, bool]:
    """`resolve_path` ile aynı, ama anahtarın hiç var olmadığını (`False`) anahtarın var
    olup değerinin `null` olduğundan (`True`, değer `None`) ayırt eder. Bu ayrım yalnızca
    `target` alanı için gereklidir (bölüm 3 kural 6: `null` ≠ "alan hiç gönderilmedi")."""

    current: Any = raw
    parts = path.split(".")
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    last = parts[-1]
    if not isinstance(current, dict) or last not in current:
        return None, False
    return current[last], True


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
    """Ham action string'ini normalize etmek için opsiyonel eşleme. Eşleşme yoksa ham değer
    aynen `action` olarak kullanılır — engine action'ın kendi business anlamını tahmin etmez."""

    screen_path: str | None = None
    duration_path: str | None = None

    source: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    effect: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    trigger: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))
    status: FieldRule = field(default_factory=lambda: FieldRule(default="unknown"))

    target: TargetRule = field(default_factory=TargetRule)
