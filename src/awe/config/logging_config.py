"""Yapılandırılmış (structured) log kurulumu (bölüm 132).

Motor, her pipeline adımında `awe.engine` logger'ı üzerinden tek satırlık JSON olay kayıtları
üretir (`analysis_started`, `family_matched`, `risk_blocked` vb.). Hiçbir kayıt kullanıcı
parametre değeri (target ref, prefill değeri) içermez — yalnızca sayaçlar, kimlikler ve karar
sonuçları taşınır.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


_ENGINE_LOGGER = logging.getLogger("awe.engine")


def log_event(event: str, **fields: object) -> None:
    _ENGINE_LOGGER.info(event, extra={"awe_event": event, **fields})
