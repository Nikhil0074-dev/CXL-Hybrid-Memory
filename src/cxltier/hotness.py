"""Hotness estimator.

heat_rd[p], heat_wr[p]  : exponentially weighted moving average (EWMA) of the FRACTION of an
                          epoch's accesses that went to page p. Dividing by the epoch total makes
                          observation windows of different length comparable.
relative heat           : (heat_rd + heat_wr) * num_pages. 1.0 = an average page; 3.0 = three
                          times the average. Thresholds are expressed in these units so they do
                          not depend on trace length or memory size.
recency factor          : 1 - w + w * exp(-(epoch - last_access_epoch) / tau), in [1-w, 1].
score                   : relative heat * recency factor (recency optional).
"""
from __future__ import annotations

import math
from typing import Dict, List


class HotnessEstimator:
    def __init__(self, num_pages: int, epoch_len: int, alpha: float = 0.4,
                 tau: float = 2.0, w_recency: float = 0.5) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be in (0, 1]")
        if tau <= 0:
            raise ValueError("tau must be positive")
        if not (0.0 <= w_recency < 1.0):
            raise ValueError("w_recency must be in [0, 1)")
        if epoch_len <= 0 or num_pages <= 0:
            raise ValueError("epoch_len and num_pages must be positive")
        self.n = num_pages
        self.epoch_len = epoch_len
        self.alpha = alpha
        self.tau = tau
        self.w = w_recency
        self.rd: List[float] = [0.0] * num_pages
        self.wr: List[float] = [0.0] * num_pages
        self.last: List[int] = [-10 ** 6] * num_pages

    def update(self, epoch: int, est_reads: Dict[int, float], est_writes: Dict[int, float]) -> None:
        a = self.alpha
        keep = 1.0 - a
        self.rd = [x * keep for x in self.rd]
        self.wr = [x * keep for x in self.wr]
        scale = a / self.epoch_len
        for p, c in est_reads.items():
            self.rd[p] += c * scale
            self.last[p] = epoch
        for p, c in est_writes.items():
            self.wr[p] += c * scale
            self.last[p] = epoch

    def heat_rel(self, p: int) -> float:
        return (self.rd[p] + self.wr[p]) * self.n

    def recency_factor(self, p: int, epoch: int) -> float:
        age = epoch - self.last[p]
        return 1.0 - self.w + self.w * math.exp(-age / self.tau)

    def score(self, p: int, epoch: int, use_recency: bool) -> float:
        h = self.heat_rel(p)
        return h * self.recency_factor(p, epoch) if use_recency else h
