"""Screen Transition Evidence (bölüm 6.8), özellikle bir adayın (candidate) kaynak session'ın
tam kendisi olmadığı -- yalnızca bir ön eki/alt dizisi olduğu -- durumlar için."""

from __future__ import annotations

from datetime import UTC, datetime

from awe.config.engine_config import ScreenEvidenceConfig
from awe.domain.enums import EpisodeCandidateKind, ScreenEvidenceState
from awe.domain.episode import EpisodeCandidate
from awe.families import group_into_families
from awe.screen_evidence import build_screen_transition_evidence
from awe.targeting import resolve_targets
from tests.support.builders import StepSpec, make_series_from_steps

_NOW = datetime(2026, 1, 1, 9, tzinfo=UTC)
_CONFIG = ScreenEvidenceConfig(min_supporting_sessions=2)


def _prefix_candidate(series, length: int) -> EpisodeCandidate:
    """`series`in yalnızca İLK `length` adımını kapsayan bir aday kurar -- Episode Candidate
    Builder'ın ürettiği bir sıra-korumalı ortak alt dizinin (ör. bir ön ek eşleşmesi) sonucunu
    taklit eder: adayın son adımı, KAYNAK session'ın son adımı DEĞİLDİR."""

    steps = series.steps[:length]
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:prefix:{length}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=EpisodeCandidateKind.COMMON_SUBSEQUENCE,
        steps=steps,
        step_indices=tuple(range(length)),
        observed_at=series.started_at,
        entry_trigger=series.entry_trigger,
        has_shortcut_trigger=series.has_shortcut_trigger,
        final_status=steps[-1].status,
    )


def test_post_view_window_does_not_leak_past_the_candidates_own_last_step():
    """Regresyon: adayın son adımı (B), kaynak session'da devam eden bir sonraki ACTION'dan
    (C) önce durmalı. Eskiden pencere adayın kendi (kısaltılmış) adım listesine göre
    sınırlanıyordu; B'den sonra C'ye kadar süren gerçek pencereyi görmek yerine session
    sonuna kadar sınırsız tarıyor, C'den SONRAKİ ekranı da (Y) B'ye ait sanıyordu -- bu da
    iki farklı ekran görüp CONFLICTING üretmesine yol açıyordu."""

    steps = [
        StepSpec(action="step_a", screen="screen_a"),
        StepSpec(action="step_b", screen="screen_b"),
        StepSpec(action="step_c", screen="screen_c"),
    ]
    # session1: step_b sonrası yalnızca "x" görünür (step_c'den önce).
    series1 = make_series_from_steps("sess1", _NOW, steps, series_suffix="1", views_after={1: ["x"], 2: ["y"]})
    # session2: aynı şekilde -- iki session da B sonrası "x" görür, sonra C'ye geçip "y" görür.
    series2 = make_series_from_steps("sess2", _NOW, steps, series_suffix="2", views_after={1: ["x"], 2: ["y"]})

    candidate1 = _prefix_candidate(series1, length=2)  # yalnızca step_a, step_b
    candidate2 = _prefix_candidate(series2, length=2)
    candidates_by_id = {candidate1.candidate_id: candidate1, candidate2.candidate_id: candidate2}
    series_by_id = {series1.series_id: series1, series2.series_id: series2}

    families = group_into_families([candidate1, candidate2])
    assert len(families) == 1
    family = families[0]
    variants = resolve_targets(family, candidates_by_id)
    assert len(variants) == 1
    variant = variants[0]

    # position=1 -> "step_b", adayın SON adımı ama kaynak session'ın son adımı değil.
    evidence = build_screen_transition_evidence(
        variant, 1, family.symbols[1], candidates_by_id, series_by_id, _CONFIG
    )

    assert evidence.state == ScreenEvidenceState.STABLE
    assert evidence.screen == "x"
