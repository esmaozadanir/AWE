"""Screen Transition Evidence (bölüm 6.8): bir ACTION sonrasında gözlenen opaque screen
anahtarını toplar. Bu katman ekranın semantik anlamını bulmaz; nedensellik kanıtlamaz,
yalnızca korelasyon gösterir (bölüm 9.2).

Pipeline sırasında Anchor Resolver'dan ÖNCE gelir (bölüm 5) — bir `ShortcutAnchor` tüketmez,
tam tersine Anchor Resolver'ın aday pozisyonlar için danıştığı bir kanıt kaynağıdır. Bu yüzden
girdi bir sembol pozisyonudur, çözülmüş bir anchor değil.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import ObservationEffect, ObservationStatus, ScreenEvidenceState
from awe.domain.episode import EpisodeCandidate
from awe.domain.screen_evidence import ScreenTransitionEvidence
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol


@dataclass(frozen=True, slots=True)
class _OccurrenceScreenResult:
    screen: str | None
    ambiguous: bool


def _occurrence_post_view_screen(
    candidate: EpisodeCandidate, series: OSeries, position: int
) -> _OccurrenceScreenResult:
    anchor_step = candidate.steps[position]
    if anchor_step.status != ObservationStatus.SUCCESS:
        return _OccurrenceScreenResult(screen=None, ambiguous=False)

    anchor_obs_index = anchor_step.observation_index
    anchor_timestamp = series.raw_observations[anchor_obs_index].timestamp

    next_action_timestamp = None
    if position + 1 < len(candidate.steps):
        next_index = candidate.steps[position + 1].observation_index
        next_action_timestamp = series.raw_observations[next_index].timestamp

    screens: set[str] = set()
    for obs in series.raw_observations[anchor_obs_index + 1 :]:
        if obs.timestamp <= anchor_timestamp:
            continue
        if next_action_timestamp is not None and obs.timestamp >= next_action_timestamp:
            break
        if obs.effect == ObservationEffect.VIEW and obs.screen:
            screens.add(obs.screen)

    if not screens:
        return _OccurrenceScreenResult(screen=None, ambiguous=False)
    if len(screens) > 1:
        return _OccurrenceScreenResult(screen=None, ambiguous=True)
    return _OccurrenceScreenResult(screen=next(iter(screens)), ambiguous=False)


def build_screen_transition_evidence(
    variant: TargetVariant,
    position: int,
    symbol: Symbol,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: ScreenEvidenceConfig,
) -> ScreenTransitionEvidence:
    session_screens: dict[str, str] = {}
    conflicting_sessions: set[str] = set()

    for occurrence_id in variant.occurrence_ids:
        candidate = candidates_by_id[occurrence_id]
        if position >= len(candidate.steps):
            continue
        series = series_by_id[candidate.series_id]
        result = _occurrence_post_view_screen(candidate, series, position)

        if result.ambiguous:
            conflicting_sessions.add(candidate.session_id)
            continue
        if result.screen is None:
            continue

        existing = session_screens.get(candidate.session_id)
        if existing is not None and existing != result.screen:
            conflicting_sessions.add(candidate.session_id)
        else:
            session_screens[candidate.session_id] = result.screen

    screen_counts = Counter(session_screens.values())

    if conflicting_sessions or len(screen_counts) > 1:
        return ScreenTransitionEvidence(
            symbol=symbol,
            state=ScreenEvidenceState.CONFLICTING,
            screen=None,
            supporting_sessions=sum(screen_counts.values()),
            conflicting_screens=tuple(sorted(screen_counts)),
        )

    if not screen_counts:
        return ScreenTransitionEvidence(
            symbol=symbol, state=ScreenEvidenceState.INSUFFICIENT, screen=None, supporting_sessions=0
        )

    ((screen, supporting_sessions),) = screen_counts.items()
    if supporting_sessions >= config.min_supporting_sessions:
        return ScreenTransitionEvidence(
            symbol=symbol,
            state=ScreenEvidenceState.STABLE,
            screen=screen,
            supporting_sessions=supporting_sessions,
        )
    return ScreenTransitionEvidence(
        symbol=symbol,
        state=ScreenEvidenceState.INSUFFICIENT,
        screen=None,
        supporting_sessions=supporting_sessions,
    )
