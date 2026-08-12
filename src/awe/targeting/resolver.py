"""Target Resolver (bölüm 6.6): Base Family occurrence'larını target fingerprint ile böler.

Occurrence fingerprint'i `(step_1.target, ..., step_n.target)`. Her exact fingerprint ayrı
bir `TargetVariant` olarak Habit'e gider — böylece `course_42` üç kez tekrar ederken
`course_17` bir kez görülmüşse kanıtlar havuzlanmaz.

`kind` yorumu (belgenin dört durumu net bir eksen üzerinde tanımlamadığı yer): burada bir
fingerprint'in kendi İÇİNDEKİ distinct non-null değer sayısına bakılır — bir occurrence'ın
kendi adımları birden fazla farklı hedefe değiniyorsa (ör. "workspace_1" ve "report_9" aynı
occurrence içinde) bu `VARIABLE_TARGET`'tır ve Shortcut Intent Builder'ın compound-identity
reddi (bölüm 6.12) ile doğrudan örtüşür. İki AYRI occurrence farklı ama kendi içinde tutarlı
hedeflere sahipse (course_42 vs course_17), bunlar zaten farklı fingerprint'ler oldukları için
ayrı ayrı `FIXED_TARGET` variant'lara ayrılır — havuzlanma zaten bu ayrıştırmayla önlenir."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from awe.domain.enums import TargetVariantKind
from awe.domain.episode import EpisodeCandidate
from awe.domain.family import BaseFamily
from awe.domain.target import TargetFingerprint, TargetVariant


def _fingerprint_digest(fingerprint: TargetFingerprint) -> str:
    serialized = "\x1f".join(value if value is not None else "\x00" for value in fingerprint)
    return hashlib.sha1(serialized.encode()).hexdigest()[:12]


def _kind_of(fingerprint: TargetFingerprint, has_unknown: bool) -> TargetVariantKind:
    if has_unknown:
        return TargetVariantKind.UNKNOWN_TARGET
    distinct_non_null = {value for value in fingerprint if value is not None}
    if not distinct_non_null:
        return TargetVariantKind.NO_EXPLICIT_TARGET
    if len(distinct_non_null) == 1:
        return TargetVariantKind.FIXED_TARGET
    return TargetVariantKind.VARIABLE_TARGET


def resolve_targets(family: BaseFamily, candidates_by_id: dict[str, EpisodeCandidate]) -> list[TargetVariant]:
    groups: dict[TargetFingerprint, list[EpisodeCandidate]] = defaultdict(list)
    for occurrence_id in family.occurrence_ids:
        candidate = candidates_by_id[occurrence_id]
        groups[candidate.targets].append(candidate)

    variants: list[TargetVariant] = []
    for fingerprint, members in groups.items():
        has_unknown = any(step.target_unknown for member in members for step in member.steps)
        variants.append(
            TargetVariant(
                variant_id=f"{family.family_id}:{_fingerprint_digest(fingerprint)}",
                family_id=family.family_id,
                kind=_kind_of(fingerprint, has_unknown),
                fingerprint=fingerprint,
                occurrence_ids=[member.candidate_id for member in members],
            )
        )
    return variants
