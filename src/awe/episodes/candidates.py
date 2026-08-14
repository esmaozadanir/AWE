"""Episode Candidate Builder: Exact Base Family eşleştirmesine giren aday davranış
birimlerini üretir. Henüz habit kararı vermez.

Üç kaynaktan aday çıkar:
1. Bir `OSeries` (structural chunk) chunk'ın tamamı, hiç bölünmeden (`FULL_CHUNK`).
2. Aynı chunk'ın (ya da bir COMMON_SUBSEQUENCE eşleşmesinin) strong pozisyonlarda bölünmesiyle
   üretilen, birbirine ÇAKIŞABİLEN "endpoint hypothesis" adayları (`EPISODE_SPAN` — bkz.
   `_endpoint_hypotheses`, docs/engine-decisions.md #10). Strong pozisyon = target taşıyan ya da
   outcome-evidence effect'li adım (Anchor Resolver'ın kendi tanımıyla aynı, bkz.
   `awe.domain.enums.OUTCOME_EVIDENCE_EFFECTS`). Her strong pozisyon BAĞIMSIZ bir hipotezdir —
   bir span SINIRI değil: chunk başından o pozisyona kadarki önek kendi adayını oluşturur,
   sonraki bir strong pozisyon bunu geçersiz kılmaz ya da yutmaz. Son strong pozisyondan sonra
   kalan (kendi içinde strong pozisyonu olmayan) bir kuyruk varsa, o da ayrı bir aday olur.
3. Farklı chunk'lar arasında bulunan, sıra-korumalı exact ortak alt diziler
   (`COMMON_SUBSEQUENCE`) — bunlar da (2)'deki AYNI hipotez-bölme işleminden geçer.

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

Maksimum aday uzunluğu `EpisodeConfig.max_symbols` ile konfigüre edilebilir; varsayılanı
`None` (sınırsız, kullanıcı kararıyla -- bkz. docs/engine-decisions.md). LCS araması zaten bu
değere bakmaksızın chunk'ın TAM sembol dizisi üzerinde çalışır (aşağıdaki `_iterative_common_
subsequences` çağrısına bak) -- `max_symbols` yalnızca SONUÇ adayının uzunluğunu kırpar, arama
maliyetini değiştirmez.
"""

from __future__ import annotations

from awe.config.engine_config import EpisodeConfig
from awe.domain.enums import OUTCOME_EVIDENCE_EFFECTS, EpisodeCandidateKind, ObservationTrigger
from awe.domain.episode import EpisodeCandidate
from awe.domain.series import OSeries
from awe.domain.tokens import BehaviorStep, Symbol


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


def _is_strong_position(step: BehaviorStep) -> bool:
    """Anchor Resolver'ın "strong position" tanımıyla (target-carrying OR outcome-evidence
    effect) birebir aynı, ama Family/Target Resolver hiç çalışmadan ham `BehaviorStep`ten
    hesaplanır. `variant.fingerprint[i] is not None` ile `step.target is not None` tam
    eşdeğerdir: `TargetVariant.fingerprint`, `EpisodeCandidate.targets` üzerinden doğrudan
    `step.target`ten türer, hiçbir aggregation/kayıp yoktur (bkz. docs/engine-decisions.md
    #10)."""
    return step.target is not None or step.symbol[1] in OUTCOME_EVIDENCE_EFFECTS


