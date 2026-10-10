"""Small statistics helpers (standard library only)."""
from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
        15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        25: 2.060, 30: 2.042}


def t_critical(df: int) -> float:
    """Two-sided 95% Student-t critical value (table with interpolation)."""
    if df < 1:
        return 0.0
    if df in _T95:
        return _T95[df]
    if df > 30:
        return 1.96 if df > 120 else 2.0
    lo = max(k for k in _T95 if k < df)
    hi = min(k for k in _T95 if k > df)
    frac = (df - lo) / (hi - lo)
    return _T95[lo] + frac * (_T95[hi] - _T95[lo])


def mean_std_ci(xs: Sequence[float]) -> Tuple[float, float, float]:
    """Return (mean, sample std, half-width of the 95% confidence interval)."""
    n = len(xs)
    if n == 0:
        raise ValueError("empty sample")
    m = sum(xs) / n
    if n < 2:
        return m, 0.0, 0.0
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(var)
    return m, sd, t_critical(n - 1) * sd / math.sqrt(n)


def weighted_percentile(pairs: Iterable[Tuple[float, float]], q: float) -> float:
    """pairs = (value, weight). q in [0, 100]. Smallest value whose cumulative weight >= q%."""
    items: List[Tuple[float, float]] = sorted((v, w) for v, w in pairs if w > 0)
    if not items:
        return 0.0
    total = sum(w for _, w in items)
    target = total * q / 100.0
    acc = 0.0
    for v, w in items:
        acc += w
        if acc >= target - 1e-9:
            return v
    return items[-1][0]
