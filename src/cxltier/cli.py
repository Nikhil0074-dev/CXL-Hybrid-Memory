"""Command line interface: python -m cxltier <command>."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import decision_matrix, linux_backend
from .config import SimConfig
from .experiments import run_matrix, summarize, write_csv
from .plotting import grouped_bar_svg, line_svg
from .policies import ABLATION, POLICY_NAMES
from .report import build_report
from .workloads import WORKLOADS

HEADLINE = ["static_interleave", "os_like", "freq_only", "freq_hysteresis", "freq_cost_conf", "adaptive_full",
            "oracle_static"]


def _cfg(args: argparse.Namespace) -> SimConfig:
    cfg = SimConfig.from_json(args.config) if getattr(args, "config", None) else SimConfig()
    kw = {}
    for name in ("num_pages", "epochs", "accesses_per_epoch", "monitor_sample_rate", "stall_fraction"):
        v = getattr(args, name, None)
        if v is not None:
            kw[name] = v
    return cfg.replace(**kw) if kw else cfg


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _select(arg: Optional[str], allowed: List[str], what: str) -> List[str]:
    if arg is None or arg == "all":
        return list(allowed)
    if arg == "ablation" and what == "policy":
        return list(ABLATION)
    names = [a.strip() for a in arg.split(",") if a.strip()]
    for n in names:
        if n not in allowed:
            raise SystemExit(f"unknown {what} '{n}'. Choose from: {', '.join(allowed)}")
    if "static_firsttouch" not in names and what == "policy":
        names.insert(0, "static_firsttouch")  # needed as the paired baseline
    return names


def _emit(out: str, title: str, cfg: SimConfig, results, policies: List[str], seeds: List[int]) -> None:
    summary = summarize(results)
    write_csv(results, os.path.join(out, "runs.csv"))
    _write(os.path.join(out, "report.md"), build_report(title, cfg, summary, policies, seeds))
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    groups = list(summary)
    series = {p: [summary[w][p]["speedup"] for w in groups] for p in policies
              if p != "static_firsttouch" and not p.startswith("oracle_epoch")}
    _write(os.path.join(out, "speedup.svg"), grouped_bar_svg(title + " (simulation)", groups, series))
    if "phase" in groups:
        phase = {}
        for r in results:
            if r.workload == "phase" and r.seed == seeds[0] and r.policy in ("static_firsttouch", "freq_only", "adaptive_full", "os_like"):
                phase[r.policy] = [x / 1e3 for x in r.per_epoch_ns]
        if phase:
            _write(os.path.join(out, "phase_timeline.svg"),
                   line_svg("Per-epoch time, phase workload (hot set moves every 10 epochs)", phase, "microseconds per epoch"))


def cmd_run(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    wl = _select(args.workloads, list(WORKLOADS), "workload")
    pol = _select(args.policies, POLICY_NAMES, "policy")
    seeds = list(range(args.seeds))
    res = run_matrix(cfg, wl, pol, seeds, progress=lambda m: print(m, file=sys.stderr))
    _emit(args.out, args.title, cfg, res, pol, seeds)
    print(f"wrote {args.out}/report.md")
    return 0


def cmd_suite(args: argparse.Namespace) -> int:
    base = _cfg(args)
    if args.quick:
        base = base.replace(num_pages=1024, epochs=20, accesses_per_epoch=4000)
    seeds = list(range(2 if args.quick else args.seeds))
    wl = list(WORKLOADS)
    out = args.out
    # 1. main comparison
    pol = [p for p in POLICY_NAMES if p != "oracle_epoch"] + ["oracle_epoch"]
    res = run_matrix(base, wl, pol, seeds, progress=lambda m: print("main:", m, file=sys.stderr))
    _emit(os.path.join(out, "main"), "Main comparison", base, res, pol, seeds)
    # 2. ablation
    res = run_matrix(base, wl, ABLATION, seeds, progress=lambda m: print("ablation:", m, file=sys.stderr))
    _emit(os.path.join(out, "ablation"), "Ablation study", base, res, ABLATION, seeds)
    # 3. sensitivity (monitor sampling and stall fraction) on three workloads
    sens_wl = ["zipf", "phase", "uniform"]
    sens_pol = ["static_firsttouch", "freq_only", "freq_cost_conf", "adaptive_full"]
    for label, key, values in (("sample_rate", "monitor_sample_rate", [1.0, 0.2, 0.05]),
                               ("stall_fraction", "stall_fraction", [0.25, 0.5, 1.0])):
        for v in values:
            c = base.replace(**{key: v})
            r = run_matrix(c, sens_wl, sens_pol, seeds)
            _emit(os.path.join(out, "sensitivity", f"{label}_{v}"), f"Sensitivity {label}={v}", c, r, sens_pol, seeds)
    _write(os.path.join(out, "decision_matrix.md"), decision_matrix.to_markdown())
    print(f"suite finished: {out}")
    return 0


def cmd_matrix(args: argparse.Namespace) -> int:
    print(decision_matrix.to_markdown())
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    print(json.dumps(linux_backend.probe(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="cxltier", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", help="JSON file with SimConfig fields")
        p.add_argument("--num-pages", dest="num_pages", type=int)
        p.add_argument("--epochs", type=int)
        p.add_argument("--accesses-per-epoch", dest="accesses_per_epoch", type=int)
        p.add_argument("--monitor-sample-rate", dest="monitor_sample_rate", type=float)
        p.add_argument("--stall-fraction", dest="stall_fraction", type=float)
        p.add_argument("--seeds", type=int, default=5)
        p.add_argument("--out", default="results/run")

    r = sub.add_parser("run", help="run selected workloads and policies")
    common(r)
    r.add_argument("--workloads", help="comma list or 'all'. Known: " + ",".join(WORKLOADS))
    r.add_argument("--policies", help="comma list, 'all' or 'ablation'. Known: " + ",".join(POLICY_NAMES))
    r.add_argument("--title", default="Policy comparison")
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("suite", help="main comparison + ablation + sensitivity")
    common(s)
    s.add_argument("--quick", action="store_true", help="small sizes, 2 seeds")
    s.set_defaults(fn=cmd_suite)

    sub.add_parser("matrix", help="print the weighted decision matrix").set_defaults(fn=cmd_matrix)
    sub.add_parser("probe", help="probe this Linux host for NUMA/CXL/tiering support").set_defaults(fn=cmd_probe)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
