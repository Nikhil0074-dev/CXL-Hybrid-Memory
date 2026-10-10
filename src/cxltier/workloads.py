"""Synthetic access-trace generators.

A trace is a list of epochs. Each epoch stores how many reads and writes every page received.
Order inside an epoch is not kept: the cost model only needs per-page counts per epoch,
which is a stated simplification (no memory-level parallelism, no cache hierarchy)."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from itertools import accumulate
from typing import Callable, Dict, List


@dataclass
class EpochTrace:
    reads: Dict[int, int]
    writes: Dict[int, int]

    def total(self) -> int:
        return sum(self.reads.values()) + sum(self.writes.values())

    def page_total(self, p: int) -> int:
        return self.reads.get(p, 0) + self.writes.get(p, 0)


@dataclass
class Trace:
    name: str
    description: str
    num_pages: int
    accesses_per_epoch: int
    epochs: List[EpochTrace]


def _split(draws: List[int], write_frac: float) -> EpochTrace:
    n_w = int(round(len(draws) * write_frac))
    return EpochTrace(reads=dict(Counter(draws[n_w:])), writes=dict(Counter(draws[:n_w])))


def _zipf_cum(n: int, s: float) -> List[float]:
    return list(accumulate(1.0 / ((r + 1) ** s) for r in range(n)))


def _draw_zipf(rng: random.Random, perm: List[int], cum: List[float], k: int) -> List[int]:
    ranks = rng.choices(range(len(perm)), cum_weights=cum, k=k)
    return [perm[r] for r in ranks]


def _gen_sequential(n: int, epochs: int, apr: int, rng: random.Random) -> List[EpochTrace]:
    per_page = 4
    step = max(1, apr // per_page)
    start = 0
    out = []
    for _ in range(epochs):
        draws = [(start + j // per_page) % n for j in range(apr)]
        rng.shuffle(draws)
        out.append(_split(draws, 0.1))
        start = (start + step) % n
    return out


def _gen_uniform(n: int, epochs: int, apr: int, rng: random.Random) -> List[EpochTrace]:
    return [_split([rng.randrange(n) for _ in range(apr)], 0.3) for _ in range(epochs)]


def _gen_hotset(n: int, epochs: int, apr: int, rng: random.Random) -> List[EpochTrace]:
    pages = list(range(n))
    rng.shuffle(pages)
    nh = max(1, n // 10)
    weights = [0.9 / nh] * nh + [0.1 / (n - nh)] * (n - nh)
    cum = list(accumulate(weights))
    return [_split(_draw_zipf(rng, pages, cum, apr), 0.2) for _ in range(epochs)]


def _gen_zipf(n: int, epochs: int, apr: int, rng: random.Random, s: float = 1.0,
              wf: float = 0.2) -> List[EpochTrace]:
    perm = list(range(n))
    rng.shuffle(perm)
    cum = _zipf_cum(n, s)
    return [_split(_draw_zipf(rng, perm, cum, apr), wf) for _ in range(epochs)]


def _gen_phase(n: int, epochs: int, apr: int, rng: random.Random, phase_len: int = 10) -> List[EpochTrace]:
    cum = _zipf_cum(n, 1.1)
    perm = list(range(n))
    out = []
    for e in range(epochs):
        if e % phase_len == 0:
            rng.shuffle(perm)       # the hot set moves to different pages
        out.append(_split(_draw_zipf(rng, perm, cum, apr), 0.2))
    return out


def _gen_scan_hot(n: int, epochs: int, apr: int, rng: random.Random) -> List[EpochTrace]:
    perm = list(range(n))
    rng.shuffle(perm)
    cum = _zipf_cum(n, 1.0)
    n_scan = int(apr * 0.4)
    per_page = 2
    step = max(1, n_scan // per_page)
    start = 0
    out = []
    for _ in range(epochs):
        hot = _draw_zipf(rng, perm, cum, apr - n_scan)
        scan = [(start + j // per_page) % n for j in range(n_scan)]
        start = (start + step) % n
        draws = hot + scan
        rng.shuffle(draws)
        out.append(_split(draws, 0.15))
    return out


def _gen_write_heavy(n: int, epochs: int, apr: int, rng: random.Random) -> List[EpochTrace]:
    return _gen_zipf(n, epochs, apr, rng, s=1.0, wf=0.7)


WORKLOADS: Dict[str, Callable[[int, int, int, random.Random], List[EpochTrace]]] = {
    "sequential": _gen_sequential,
    "uniform": _gen_uniform,
    "hotset": _gen_hotset,
    "zipf": _gen_zipf,
    "phase": _gen_phase,
    "scan_hot": _gen_scan_hot,
    "write_heavy": _gen_write_heavy,
}

DESCRIPTIONS: Dict[str, str] = {
    "sequential": "Sliding sequential sweep, 4 touches/page, 10% writes. No stable hot set: migration should not help.",
    "uniform": "Uniform random, 30% writes. No locality at all: migration should not help (negative-control).",
    "hotset": "10% of pages receive 90% of accesses, stable over time, 20% writes. Best case for promotion.",
    "zipf": "Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.",
    "phase": "Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.",
    "scan_hot": "Stable Zipf hot set (60%) plus a sequential scan (40%). Tests scan pollution of the fast tier.",
    "write_heavy": "Zipf(s=1.0) with 70% writes. Tests the cost of writes on the persistent tier.",
}


def generate(name: str, num_pages: int, epochs: int, accesses_per_epoch: int, seed: int = 0) -> Trace:
    if name not in WORKLOADS:
        raise KeyError(f"unknown workload '{name}'. Known: {sorted(WORKLOADS)}")
    if num_pages < 16:
        raise ValueError("num_pages must be at least 16")
    rng = random.Random(f"{name}-{seed}")
    eps = WORKLOADS[name](num_pages, epochs, accesses_per_epoch, rng)
    return Trace(name=name, description=DESCRIPTIONS[name], num_pages=num_pages,
                 accesses_per_epoch=accesses_per_epoch, epochs=eps)
