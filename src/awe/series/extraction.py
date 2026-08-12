"""O-Series Extraction: session event stream → behavior attempt (occurrence) dizisi (bölüm 35).

Bu katman Habit hesaplamaz, Family clustering yapmaz, Risk/Benefit değerlendirmez — yalnızca
bir session'ın ham Observation akışını anlamlı occurrence sınırlarına böler.

Sınır kuralları:

* `breaksEpisode=true` — kesin, hard boundary (bölüm 39).
* Başarılı tamamlanma — `role=outcome` ya da `effect in {submit, confirm}` olan bir adımın
  `status=success` olması, doğal bir occurrence sonu sayılır. Bu, canonical `role`/`effect`/
  `status` sözlüğüne dayanan yapısal bir kuraldır; herhangi bir business action string'ine
  bakmaz.

Bu iki sınırın dışında kalan tek-session içi çoklu bağımsız davranış (tamamlanma sinyali
üretmeden konu değiştirme) MVP kapsamında ayrıştırılmaz; bu bilinçli bir sınırlamadır ve
`docs/architecture.md` içinde gerekçelendirilmiştir.

Bir occurrence bloğu belirlendikten sonra, o blok içinde karşılaştırma sembollerine hangi
adımların gireceği `classify_event` (ACTION/CONTEXT/IGNORE) ile belirlenir: yalnızca
ACTION'a sınıflanan adımlar normalize edilmiş projeksiyona girer; CONTEXT/IGNORE adımları
`raw_observations`'ta (audit amaçlı) kalmaya devam eder ama sembol dizisine hiç girmez.
"""

from __future__ import annotations

from awe.adapter.classification import classify_event
from awe.config.engine_config import FamilyConfig
from awe.domain.enums import (
    EventClassification,
    ObservationEffect,
    ObservationRole,
    ObservationStatus,
    ObservationTrigger,
    OrderingConfidence,
)
from awe.domain.observation import Observation
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, BehaviorToken
from awe.series.normalization import normalize_steps

_COMPLETION_EFFECTS = (ObservationEffect.SUBMIT, ObservationEffect.CONFIRM)


def _split_on_breaks_episode(observations: list[Observation]) -> list[list[Observation]]:
    blocks: list[list[Observation]] = []
    current: list[Observation] = []
    for obs in observations:
        current.append(obs)
        if obs.breaks_episode:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _is_completion(obs: Observation) -> bool:
    if obs.status != ObservationStatus.SUCCESS:
        return False
    return obs.role == ObservationRole.OUTCOME or obs.effect in _COMPLETION_EFFECTS


def _split_on_completion(observations: list[Observation]) -> list[list[Observation]]:
    blocks: list[list[Observation]] = []
    current: list[Observation] = []
    for obs in observations:
        current.append(obs)
        if _is_completion(obs):
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _to_behavior_step(obs: Observation, index: int) -> BehaviorStep:
    return BehaviorStep(
        token=BehaviorToken(action=obs.action, effect=obs.effect),
        screen=obs.screen,
        widget=obs.widget,
        status=obs.status,
        observation_index=index,
    )


def _build_series(
    block: list[Observation], ordering_confidence: OrderingConfidence, config: FamilyConfig
) -> OSeries:
    raw_steps = [
        _to_behavior_step(obs, idx)
        for idx, obs in enumerate(block)
        if classify_event(obs) == EventClassification.ACTION
    ]
    normalization = normalize_steps(raw_steps, config.detour_max_length)

    first, last = block[0], block[-1]
    series_id = f"{first.session_id}#{first.event_id}"

    return OSeries(
        series_id=series_id,
        project_id=first.project_id,
        subject_id=first.subject_id,
        session_id=first.session_id,
        started_at=first.timestamp,
        ended_at=last.timestamp,
        ordering_confidence=ordering_confidence,
        raw_observations=tuple(block),
        normalized_steps=tuple(normalization.steps),
        retries=tuple(normalization.retries),
        detour_observation_count=normalization.detour_step_count,
        ended_by_breaks_episode=last.breaks_episode,
        entry_trigger=first.trigger,
        entry_screen=first.screen,
        has_shortcut_trigger=any(o.trigger == ObservationTrigger.SHORTCUT for o in block),
        final_status=last.status,
    )


def extract_series(
    ordered_session_observations: list[Observation],
    ordering_confidence: OrderingConfidence,
    config: FamilyConfig,
) -> list[OSeries]:
    if not ordered_session_observations:
        return []

    series: list[OSeries] = []
    for episode_block in _split_on_breaks_episode(ordered_session_observations):
        for completion_block in _split_on_completion(episode_block):
            series.append(_build_series(completion_block, ordering_confidence, config))
    return series
