"""AWE Core hiçbir uygulamaya özel iş kavramı içermez (bölüm 1, 3). Bu test motor
paketlerini tarayarak, sekiz örnek entegrasyonun (`config_examples/`) veya yaygın iş
alanlarının isimlerinin sızmadığını doğrular.
"""

from __future__ import annotations

import re
from pathlib import Path

_CORE_PACKAGES = [
    "adapter",
    "ordering",
    "series",
    "episodes",
    "families",
    "targeting",
    "habit",
    "screen_evidence",
    "planner",
    "risk",
    "benefit",
    "selection",
    "lifecycle",
    "domain",
    "persistence",
    "services",
]
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "awe"

_FORBIDDEN_WORDS = [
    # config_examples/ altındaki örnek entegrasyon proje adları
    "shopwave",
    "learnloop",
    "taskflow",
    "financepilot",
    "healthtrack",
    "socialpulse",
    "streamboxx",
    "wanderly",
    # yaygın iş alanı kelimeleri — motorun hiçbir yerinde geçmemesi beklenir
    "invoice",
    "shipment",
    "patient",
    "playlist",
    "flight_number",
]


def test_core_engine_packages_contain_no_application_specific_vocabulary():
    violations = []
    for package in _CORE_PACKAGES:
        package_dir = _SRC_ROOT / package
        for path in package_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for word in _FORBIDDEN_WORDS:
                if re.search(rf"\b{re.escape(word)}\b", text):
                    violations.append(f"{path.relative_to(_SRC_ROOT)}: '{word}'")
    assert not violations, f"application-specific vocabulary leaked into core engine: {violations}"
