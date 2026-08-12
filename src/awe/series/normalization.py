"""Raw adım dizisinden karşılaştırma projeksiyonu: retry ve bounded detour normalizasyonu.

İki farklı örüntü kasıtlı olarak birbirinden ayrılır:

* **Retry** — aynı sembol ardışık tekrar ediyor ve önceki deneme `fail`/`cancel` durumunda
  (bölüm 42). Tek adıma sıkıştırılır, retry sayısı ayrıca tutulur.
* **Detour** — açık bir `navigate_back` sinyalinden sonra önceki bir sembole dönülüyor
  (bölüm 41). Yalnızca `effect=navigate_back` gözlenmişse tetiklenir; aksi halde tekrarlayan
  bir sembol otomatik olarak detour sayılmaz, çünkü bu gerçek bir loop olabilir (bölüm 114).
  Bu, action string'ine bakarak "back" tahmini yapmak yerine (yasak, bölüm 1) canonical
  `effect` sözlüğüne dayanan açık bir yapısal karardır.

Her iki örüntü de ham kanıtı silmez; yalnızca Family karşılaştırması için kullanılan
projeksiyonu etkiler (bölüm 36).
"""

from __future__ import annotations

from dataclasses import dataclass

from awe.domain.enums import ObservationEffect, ObservationStatus
from awe.domain.series import RetryEvidence
from awe.domain.tokens import BehaviorStep

_RETRYABLE_STATUSES = (ObservationStatus.FAIL, ObservationStatus.CANCEL)


@dataclass(slots=True)
class NormalizationResult:
    steps: list[BehaviorStep]
    retries: list[RetryEvidence]
    detour_step_count: int


def normalize_steps(raw_steps: list[BehaviorStep], detour_max_length: int) -> NormalizationResult:
    result: list[BehaviorStep] = []
    retries: list[RetryEvidence] = []
    detour_step_count = 0
    pending_return_merge = False
    consecutive_back_pops = 0

    for step in raw_steps:
        if result and result[-1].symbol == step.symbol and result[-1].status in _RETRYABLE_STATUSES:
            if retries and retries[-1].symbol == step.symbol:
                retries[-1] = RetryEvidence(
                    symbol=step.symbol, failed_attempts=retries[-1].failed_attempts + 1
                )
            else:
                retries.append(RetryEvidence(symbol=step.symbol, failed_attempts=1))
            result[-1] = step
            pending_return_merge = False
            consecutive_back_pops = 0
            continue

        if step.token.effect == ObservationEffect.NAVIGATE_BACK:
            if result and consecutive_back_pops < detour_max_length:
                result.pop()
                detour_step_count += 1
                consecutive_back_pops += 1
                pending_return_merge = True
            else:
                # Yığın zaten boş (geri gidilecek kayıtlı bir adım kalmamış) ya da bounded
                # sınır aşılmış: `back` kendi başına anlamlı bir davranış adımı değildir,
                # bu yüzden literal bir sembol olarak eklenmez — sessizce yutulur. Aksi halde
                # art arda gelen fazla "back" basışları normalize edilmiş diziye yapay
                # "back" sembolleri olarak sızar (bölüm 41: detour normalizasyonu bounded
                # olmalı, ama ham kanıtı uydurma sembollerle kirletmemeli).
                detour_step_count += 1
                pending_return_merge = False
            continue

        if pending_return_merge and result and result[-1].symbol == step.symbol:
            detour_step_count += 1
            pending_return_merge = False
            continue

        result.append(step)
        pending_return_merge = False
        consecutive_back_pops = 0

    return NormalizationResult(steps=result, retries=retries, detour_step_count=detour_step_count)
