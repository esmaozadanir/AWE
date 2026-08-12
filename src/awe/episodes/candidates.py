"""Episode Candidate Builder (bölüm 6.4): Exact Base Family eşleştirmesine giren aday davranış
birimlerini üretir. Henüz habit kararı vermez.

İki aday tipi çıkarılır:
1. Her `OSeries` (structural chunk) chunk'ın tamamı (`FULL_CHUNK`).
2. Farklı chunk'lar arasında bulunan exact, contiguous, pairwise-maximal ortak alt diziler
   (`COMMON_RUN`) — klasik "iki dizi arasındaki tüm maksimal ortak alt dizeler" problemidir.

Step eşitliği `Symbol = (action, effect, screen, mapping_version)` tam eşitliğidir; fuzzy
merge veya optional-step toleransı yoktur (bölüm 6.4). Maksimum aday uzunluğu belgede
kesinleştirilmemiş bir karardır ("Eski MVP'deki max=8 korunacaksa bu ayrıca sabitlenip test
edilmelidir") — burada `EpisodeConfig.max_symbols` (varsayılan 8) olarak sabitlenmiş ve
konfigüre edilebilir bırakılmıştır.
"""

from __future__ import annotations

from awe.config.engine_config import EpisodeConfig
from awe.domain.enums import EpisodeCandidateKind, ObservationTrigger
from awe.domain.episode import EpisodeCandidate
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol


def _all_maximal_common_runs(left: tuple[Symbol, ...], right: tuple[Symbol, ...]) -> list[tuple[int, int, int]]:
    """İki sembol dizisi arasındaki tüm yerel-maksimal exact contiguous ortak alt dizileri
    bulur. Döndürülen her `(left_start, right_start, length)`, ne solda ne sağda daha ileri
    genişletilemeyen bir ortak koşudur — tekli "en uzun ortak alt dize" değil, olabilecek
    tüm maksimal koşuların kümesidir (bölüm 6.4: "pairwise-maximal ortak koşular", çoğul)."""

    n, m = len(left), len(right)
    if n == 0 or m == 0:
        return []

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    runs: list[tuple[int, int, int]] = []
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if left[i - 1] != right[j - 1]:
                continue
            dp[i][j] = dp[i - 1][j - 1] + 1
            is_maximal_end = i == n or j == m or left[i] != right[j]
            if is_maximal_end:
                length = dp[i][j]
                runs.append((i - length, j - length, length))
    return runs


def _candidate_from_slice(
    series: OSeries, start: int, length: int, kind: EpisodeCandidateKind
) -> EpisodeCandidate:
    steps = series.steps[start : start + length]
    first_observation = series.raw_observations[steps[0].observation_index]
    has_shortcut_trigger = any(
        series.raw_observations[step.observation_index].trigger == ObservationTrigger.SHORTCUT for step in steps
    )
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:{kind.value}:{start}:{length}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=kind,
        steps=steps,
        start_index=start,
        observed_at=series.started_at,
        entry_trigger=first_observation.trigger,
        has_shortcut_trigger=has_shortcut_trigger,
        final_status=steps[-1].status,
    )


def build_episode_candidates(all_series: list[OSeries], config: EpisodeConfig) -> list[EpisodeCandidate]:
    candidates: list[EpisodeCandidate] = []
    seen_keys: set[tuple[str, int, int]] = set()

    for series in all_series:
        if len(series.steps) < config.min_symbols:
            continue
        length = min(len(series.steps), config.max_symbols)
        candidates.append(_candidate_from_slice(series, 0, length, EpisodeCandidateKind.FULL_CHUNK))
        # Bir common-run karşılaştırması aynı (series, 0, length) aralığını tekrar bulursa
        # (iki chunk baştan sona birebir aynıysa bu kaçınılmazdır), FULL_CHUNK adayıyla
        # çakışan bir COMMON_RUN kopyası eklenmesin — aksi halde tek gerçek occurrence iki kez
        # sayılır (bkz. Habit'in organic_occurrences kanıtı).
        seen_keys.add((series.series_id, 0, length))

    eligible = [series for series in all_series if len(series.steps) >= config.min_symbols]

    for a_idx in range(len(eligible)):
        series_a = eligible[a_idx]
        symbols_a = series_a.symbols
        for b_idx in range(a_idx + 1, len(eligible)):
            series_b = eligible[b_idx]
            symbols_b = series_b.symbols

            for start_a, start_b, run_length in _all_maximal_common_runs(symbols_a, symbols_b):
                if run_length < config.min_symbols:
                    continue
                capped_length = min(run_length, config.max_symbols)
                for series, start in ((series_a, start_a), (series_b, start_b)):
                    key = (series.series_id, start, capped_length)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    candidates.append(
                        _candidate_from_slice(series, start, capped_length, EpisodeCandidateKind.COMMON_RUN)
                    )

    return candidates
