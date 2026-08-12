"""Episode Candidate Builder: Exact Base Family eşleştirmesine giren aday davranış
birimlerini üretir. Henüz habit kararı vermez.

İki aday tipi çıkarılır:
1. Her `OSeries` (structural chunk) chunk'ın tamamı (`FULL_CHUNK`).
2. Farklı chunk'lar arasında bulunan, sıra-korumalı exact ortak alt diziler
   (`COMMON_SUBSEQUENCE`).

Step eşitliği `Symbol = (action, effect, screen, mapping_version)` tam eşitliğidir; bir
adımın DEĞERİNDE hiçbir tolerans yoktur (fuzzy/yaklaşık eşleşme yok). Ancak iki chunk
arasındaki ortak deseni ararken **ardışıklık (contiguity) zorunlu değildir** — sıra
korunduğu sürece araya, kaynak dizide eşleşmeyen adımlar girebilir (ör. bir bildirim
kontrolü, yanlış tıklama, retry). Bu kasıtlı bir tasarım kararıdır ve bölüm 6.4'ün
"Optional step toleransı yoktur" ifadesinden bilinçli bir sapmadır: gerçek event
loglarında kullanıcılar aynı davranışı neredeyse hiçbir zaman birebir aynı, kesintisiz
adım dizisiyle tekrar etmez; yalnızca ardışık ortak alt dize (substring) arayan bir
algoritma bu yüzden gerçek alışkanlıkları aşırı parçalar (bölüm 9.3'ün kabul ettiği
riskin, kullanım verisinde kabul edilemez boyuta ulaşması). Klasik "en uzun ortak alt
dizi" (LCS) problemidir — eşleşen her adım hâlâ tam (exact) değer eşitliği taşımalıdır,
yalnızca aralarındaki boşluk toleransı gevşetilmiştir; bu hâlâ fuzzy/yaklaşık bir
benzerlik skoru DEĞİLDİR.

Bir chunk çifti arasında birden fazla bağımsız ortak desen olabileceğinden (ör. iki farklı
alışkanlık aynı iki session'da da görülüyorsa), tek bir LCS bulunduktan sonra eşleşen
pozisyonlar her iki diziden de çıkarılır ve arama `min_symbols` altına düşene kadar
tekrarlanır ("iterative peeling").

Maksimum aday uzunluğu belgede kesinleştirilmemiş bir karardır ("Eski MVP'deki max=8
korunacaksa bu ayrıca sabitlenip test edilmelidir") — burada `EpisodeConfig.max_symbols`
(varsayılan 8) olarak sabitlenmiş ve konfigüre edilebilir bırakılmıştır.
"""

from __future__ import annotations

from awe.config.engine_config import EpisodeConfig
from awe.domain.enums import EpisodeCandidateKind, ObservationTrigger
from awe.domain.episode import EpisodeCandidate
from awe.domain.series import OSeries
from awe.domain.tokens import Symbol


