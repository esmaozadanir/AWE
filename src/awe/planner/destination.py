"""Destination Resolver (bölüm 6.11): tek görevi açılacak opaque `screen` anahtarını seçmektir.

`screen`, karşılaştırma sembolünün bir parçası olduğu için (bölüm 6.5) aynı family'nin tüm
üye occurrence'ları anchor pozisyonunda zaten aynı `screen` değerini paylaşır — action-surface
durumunda ayrı bir "representative screen" hesaplamaya gerek yoktur, sembolden doğrudan okunur.
"""

from __future__ import annotations

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import AnchorStatus, ObservationEffect, ReasonCode, ScreenEvidenceState
from awe.domain.episode import EpisodeCandidate
from awe.domain.plan import Destination, ShortcutAnchor
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.planner.anchors import ROUTE_OPEN_EFFECTS
from awe.screen_evidence import build_screen_transition_evidence

_ACTION_SURFACE_EFFECTS = frozenset(
    effect.value
    for effect in (
        ObservationEffect.SUBMIT,
        ObservationEffect.CREATE,
        ObservationEffect.DELETE,
        ObservationEffect.CONFIRM,
        ObservationEffect.UPDATE,
        ObservationEffect.TOGGLE,
        ObservationEffect.REQUEST,
        ObservationEffect.DOWNLOAD,
        ObservationEffect.INPUT,
        ObservationEffect.SELECT,
        ObservationEffect.FILTER,
        ObservationEffect.SORT,
        ObservationEffect.FOCUS,
    )
)

_UNRESOLVED = Destination(screen=None, resolved=False, reason_codes=(ReasonCode.DESTINATION_UNRESOLVED,))


def resolve_destination(
    anchor: ShortcutAnchor,
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    config: ScreenEvidenceConfig,
) -> Destination:
    if anchor.status not in (AnchorStatus.RESOLVED, AnchorStatus.ATTEMPT_ONLY):
        return _UNRESOLVED

    _action, effect, screen, _mapping_version = anchor.symbol

    if effect in ROUTE_OPEN_EFFECTS:
        evidence = build_screen_transition_evidence(
            variant, anchor.position, anchor.symbol, candidates_by_id, series_by_id, config
        )
        if evidence.state == ScreenEvidenceState.STABLE and evidence.screen:
            return Destination(screen=evidence.screen, resolved=True)
        return _UNRESOLVED

    if effect in _ACTION_SURFACE_EFFECTS:
        if screen:
            return Destination(screen=screen, resolved=True)
        return _UNRESOLVED

    return _UNRESOLVED
