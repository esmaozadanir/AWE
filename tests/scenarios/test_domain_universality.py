"""AWE Core'un domain-independence kısıtını otomatik olarak denetler (bölüm 1).

Yasak olan şey, açık iş sözlüğünün (`action`, `screen`, `widget` gibi tamamen
müşteriye özel, kontrolsüz alanların) motor kodunda sabit bir string'e karşı doğrudan
karşılaştırılmasıdır — ör. `if screen == "orders":` ya da `if action ==
"lesson_complete":`. Bu, motorun belirli bir uygulamaya özel davranmaya başladığının kesin
göstergesidir. Canonical, AWE'nin kendi sahip olduğu sözlükle (ör. `effect ==
ObservationEffect.CONFIRM`) karşılaştırma serbesttir; yasak olan yalnızca açık uçlu,
müşteriye özel alanların ham string sabitleriyle karşılaştırılmasıdır.

Denetim, testler ve sentetik veri üreticisi dışındaki tüm motor paketlerini kapsar; test
fixture'ları ve `awe.testing` sentetik üretici, gerçekçilik için iş benzeri isimler
kullanabilir (bölüm "SENTETİK VERİLER GERÇEKÇİ OLMALI") — motor kodunun kendisi bu isimlere
hiçbir zaman dayanmaz.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ENGINE_PACKAGES = (
    "domain",
    "adapter",
    "ordering",
    "series",
    "families",
    "habit",
    "planner",
    "risk",
    "benefit",
    "selection",
    "lifecycle",
    "services",
)

_OPEN_VOCABULARY_FIELDS = frozenset({"action", "screen", "widget"})


def _engine_source_files() -> list[Path]:
    root = Path(__file__).resolve().parents[2] / "src" / "awe"
    files = []
    for package in _ENGINE_PACKAGES:
        files.extend((root / package).rglob("*.py"))
    return sorted(files)


def _field_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _find_open_vocabulary_string_comparisons(tree: ast.Module) -> list[tuple[int, str, str]]:
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for left, right in zip(operands, operands[1:], strict=False):
            for field_side, literal_side in ((left, right), (right, left)):
                field_name = _field_name(field_side)
                if field_name in _OPEN_VOCABULARY_FIELDS and isinstance(literal_side, ast.Constant):
                    if isinstance(literal_side.value, str):
                        violations.append((node.lineno, field_name, literal_side.value))
    return violations


_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "path", _engine_source_files(), ids=lambda p: str(p.relative_to(_REPO_ROOT))
)
def test_engine_code_never_compares_open_vocabulary_fields_to_string_literals(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = _find_open_vocabulary_string_comparisons(tree)
    assert not violations, (
        f"{path}: motor kodu müşteriye özel bir alanı ({violations}) sabit bir string'e karşı "
        "doğrudan karşılaştırıyor — bu domain-independence kısıtını ihlal eder (bölüm 1)."
    )
