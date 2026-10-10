"""Markdown report generation. Every number comes from simulator runs; nothing is hand-written."""
from __future__ import annotations

from typing import Dict, List, Sequence

from .config import SimConfig
from .workloads import DESCRIPTIONS


def _fmt_sp(d: Dict[str, float]) -> str:
    if d["n"] > 1:
        return f"{d['speedup']:.3f} ± {d['speedup_ci']:.3f}"
    return f"{d['speedup']:.3f}"


def build_report(title: str, cfg: SimConfig, summary: Dict[str, Dict[str, Dict[str, float]]],
                 policies: Sequence[str], seeds: Sequence[int]) -> str:
    L: List[str] = [f"# {title}", ""]
    L += ["**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).",
          "The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;",
          "value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.", ""]
    L += [f"- pages: {cfg.num_pages}, epochs: {cfg.epochs}, accesses/epoch: {cfg.accesses_per_epoch}, seeds: {list(seeds)}",
          f"- monitor sample rate: {cfg.monitor_sample_rate}, stall fraction: {cfg.stall_fraction}, pinned pages: {cfg.pinned_fraction:.1%}",
          "- tiers: " + "; ".join(f"{t.name} ({t.capacity_pages} pages, rd {t.read_ns:.0f} ns, wr {t.write_ns:.0f} ns)"
                                    for t in cfg.tiers), ""]
    L += ["## Speedup summary", "", "| workload | " + " | ".join(policies) + " |",
          "|---|" + "---|" * len(policies)]
    for w in summary:
        L.append(f"| {w} | " + " | ".join(_fmt_sp(summary[w][p]) if p in summary[w] else "-" for p in policies) + " |")
    L.append("")
    L += ["## Where each policy wins or loses (vs static_firsttouch, mean speedup)", ""]
    for p in policies:
        if p == "static_firsttouch":
            continue
        wins = [w for w in summary if p in summary[w] and summary[w][p]["speedup"] > 1.02]
        loss = [w for w in summary if p in summary[w] and summary[w][p]["speedup"] < 0.98]
        L.append(f"- **{p}**: faster on {len(wins)}/{len(summary)} workloads ({', '.join(wins) or 'none'}); "
                 f"slower on {len(loss)} ({', '.join(loss) or 'none'}).")
    L.append("")
    for w in summary:
        L += [f"## Workload: {w}", "", DESCRIPTIONS.get(w, ""), "",
              "| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for p in policies:
            if p not in summary[w]:
                continue
            d = summary[w][p]
            L.append(f"| {p} | {_fmt_sp(d)} | {d['avg_lat']:.1f} | {d['p99']:.0f} | {d['t0_share']:.2f} | "
                     f"{d['mig_mb']:.1f} | {d['pm_mb']:.1f} | {d['mig_pct']:.1f} | {d['overhead_pct']:.1f} | "
                     f"{d['pingpong']:.0f} | {d['failed']:.0f} |")
        L.append("")
    L += ["## Limits of these results", "",
          "- Simulation with assumed costs; relative ordering may change on real hardware.",
          "- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.",
          "- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.",
          "- p99 is over per-access latency values (tier/read/write), excluding migration stalls.", ""]
    return "\n".join(L)