def _endpoint_hypotheses(indices: list[int], steps: tuple[BehaviorStep, ...]) -> list[list[int]]:
    """`indices` (artan sıralı; FULL_CHUNK kaynaklıysa ardışık, COMMON_SUBSEQUENCE kaynaklıysa
    ardışık olmayabilir) içindeki her strong pozisyonu BAĞIMSIZ bir "endpoint hypothesis"
    sayar — span SINIRI değil. Her strong pozisyon için, `indices`in BAŞINDAN o pozisyona
    kadarki önek, ayrı ve ÇAKIŞAN bir hipotez olarak üretilir; hiçbiri diğerini yutmaz ya da
    geçersiz kılmaz (bkz. docs/engine-decisions.md #10 — chunk'ı strong pozisyonlarda AYRIK
    span'lara bölen ilk tasarım, gerçek referans verisini kırdığı için reddedildi). Son strong
    pozisyondan SONRA kalan (kendi içinde strong pozisyonu olmayan bir kuyruk) varsa, o da
    ayrı, WEAK-anchor'a uygun bir hipotez olur. Hiç strong pozisyon yoksa `indices`in TAMAMI
    tek bir hipotez olarak döner (bugünkü WEAK-anchor yolu değişmeden korunur).

    Kanıt: `len(hypotheses) == 1` ANCAK VE ANCAK sıfır strong pozisyon varsa geçerlidir — bu
    durumda hipotez `indices`in birebir kendisidir; aksi halde en az bir GERÇEK önek (`indices`
    'in tamamından kısa) üretilir. Çağıran bunu FULL_CHUNK/EPISODE_SPAN ve
    COMMON_SUBSEQUENCE/EPISODE_SPAN etiketlemesi için güvenle kullanır."""
    strong = [i for i in indices if _is_strong_position(steps[i])]
    if not strong:
        return [list(indices)]

    hypotheses = [[i for i in indices if i <= boundary] for boundary in strong]
    remainder = [i for i in indices if i > strong[-1]]
    if remainder:
        hypotheses.append(remainder)
    return hypotheses


def _cap_hypothesis(hypothesis: list[int], steps: tuple[BehaviorStep, ...], max_symbols: int | None) -> list[int]:
    """`max_symbols` aşılırsa kırpar. Hipotez KENDİ son adımında bir strong pozisyonda
    bitiyorsa (önek hipotezi, ya da tesadüfen sonu strong olan tek-hipotez durumu), kırpma
    BAŞTAN yapılır — bitiş noktası (asıl kanıt) korunur, yoksa strong pozisyonun kendisi
    kırpılıp atılabilir. Bitmiyorsa (sıfır strong pozisyonlu bütün blok YA DA son strong
    pozisyondan sonraki kuyruk), kırpma SONDAN yapılır — bu, `max_symbols` bu katmana
    eklenmeden ÖNCEKİ (sınırsız varsayılan öncesi) davranışla birebir aynıdır."""
    if max_symbols is None or len(hypothesis) <= max_symbols:
        return hypothesis
    if _is_strong_position(steps[hypothesis[-1]]):
        return hypothesis[-max_symbols:]
    return hypothesis[:max_symbols]


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
        full_indices = list(range(len(series.steps)))
        hypotheses = _endpoint_hypotheses(full_indices, series.steps)
        kind = EpisodeCandidateKind.FULL_CHUNK if len(hypotheses) == 1 else EpisodeCandidateKind.EPISODE_SPAN
        for hypothesis in hypotheses:
            indices = _cap_hypothesis(hypothesis, series.steps, config.max_symbols)
            if len(indices) < config.min_symbols:
                continue
            candidates.append(_candidate_from_indices(series, indices, kind))
            # Bir common-subsequence karşılaştırması aynı pozisyon kümesini tekrar bulursa (iki
            # chunk baştan sona birebir aynıysa bu kaçınılmazdır), bu hipotezle çakışan bir
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
                for series, raw_indices in ((series_a, left_indices), (series_b, right_indices)):
                    hypotheses = _endpoint_hypotheses(raw_indices, series.steps)
                    kind = (
                        EpisodeCandidateKind.COMMON_SUBSEQUENCE
                        if len(hypotheses) == 1
                        else EpisodeCandidateKind.EPISODE_SPAN
                    )
                    for hypothesis in hypotheses:
                        indices = _cap_hypothesis(hypothesis, series.steps, config.max_symbols)
                        if len(indices) < config.min_symbols:
                            continue
                        key = (series.series_id, tuple(indices))
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        candidates.append(_candidate_from_indices(series, indices, kind))

    return candidates
