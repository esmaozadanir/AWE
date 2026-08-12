"""Ayrıştırıcı (discriminative) sembol ağırlıklandırması (bölüm 49).

Bir sembol subject'in neredeyse bütün O-Series'lerinde görülüyorsa (ör. ortak bir başlangıç
ekranı, bölüm 20/115), Family benzerlik skorunu şişirmemesi için düşük ağırlık alır. Ham IDF,
az sayıda O-Series'i olan subject'lerde anlamsız uç değerler ürettiğinden add-one smoothing
uygulanır ve örneklem `min_series_for_weighting` altındaysa uniform ağırlığa düşülür
(IMPLEMENTATION_PLAN.md 2.6).

Ağırlık asla tam sıfıra inmez (`min_weight` alt sınırı korunur). Bunun nedeni: bir subject'in
gözlenen davranışının tamamı TEK bir Habit'e aitse (yaygın durum), o Habit'in kendi çekirdek
sembolleri de "hemen her yerde görülüyor" sayılır ve ham IDF onları sıfıra çeker — bu ise nadir
görülen tek seferlik bir sapmayı (bkz. bir detour) yapay biçimde asıl çekirdekten daha
"ayırt edici" gösterip benzerlik skorunu bozar. Alt sınır bu tersine dönmeyi önler.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from awe.domain.tokens import Symbol

UNIFORM_WEIGHT = 1.0
DEFAULT_MIN_WEIGHT = 0.15


def compute_discriminative_weights(
    series_symbol_sequences: Iterable[tuple[Symbol, ...]],
    min_series_for_weighting: int,
    min_weight: float = DEFAULT_MIN_WEIGHT,
) -> dict[Symbol, float]:
    sequences = list(series_symbol_sequences)
    total_series = len(sequences)

    all_symbols: set[Symbol] = set()
    document_frequency: dict[Symbol, int] = {}
    for symbols in sequences:
        for symbol in set(symbols):
            all_symbols.add(symbol)
            document_frequency[symbol] = document_frequency.get(symbol, 0) + 1

    if total_series < min_series_for_weighting or not all_symbols:
        return {symbol: UNIFORM_WEIGHT for symbol in all_symbols}

    raw_weights = {
        symbol: -math.log((df + 1) / (total_series + 1))
        for symbol, df in document_frequency.items()
    }
    max_weight = max(raw_weights.values()) if raw_weights else 1.0
    if max_weight <= 0:
        return {symbol: UNIFORM_WEIGHT for symbol in all_symbols}
    return {symbol: max(min_weight, weight / max_weight) for symbol, weight in raw_weights.items()}


def weight_of(symbol: Symbol, weights: dict[Symbol, float]) -> float:
    return weights.get(symbol, UNIFORM_WEIGHT)
