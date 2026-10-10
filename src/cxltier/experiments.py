"""Experiment runner: workloads x policies x seeds, with shared traces so comparisons are paired."""
from __future__ import annotations

import csv
import os
from typing import Callable, Dict, List, Optional, Sequence

from .config import SimConfig
from .policies import BASELINE, make_policy
from .simulator import RunResult, Simulator
from .stats import mean_std_ci
from .workloads import generate


def run_matrix(cfg: SimConfig, workloads: Sequence[str], policies: Sequence[str], seeds: Sequence[int],
               progress: Optional[Callable[[str], None]] = None) -> List[RunResult]:
    out: List[RunResult] = []
    for w in workloads:
        for s in seeds:
            tr = generate(w, cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, s)
            for pn in policies:
                out.append(Simulator(cfg, tr, make_policy(pn, cfg), seed=s).run())
            if progress:
                progress(f"{w} seed {s} done")
    return out


def write_csv(results: Sequence[RunResult], path: str) -> None:
    if not results:
        raise ValueError("no results to write")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rows = [r.to_row() for r in results]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


def summarize(results: Sequence[RunResult], baseline: str = BASELINE) -> Dict[str, Dict[str, Dict[str, float]]]:
    """summary[workload][policy] -> stats. Speedup is paired per seed against `baseline`."""
    by: Dict[str, Dict[str, Dict[int, RunResult]]] = {}
    for r in results:
        by.setdefault(r.workload, {}).setdefault(r.policy, {})[r.seed] = r
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for w, pols in by.items():
        base = pols.get(baseline, {})
        out[w] = {}
        for pn, runs in pols.items():
            seeds = sorted(runs)
            sp = [base[s].total_ns / runs[s].total_ns for s in seeds if s in base]
            m, sd, ci = mean_std_ci(sp) if sp else (float("nan"), 0.0, 0.0)
            def avg(f):
                return sum(f(runs[s]) for s in seeds) / len(seeds)
            out[w][pn] = dict(
                n=len(seeds), speedup=m, speedup_std=sd, speedup_ci=ci,
                total_ms=avg(lambda r: r.total_ns) / 1e6,
                avg_lat=avg(lambda r: r.avg_latency_ns), p99=avg(lambda r: r.p99_latency_ns),
                t0_share=avg(lambda r: r.tier_access_share[0]),
                mig_mb=avg(lambda r: r.bytes_migrated) / 2 ** 20,
                pm_mb=avg(lambda r: r.pm_bytes_written) / 2 ** 20,
                overhead_pct=100.0 * avg(lambda r: r.overhead_ns / r.total_ns),
                mig_pct=100.0 * avg(lambda r: r.migration_ns / r.total_ns),
                pingpong=avg(lambda r: r.pingpong), copies=avg(lambda r: r.copies),
                failed=avg(lambda r: r.failed_ops))
    return out
