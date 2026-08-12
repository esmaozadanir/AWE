"""Sembol dizileri arası ayrıştırıcı-ağırlıklı benzerlik ve core-kapsama hesapları."""

from __future__ import annotations

from awe.domain.tokens import Symbol
from awe.families.weighting import weight_of


def weighted_similarity(
    left: tuple[Symbol, ...], right: tuple[Symbol, ...], weights: dict[Symbol, float]
) -> float:
    """Ağırlıklı LCS üzerinden Dice benzerlik katsayısı (0-1 arası, simetrik).

    LCS, dizide bulunmayan araya girmiş semboller (opsiyonel adım/detour artığı) varlığında
    dahi ortak yapıyı bulur — bitişiklik gerektirmez. Bu, bölüm 53'teki opsiyonel prefix/
    suffix/middle örneklerinin family kimliğini bozmamasını sağlar.
    """

    if not left or not right:
        return 0.0

    n, m = len(left), len(right)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if left[i - 1] == right[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + weight_of(left[i - 1], weights)
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    weighted_lcs = dp[n][m]
    left_weight = sum(weight_of(s, weights) for s in left)
    right_weight = sum(weight_of(s, weights) for s in right)
    total = left_weight + right_weight
    if total <= 0:
        return 0.0
    return (2 * weighted_lcs) / total


def order_preserving_coverage(symbols: tuple[Symbol, ...], pairs: set[tuple[Symbol, Symbol]]) -> float:
    """Verilen (predecessor, successor) çiftlerinin kaçının `symbols` içinde SIRAYLA (bitişik
    olması şart değil) göründüğünü ölçer. Opsiyonel ara adımlar bu kontrolü bozmaz."""

    if not pairs:
        return 1.0

    positions: dict[Symbol, list[int]] = {}
    for idx, symbol in enumerate(symbols):
        positions.setdefault(symbol, []).append(idx)

    covered = 0
    for predecessor, successor in pairs:
        pred_positions = positions.get(predecessor)
        succ_positions = positions.get(successor)
        if not pred_positions or not succ_positions:
            continue
        if pred_positions[0] < succ_positions[-1]:
            covered += 1

    return covered / len(pairs)