def _longest_common_subsequence_indices(
    left: tuple[Symbol, ...], right: tuple[Symbol, ...]
) -> tuple[list[int], list[int]]:
    """İki sembol dizisi arasında sıra-korumalı (ardışık olması gerekmeyen) TEK bir en uzun
    ortak alt diziyi (LCS) bulur. Eşit uzunlukta birden fazla aday varsa deterministik bir
    seçim yapılır (traceback eşitlikte her zaman `left`'te geriye gitmeyi tercih eder).
    Döner: `(left'teki eşleşen pozisyonlar, right'teki eşleşen pozisyonlar)` — ikisi de aynı
    uzunlukta ve sırayla birbirine karşılık gelir."""

    n, m = len(left), len(right)
    if n == 0 or m == 0:
        return [], []

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if left[i - 1] == right[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = dp[i - 1][j] if dp[i - 1][j] >= dp[i][j - 1] else dp[i][j - 1]

    left_indices: list[int] = []
    right_indices: list[int] = []
    i, j = n, m
    while i > 0 and j > 0:
        if left[i - 1] == right[j - 1]:
            left_indices.append(i - 1)
            right_indices.append(j - 1)
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    left_indices.reverse()
    right_indices.reverse()
    return left_indices, right_indices


def _iterative_common_subsequences(
    left: tuple[Symbol, ...], right: tuple[Symbol, ...], min_length: int
) -> list[tuple[list[int], list[int]]]:
    """`_longest_common_subsequence_indices`'i tekrarlı uygular: bulunan her LCS'in eşleşen
    pozisyonlarını her iki diziden de çıkarır (maskeler) ve kalan pozisyonlar üzerinde
    `min_length`'in altına düşene kadar tekrar arar. Bu, bir chunk çiftinin birden fazla
    bağımsız ortak deseni paylaşabildiği durumları yakalar."""

    results: list[tuple[list[int], list[int]]] = []
    left_active = list(range(len(left)))
    right_active = list(range(len(right)))

    while left_active and right_active:
        sub_left = tuple(left[i] for i in left_active)
        sub_right = tuple(right[j] for j in right_active)
        rel_left, rel_right = _longest_common_subsequence_indices(sub_left, sub_right)
        if len(rel_left) < min_length:
            break

        left_indices = [left_active[i] for i in rel_left]
        right_indices = [right_active[j] for j in rel_right]
        results.append((left_indices, right_indices))

        left_used = set(left_indices)
        right_used = set(right_indices)
        left_active = [i for i in left_active if i not in left_used]
        right_active = [j for j in right_active if j not in right_used]

    return results


def _candidate_from_indices(series: OSeries, indices: list[int], kind: EpisodeCandidateKind) -> EpisodeCandidate:
    steps = tuple(series.steps[i] for i in indices)
    first_observation = series.raw_observations[steps[0].observation_index]
    has_shortcut_trigger = any(
        series.raw_observations[step.observation_index].trigger == ObservationTrigger.SHORTCUT for step in steps
    )
    index_key = "-".join(str(i) for i in indices)
    return EpisodeCandidate(
        candidate_id=f"{series.series_id}:{kind.value}:{index_key}",
        project_id=series.project_id,
        subject_id=series.subject_id,
        session_id=series.session_id,
        series_id=series.series_id,
        kind=kind,
        steps=steps,
        step_indices=tuple(indices),
        observed_at=series.started_at,
        entry_trigger=first_observation.trigger,
        has_shortcut_trigger=has_shortcut_trigger,
        final_status=steps[-1].status,
    )


def build_episode_candidates(all_series: list[OSeries], config: EpisodeConfig) -> list[EpisodeCandidate]:
    candidates: list[EpisodeCandidate] = []
    seen_keys: set[tuple[str, tuple[int, ...]]] = set()

    for series in all_series:
        if len(series.steps) < config.min_symbols:
            continue
        indices = list(range(min(len(series.steps), config.max_symbols)))
        candidates.append(_candidate_from_indices(series, indices, EpisodeCandidateKind.FULL_CHUNK))
        # Bir common-subsequence karşılaştırması aynı pozisyon kümesini tekrar bulursa (iki
        # chunk baştan sona birebir aynıysa bu kaçınılmazdır), FULL_CHUNK adayıyla çakışan bir
        # kopya eklenmesin — aksi halde tek gerçek occurrence iki kez sayılır (bkz. Habit'in
        # organic_occurrences kanıtı).
        seen_keys.add((series.series_id, tuple(indices)))

    eligible = [series for series in all_series if len(series.steps) >= config.min_symbols]

    for a_idx in range(len(eligible)):
        series_a = eligible[a_idx]
        symbols_a = series_a.symbols
        for b_idx in range(a_idx + 1, len(eligible)):
            series_b = eligible[b_idx]
            symbols_b = series_b.symbols

            for left_indices, right_indices in _iterative_common_subsequences(
                symbols_a, symbols_b, config.min_symbols
            ):
                capped_left = left_indices[: config.max_symbols]
                capped_right = right_indices[: config.max_symbols]
                for series, indices in ((series_a, capped_left), (series_b, capped_right)):
                    key = (series.series_id, tuple(indices))
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    candidates.append(
                        _candidate_from_indices(series, indices, EpisodeCandidateKind.COMMON_SUBSEQUENCE)
                    )

    return candidates
