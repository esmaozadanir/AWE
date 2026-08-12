"""Exact Base Family (bölüm 6.5): tamamen aynı yapısal izi taşıyan `EpisodeCandidate`'ları
aynı family'de toplar.

Eşitlik `Symbol = (action, effect, screen, mapping_version)` dizisinin tam eşitliğidir.
Fuzzy benzerlik, ağırlıklandırma, ambiguity marjı yoktur (bölüm 6.4: "Fuzzy merge yoktur")
— bu, eski tasarımın MATCH/VARIANT_MATCH/AMBIGUOUS/NO_MATCH karar sürecini tamamen ortadan
kaldırır: aynı exact dizi her zaman aynı family'ye gider, bu deterministik olarak dizinin
kendisinden türetilen `family_id` ile sağlanır (aday sırasından veya "önce kim geldi"den
bağımsız — bölüm 9.3'te kabul edilen fragmentation riskinin bilinçli karşılığıdır)."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from awe.domain.episode import EpisodeCandidate
from awe.domain.family import BaseFamily
from awe.domain.tokens import Symbol


def compute_family_id(project_id: str, subject_id: str, symbols: tuple[Symbol, ...]) -> str:
    serialized = "\x1e".join(
        f"{action}\x1f{effect}\x1f{screen or ''}\x1f{mapping_version}"
        for action, effect, screen, mapping_version in symbols
    )
    digest = hashlib.sha1(f"{project_id}\x1d{subject_id}\x1d{serialized}".encode()).hexdigest()[:16]
    return f"fam_{digest}"


def group_into_families(candidates: list[EpisodeCandidate]) -> list[BaseFamily]:
    if not candidates:
        return []

    project_id = candidates[0].project_id
    subject_id = candidates[0].subject_id

    grouped: dict[tuple[Symbol, ...], list[EpisodeCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.symbols].append(candidate)

    families: list[BaseFamily] = []
    for symbols, members in grouped.items():
        families.append(
            BaseFamily(
                family_id=compute_family_id(project_id, subject_id, symbols),
                project_id=project_id,
                subject_id=subject_id,
                symbols=symbols,
                occurrence_ids=[member.candidate_id for member in members],
            )
        )
    return families
