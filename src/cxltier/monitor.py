"""Access monitor model.

Real systems cannot read exact per-page access counts from user space. They use page-table
accessed-bit scans, NUMA hinting faults, DAMON-style sampling, or PEBS/IBS samples. This
class models that loss of information: each access is seen with probability `sample_rate`,
and counts are scaled by 1/sample_rate to give an unbiased (but noisy) estimate."""
from __future__ import annotations

import math
import random
from typing import Dict, Tuple


def binomial(rng: random.Random, n: int, p: float) -> int:
    if n <= 0 or p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    if n <= 40:
        return sum(1 for _ in range(n) if rng.random() < p)
    mean = n * p
    sd = math.sqrt(n * p * (1.0 - p))
    return min(n, max(0, int(round(rng.gauss(mean, sd)))))


class AccessMonitor:
    def __init__(self, sample_rate: float, rng: random.Random) -> None:
        if not (0.0 < sample_rate <= 1.0):
            raise ValueError("sample_rate must be in (0, 1]")
        self.sample_rate = sample_rate
        self.rng = rng

    def observe(self, reads: Dict[int, int], writes: Dict[int, int]
                ) -> Tuple[Dict[int, float], Dict[int, float], int]:
        """Return (estimated reads, estimated writes, number of samples taken)."""
        s = self.sample_rate
        est_r: Dict[int, float] = {}
        est_w: Dict[int, float] = {}
        samples = 0
        for p, c in reads.items():
            k = binomial(self.rng, c, s)
            if k:
                est_r[p] = k / s
                samples += k
        for p, c in writes.items():
            k = binomial(self.rng, c, s)
            if k:
                est_w[p] = k / s
                samples += k
        return est_r, est_w, samples
