"""Anchor Resolver (bölüm 6.9): tekrarlanan davranışın gözlenen amaç/son işlem noktasını bulur.
Shortcut değildir; yalnızca `HABIT_DETECTED` variant üzerinde çalışır.

Strength yorumu (belgenin üç kanıt kaynağından türetilmiştir, belge STRONG/MEDIUM ayrımını
formülle vermez): pozisyon exact target taşıyorsa `STRONG`; yalnızca outcome-evidence effect
taşıyorsa `MEDIUM`; yalnızca stable post-view kanıtından çözülmüşse `WEAK`.
"""

from __future__ import annotations

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import (
    OUTCOME_EVIDENCE_EFFECTS,
    AnchorStatus,
    AnchorStrength,
    ObservationEffect,
    ObservationStatus,
    ReasonCode,
    ScreenEvidenceState,
    TargetVariantKind,
)
from awe.domain.episode import EpisodeCandidate
from awe.domain.plan import ShortcutAnchor
from awe.domain.series import OSeries
from awe.domain.target import TargetVariant
from awe.domain.tokens import Symbol
from awe.screen_evidence import build_screen_transition_evidence

ROUTE_OPEN_EFFECTS = frozenset(effect.value for effect in (ObservationEffect.ROUTE, ObservationEffect.OPEN))


def _occurrence_status_at(
    position: int, variant: TargetVariant, candidates_by_id: dict[str, EpisodeCandidate]
) -> AnchorStatus:
    any_success = any(
        candidates_by_id[occurrence_id].steps[position].status == ObservationStatus.SUCCESS
        for occurrence_id in variant.occurrence_ids
        if position < len(candidates_by_id[occurrence_id].steps)
    )
    return AnchorStatus.RESOLVED if any_success else AnchorStatus.ATTEMPT_ONLY


def resolve_anchor(
    family_symbols: tuple[Symbol, ...],
    variant: TargetVariant,
    candidates_by_id: dict[str, EpisodeCandidate],
    series_by_id: dict[str, OSeries],
    screen_evidence_config: ScreenEvidenceConfig,
) -> ShortcutAnchor:
    last_position = max(len(family_symbols) - 1, 0)
    fallback_symbol = family_symbols[-1] if family_symbols else ("", "", None, "")

    if variant.kind == TargetVariantKind.UNKNOWN_TARGET:
        return ShortcutAnchor(
            symbol=fallback_symbol,
            position=last_position,
            strength=AnchorStrength.WEAK,
            status=AnchorStatus.UNRESOLVED,
            reason_codes=(ReasonCode.UNKNOWN_TARGET_BLOCKS_ANCHOR,),
        )

    target_positions = {i for i in range(len(family_symbols)) if variant.fingerprint[i] is not None}
    outcome_positions = {i for i, symbol in enumerate(family_symbols) if symbol[1] in OUTCOME_EVIDENCE_EFFECTS}
    strong_positions = target_positions | outcome_positions

    if strong_positions:
        position = max(strong_positions)
        strength = AnchorStrength.STRONG if position in target_positions else AnchorStrength.MEDIUM
        trailing = family_symbols[position + 1 :]
        trailing_is_route_open_only = bool(trailing) and all(
            symbol[1] in ROUTE_OPEN_EFFECTS for symbol in trailing
        )
        if trailing_is_route_open_only:
            return ShortcutAnchor(
                symbol=family_symbols[position],
                position=position,
                strength=strength,
                status=AnchorStatus.AMBIGUOUS,
                reason_codes=(ReasonCode.AMBIGUOUS_ANCHOR,),
            )
        status = _occurrence_status_at(position, variant, candidates_by_id)
        reasons = () if status == AnchorStatus.RESOLVED else (ReasonCode.ATTEMPT_ONLY,)
        return ShortcutAnchor(
            symbol=family_symbols[position],
            position=position,
            strength=strength,
            status=status,
            reason_codes=reasons,
        )

    all_route_open_only = bool(family_symbols) and all(
        symbol[1] in ROUTE_OPEN_EFFECTS for symbol in family_symbols
    )
    if all_route_open_only:
        evidence = build_screen_transition_evidence(
            variant,
            last_position,
            family_symbols[last_position],
            candidates_by_id,
            series_by_id,
            screen_evidence_config,
        )
        if evidence.state == ScreenEvidenceState.STABLE:
            status = _occurrence_status_at(last_position, variant, candidates_by_id)
            reasons = () if status == AnchorStatus.RESOLVED else (ReasonCode.ATTEMPT_ONLY,)
            return ShortcutAnchor(
                symbol=family_symbols[last_position],
                position=last_position,
                strength=AnchorStrength.WEAK,
                status=status,
                reason_codes=reasons,
            )

    return ShortcutAnchor(
        symbol=fallback_symbol,
        position=last_position,
        strength=AnchorStrength.WEAK,
        status=AnchorStatus.AMBIGUOUS,
        reason_codes=(ReasonCode.AMBIGUOUS_ANCHOR,),
    )
