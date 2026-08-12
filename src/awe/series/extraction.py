"""O-Series Builder: bir session'ın sıralı Observation akışını structural chunk'lara böler
(bölüm 6.3). Henüz Family/Habit/Risk/Benefit hesaplamaz.

Eski tasarımdan farklı olarak sınır `breaksEpisode` bayrağı ya da "completion effect" tahmini
değildir (bu alanlar artık yok). Yalnızca iki yapısal kural chunk sınırı çizer:
1. Aynı timestamp'te 2+ ACTION-classified event varsa sıra üretilmez — bu grup hiçbir chunk'ın
   step dizisine girmez (yalnızca trailing raw kanıt olarak korunur), mevcut chunk kesilir.
2. `navigation`/`notification`/`deeplink` tetikleyicili bir ACTION, mevcut chunk zaten en az
   bir step içeriyorsa (yani "akışın ortasında" geliyorsa) yeni bir chunk başlatır; kendisi
   yeni chunk'ın giriş adımı olur.

Retry/detour sıkıştırması kasıtlı olarak yoktur (bölüm 6.4: "Fuzzy merge yoktur") — tekrarlanan
adımlar veya geri-navigasyonlar olduğu gibi kalır; bu, exact family fragmentation riskini
(bölüm 9.3) motor tarafında telafi etmeden kabul eden bilinçli bir tasarım kararıdır.
"""

from __future__ import annotations

from awe.adapter.classification import classify_event
from awe.domain.enums import EventClassification, ObservationTrigger, OrderingConfidence
from awe.domain.observation import Observation
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken

_CHUNK_STARTING_TRIGGERS = frozenset(
    {ObservationTrigger.NAVIGATION, ObservationTrigger.NOTIFICATION, ObservationTrigger.DEEPLINK}
)

_ChunkEntry = tuple[Observation, bool]
"""(observation, excluded_from_steps). `excluded_from_steps=True`, bu event'in bir ambiguity
grubunun parçası olduğu ve hiçbir chunk'ın step dizisine giremeyeceği anlamına gelir."""


def extract_series(
    ordered_observations: list[Observation], ordering_confidence: OrderingConfidence
) -> list[OSeries]:
    if not ordered_observations:
        return []

    project_id = ordered_observations[0].project_id
    subject_id = ordered_observations[0].subject_id
    session_id = ordered_observations[0].session_id

    timestamp_groups: list[list[Observation]] = []
    for obs in ordered_observations:
        if timestamp_groups and timestamp_groups[-1][0].timestamp == obs.timestamp:
            timestamp_groups[-1].append(obs)
        else:
            timestamp_groups.append([obs])

    chunks: list[list[_ChunkEntry]] = [[]]
    cut_by_ambiguity: list[bool] = [False]
    chunk_has_step = False

    for group in timestamp_groups:
        action_members = [o for o in group if classify_event(o) == EventClassification.ACTION]

        if len(action_members) >= 2:
            chunks[-1].extend((o, True) for o in group)
            cut_by_ambiguity[-1] = True
            chunks.append([])
            cut_by_ambiguity.append(False)
            chunk_has_step = False
            continue

        action_obs = action_members[0] if action_members else None
        if action_obs is not None and chunk_has_step and action_obs.trigger in _CHUNK_STARTING_TRIGGERS:
            chunks.append([])
            cut_by_ambiguity.append(False)
            chunk_has_step = False

        chunks[-1].extend((o, False) for o in group)
        if action_obs is not None:
            chunk_has_step = True

    series_list: list[OSeries] = []
    for entries, was_cut in zip(chunks, cut_by_ambiguity, strict=True):
        if not entries:
            continue
        series_list.append(_build_chunk(entries, project_id, subject_id, session_id, ordering_confidence, was_cut))
    return series_list


def _build_chunk(
    entries: list[_ChunkEntry],
    project_id: str,
    subject_id: str,
    session_id: str,
    ordering_confidence: OrderingConfidence,
    cut_by_ambiguity: bool,
) -> OSeries:
    observations = [obs for obs, _excluded in entries]

    steps: list[BehaviorStep] = []
    for index, (obs, excluded) in enumerate(entries):
        if excluded or classify_event(obs) != EventClassification.ACTION:
            continue
        token = BehaviorToken(
            action=obs.action, effect=obs.effect, screen=obs.screen, mapping_version=obs.mapping_version
        )
        steps.append(
            BehaviorStep(
                token=token,
                target=obs.target,
                target_unknown=obs.quality.missing_target_field,
                status=obs.status,
                observation_index=index,
            )
        )

    first, last = observations[0], observations[-1]
    entry_obs = next(
        (obs for obs, excluded in entries if not excluded and classify_event(obs) == EventClassification.ACTION),
        first,
    )

    return OSeries(
        series_id=f"{session_id}#{first.event_id}",
        project_id=project_id,
        subject_id=subject_id,
        session_id=session_id,
        started_at=first.timestamp,
        ended_at=last.timestamp,
        ordering_confidence=ordering_confidence,
        raw_observations=tuple(observations),
        steps=tuple(steps),
        entry_trigger=entry_obs.trigger,
        entry_screen=entry_obs.screen,
        has_shortcut_trigger=any(obs.trigger == ObservationTrigger.SHORTCUT for obs in observations),
        final_status=last.status,
        cut_by_ambiguity=cut_by_ambiguity,
    )
