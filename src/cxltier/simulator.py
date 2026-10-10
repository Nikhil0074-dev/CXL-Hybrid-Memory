"""Trace-driven tiered-memory simulator.

Per epoch:  1) charge access latency using the CURRENT placement
            2) monitor + update hotness (only for policies that use a monitor)
            3) ask the policy for a plan for the NEXT epoch (skipped after the final epoch)
            4) execute the plan; pinned pages and random failures can make operations fail

Timing assumptions (see docs/ASSUMPTIONS.md): accesses are serialized (no memory-level
parallelism), no CPU caches, migration stalls the application for `stall_fraction` of copy time."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import PAGE_BYTES, SimConfig
from .hotness import HotnessEstimator
from .journal import Journal
from .monitor import AccessMonitor
from .planner import Op
from .stats import weighted_percentile
from .workloads import Trace


class SimulatedCrash(Exception):
    """Raised to emulate a power failure after a journal BEGIN and before its COMMIT."""


@dataclass
class EpochResult:
    epoch: int
    access_ns: float = 0.0
    migration_ns: float = 0.0
    overhead_ns: float = 0.0
    tier_access_share: List[float] = field(default_factory=list)
    copies: int = 0
    failed: int = 0
    pingpong: int = 0


@dataclass
class RunResult:
    policy: str
    workload: str
    seed: int
    accesses: int
    total_ns: float
    access_ns: float
    migration_ns: float
    overhead_ns: float
    avg_latency_ns: float
    p50_latency_ns: float
    p99_latency_ns: float
    tier_access_share: List[float]
    promotions: int
    demotions: int
    copies: int
    bytes_migrated: int
    pm_bytes_written: int
    failed_ops: int
    pingpong: int
    per_epoch_ns: List[float]
    per_epoch_tier0_share: List[float]
    final_occupancy: List[int]

    def to_row(self) -> Dict[str, object]:
        d = dict(self.__dict__)
        d["per_epoch_ns"] = ";".join(f"{x:.0f}" for x in self.per_epoch_ns)
        d["per_epoch_tier0_share"] = ";".join(f"{x:.4f}" for x in self.per_epoch_tier0_share)
        d["tier_access_share"] = ";".join(f"{x:.4f}" for x in self.tier_access_share)
        d["final_occupancy"] = ";".join(str(x) for x in self.final_occupancy)
        return d


class PlanContext:
    """Read-only view handed to policies."""

    def __init__(self, sim: "Simulator", epoch: int, obs_r, obs_w, next_epoch) -> None:
        self.sim = sim
        self.epoch = epoch
        self.n = sim.n
        self.tier_of = sim.tier_of
        self.tiers = sim.cfg.tiers
        self.cfg = sim.cfg
        self.est = sim.est
        self.last_migrated = sim.last_migrated
        self.blocked_until = sim.blocked_until
        self.headroom = sim.headroom
        self.accesses_per_epoch = sim.trace.accesses_per_epoch
        self.obs_reads = obs_r
        self.obs_writes = obs_w
        self.next_epoch = next_epoch


class Simulator:
    def __init__(self, cfg: SimConfig, trace: Trace, policy, seed: int = 0,
                 journal: Optional[Journal] = None, journal_scope: str = "persistent",
                 crash_after_groups: Optional[int] = None) -> None:
        if trace.num_pages != cfg.num_pages:
            raise ValueError("trace and config disagree on num_pages")
        if journal_scope not in ("persistent", "all"):
            raise ValueError("journal_scope must be 'persistent' or 'all'")
        self.cfg = cfg
        self.trace = trace
        self.policy = policy
        self.seed = seed
        self.n = cfg.num_pages
        self.headroom = cfg.headroom()
        self.journal = journal
        self.journal_scope = journal_scope
        self.crash_after_groups = crash_after_groups
        self.groups_started = 0
        rng_alloc = random.Random(f"alloc-{trace.name}-{seed}")
        self.order = list(range(self.n))
        rng_alloc.shuffle(self.order)
        rng_pin = random.Random(f"pin-{trace.name}-{seed}")
        k = int(round(cfg.pinned_fraction * self.n))
        self.pinned = set(rng_pin.sample(range(self.n), k)) if k else set()
        self.rng_fail = random.Random(f"fail-{trace.name}-{seed}-{policy.name}")
        self.monitor = AccessMonitor(cfg.monitor_sample_rate,
                                     random.Random(f"mon-{trace.name}-{seed}-{policy.name}"))
        self.est = HotnessEstimator(self.n, trace.accesses_per_epoch) if policy.uses_monitor else None
        self.tier_of = policy.initial_placement(self)
        self._check_placement(self.tier_of)
        self.snapshot = list(self.tier_of)
        T = len(cfg.tiers)
        self.occ = [0] * T
        for t in self.tier_of:
            self.occ[t] += 1
        self.last_migrated = [-10 ** 6] * self.n
        self.last_src = [-1] * self.n
        self.blocked_until = [0] * self.n

    # ---------------------------------------------------------------- placement helpers
    def first_touch_placement(self) -> List[int]:
        T = len(self.cfg.tiers)
        out = [T - 1] * self.n
        t, filled = 0, 0
        for p in self.order:
            while t < T - 1 and filled >= self.cfg.tiers[t].capacity_pages - self.headroom[t]:
                t += 1
                filled = 0
            out[p] = t
            filled += 1
        return out

    def _check_placement(self, tier_of: List[int]) -> None:
        T = len(self.cfg.tiers)
        if len(tier_of) != self.n:
            raise ValueError("placement has wrong length")
        occ = [0] * T
        for t in tier_of:
            if not (0 <= t < T):
                raise ValueError("placement uses an invalid tier")
            occ[t] += 1
        for t in range(T):
            if occ[t] > self.cfg.tiers[t].capacity_pages:
                raise ValueError(f"placement overfills tier {t}")

    # ---------------------------------------------------------------- execution
    def _journaled(self, copies) -> bool:
        if self.journal is None:
            return False
        if self.journal_scope == "all":
            return True
        tiers = self.cfg.tiers
        return any(tiers[s].persistent or tiers[d].persistent for _, s, d in copies)

    def _apply_group(self, copies, e: int, res: EpochResult, stats: dict) -> None:
        """Apply several page copies atomically (mapping changes only after the journal BEGIN)."""
        gid = None
        if self._journaled(copies):
            gid = self.journal.begin(copies)
            self.groups_started += 1
            if self.crash_after_groups is not None and self.groups_started >= self.crash_after_groups:
                raise SimulatedCrash(f"crash after BEGIN of group {gid}")
        for p, src, dst in copies:
            self.tier_of[p] = dst
            self.occ[src] -= 1
            self.occ[dst] += 1
            if self.last_src[p] == dst and e - self.last_migrated[p] <= self.cfg.pingpong_window:
                res.pingpong += 1
                stats["pingpong"] += 1
            self.last_src[p] = src
            self.last_migrated[p] = e
            res.copies += 1
            stats["copies"] += 1
            if dst < src:
                stats["promotions"] += 1
            else:
                stats["demotions"] += 1
            if self.cfg.tiers[dst].persistent:
                stats["pm_bytes"] += PAGE_BYTES
            if not self.policy.free_migration:
                ns = self.cfg.stall_fraction * self.cfg.copy_ns(src, dst)
                res.migration_ns += ns
        if gid is not None:
            self.journal.commit(gid)

    def _fail(self, pages, e: int, res: EpochResult, stats: dict) -> None:
        res.failed += 1
        stats["failed"] += 1
        for p in pages:
            self.blocked_until[p] = e + self.cfg.fail_backoff_epochs

    def _movable(self, p: int) -> bool:
        return p not in self.pinned and self.rng_fail.random() >= self.cfg.migration_fail_prob

    def _execute(self, ops: List[Op], e: int, res: EpochResult, stats: dict) -> None:
        T = len(self.cfg.tiers)
        for op in ops:
            if op.kind == "move":
                p, dst = op.a, op.b
                src = self.tier_of[p]
                if not (0 <= dst < T) or src == dst:
                    self._fail([p], e, res, stats)
                    continue
                if not self._movable(p) or self.occ[dst] >= self.cfg.tiers[dst].capacity_pages:
                    self._fail([p], e, res, stats)
                    continue
                self._apply_group([(p, src, dst)], e, res, stats)
            elif op.kind == "swap":
                p, q = op.a, op.b
                tp, tq = self.tier_of[p], self.tier_of[q]
                if p == q or tp == tq or not (self._movable(p) and self._movable(q)):
                    self._fail([p, q], e, res, stats)
                    continue
                self._apply_group([(p, tp, tq), (q, tq, tp)], e, res, stats)
            else:
                raise ValueError(f"unknown op kind {op.kind}")

    def _apply_oracle(self, target: List[int], e: int, res: EpochResult, stats: dict) -> None:
        self._check_placement(target)
        for p in range(self.n):
            if target[p] != self.tier_of[p]:
                src, dst = self.tier_of[p], target[p]
                self.tier_of[p] = dst
                self.occ[src] -= 1
                self.occ[dst] += 1
                res.copies += 1
                stats["copies"] += 1
                stats["promotions" if dst < src else "demotions"] += 1
                if self.cfg.tiers[dst].persistent:
                    stats["pm_bytes"] += PAGE_BYTES

    # ---------------------------------------------------------------- main loop
    def run(self) -> RunResult:
        cfg, tr = self.cfg, self.trace
        T = len(cfg.tiers)
        rd_ns = [t.read_ns for t in cfg.tiers]
        wr_ns = [t.write_ns for t in cfg.tiers]
        tier_rd = [0] * T
        tier_wr = [0] * T
        stats = dict(copies=0, promotions=0, demotions=0, pm_bytes=0, failed=0, pingpong=0)
        per_epoch, per_epoch_t0 = [], []
        tot_access = tot_mig = tot_over = 0.0
        accesses = 0
        last_e = len(tr.epochs) - 1
        for e, ep in enumerate(tr.epochs):
            res = EpochResult(epoch=e)
            e_rd = [0] * T
            e_wr = [0] * T
            for p, c in ep.reads.items():
                t = self.tier_of[p]
                e_rd[t] += c
            for p, c in ep.writes.items():
                t = self.tier_of[p]
                e_wr[t] += c
            res.access_ns = sum(e_rd[t] * rd_ns[t] + e_wr[t] * wr_ns[t] for t in range(T))
            n_acc = sum(e_rd) + sum(e_wr)
            accesses += n_acc
            for t in range(T):
                tier_rd[t] += e_rd[t]
                tier_wr[t] += e_wr[t]
            res.tier_access_share = [(e_rd[t] + e_wr[t]) / n_acc if n_acc else 0.0 for t in range(T)]

            obs_r: Dict[int, float] = {}
            obs_w: Dict[int, float] = {}
            if self.policy.uses_monitor:
                obs_r, obs_w, samples = self.monitor.observe(ep.reads, ep.writes)
                self.est.update(e, obs_r, obs_w)
                res.overhead_ns += samples * cfg.monitor_cost_per_sample_ns + self.n * cfg.scan_cost_per_page_ns

            if e < last_e:
                nxt = tr.epochs[e + 1]
                ctx = PlanContext(self, e, obs_r, obs_w, nxt)
                if self.policy.free_migration:
                    target = self.policy.oracle_placement(ctx)
                    if target is not None:
                        self._apply_oracle(target, e, res, stats)
                else:
                    ops = self.policy.plan(ctx)
                    self._execute(ops, e, res, stats)
            self.policy.observe_result(res)
            ep_total = res.access_ns + res.migration_ns + res.overhead_ns
            per_epoch.append(ep_total)
            per_epoch_t0.append(res.tier_access_share[0])
            tot_access += res.access_ns
            tot_mig += res.migration_ns
            tot_over += res.overhead_ns

        pairs = []
        for t in range(T):
            pairs.append((rd_ns[t], tier_rd[t]))
            pairs.append((wr_ns[t], tier_wr[t]))
        share = [(tier_rd[t] + tier_wr[t]) / accesses if accesses else 0.0 for t in range(T)]
        return RunResult(
            policy=self.policy.name, workload=tr.name, seed=self.seed, accesses=accesses,
            total_ns=tot_access + tot_mig + tot_over, access_ns=tot_access,
            migration_ns=tot_mig, overhead_ns=tot_over,
            avg_latency_ns=tot_access / accesses if accesses else 0.0,
            p50_latency_ns=weighted_percentile(pairs, 50), p99_latency_ns=weighted_percentile(pairs, 99),
            tier_access_share=share, promotions=stats["promotions"], demotions=stats["demotions"],
            copies=stats["copies"], bytes_migrated=stats["copies"] * PAGE_BYTES,
            pm_bytes_written=stats["pm_bytes"], failed_ops=stats["failed"], pingpong=stats["pingpong"],
            per_epoch_ns=per_epoch, per_epoch_tier0_share=per_epoch_t0, final_occupancy=list(self.occ))
