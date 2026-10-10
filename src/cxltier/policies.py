"""Placement policies. All policies see the same trace and the same initial allocation."""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional

from .planner import Op, PlannerParams, build_plan


class Policy:
    name = "base"
    description = ""
    uses_monitor = False      # pays monitoring overhead and gets a HotnessEstimator
    free_migration = False    # only the clairvoyant oracle sets this
    is_oracle = False

    def initial_placement(self, sim) -> List[int]:
        return sim.first_touch_placement()

    def plan(self, ctx) -> List[Op]:
        return []

    def oracle_placement(self, ctx) -> Optional[List[int]]:
        return None

    def observe_result(self, res) -> None:
        pass


# ------------------------------------------------------------------ static baselines
class StaticFirstTouch(Policy):
    name = "static_firsttouch"
    description = "Pages stay where first-touch allocation put them (fill DDR5, then CXL, then persistent)."


class StaticInterleave(Policy):
    name = "static_interleave"
    description = "Pages spread across tiers in proportion to capacity (like weighted interleave). No migration."

    def initial_placement(self, sim) -> List[int]:
        T = len(sim.cfg.tiers)
        limit = [sim.cfg.tiers[t].capacity_pages - sim.headroom[t] for t in range(T)]
        count = [0] * T
        out = [0] * sim.n
        for p in sim.order:
            best, best_ratio = -1, None
            for t in range(T):
                if count[t] >= limit[t]:
                    continue
                ratio = count[t] / limit[t]
                if best_ratio is None or ratio < best_ratio:
                    best, best_ratio = t, ratio
            out[p] = best
            count[best] += 1
        return out


class OracleStatic(Policy):
    name = "oracle_static"
    is_oracle = True
    description = "UPPER BOUND for static placement: knows the whole trace, ranks pages by total cost-weighted accesses."

    def initial_placement(self, sim) -> List[int]:
        w = [0.0] * sim.n
        for ep in sim.trace.epochs:
            for p, c in ep.reads.items():
                w[p] += c
            for p, c in ep.writes.items():
                w[p] += c * 2.0
        return rank_fill(sim, w)


def rank_fill(sim, weights: List[float]) -> List[int]:
    T = len(sim.cfg.tiers)
    limit = [sim.cfg.tiers[t].capacity_pages - sim.headroom[t] for t in range(T)]
    limit[-1] = sim.cfg.tiers[-1].capacity_pages
    ranked = sorted(range(sim.n), key=lambda p: (-weights[p], p))
    out = [T - 1] * sim.n
    t, filled = 0, 0
    for p in ranked:
        while t < T - 1 and filled >= limit[t]:
            t += 1
            filled = 0
        out[p] = t
        filled += 1
    return out


class OracleEpoch(Policy):
    name = "oracle_epoch"
    is_oracle = True
    free_migration = True
    description = "UPPER BOUND: re-ranks pages by the NEXT epoch's true counts and moves them for free."

    def oracle_placement(self, ctx) -> Optional[List[int]]:
        if ctx.next_epoch is None:
            return None
        w = [0.0] * ctx.n
        for p, c in ctx.next_epoch.reads.items():
            w[p] += c
        for p, c in ctx.next_epoch.writes.items():
            w[p] += c * 2.0
        return rank_fill(ctx.sim, w)


# ------------------------------------------------------------------ OS-like approximation
class OSLike(Policy):
    """Rough approximation of Linux-style tiering (NUMA hinting + LRU demotion). NOT the real kernel:
    promote pages touched >=2 times this epoch and >=1 time last epoch, one tier up, in arbitrary
    order, under a rate limit; demote least-recently-used pages to keep headroom."""
    name = "os_like"
    uses_monitor = True
    description = "Approximation of kernel-style tiering: two-touch promotion, LRU demotion, rate limit. Not the real kernel."

    def __init__(self, promote_budget: int = 256, min_touches: int = 2) -> None:
        self.promote_budget = promote_budget
        self.min_touches = min_touches
        self.prev: Dict[int, float] = {}
        self.last_seen: Optional[List[int]] = None

    def plan(self, ctx) -> List[Op]:
        n, T, e = ctx.n, len(ctx.tiers), ctx.epoch
        if self.last_seen is None:
            self.last_seen = [-1] * n
        cur: Dict[int, float] = {}
        for p, c in ctx.obs_reads.items():
            cur[p] = cur.get(p, 0.0) + c
        for p, c in ctx.obs_writes.items():
            cur[p] = cur.get(p, 0.0) + c
        for p in cur:
            self.last_seen[p] = e
        wt = list(ctx.tier_of)
        free = [ctx.tiers[t].capacity_pages for t in range(T)]
        for t in wt:
            free[t] -= 1
        reserve = ctx.headroom
        ops: List[Op] = []
        lru: Dict[int, List[int]] = {}
        ptr: Dict[int, int] = {}

        def demote_lru(t: int) -> bool:
            if t >= T - 1:
                return False
            if free[t + 1] <= reserve[t + 1] and not demote_lru(t + 1):
                return False
            if t not in lru:
                lru[t] = sorted((i for i in range(n) if wt[i] == t and e >= ctx.blocked_until[i]),
                                key=lambda i: (self.last_seen[i], i))
                ptr[t] = 0
            while ptr[t] < len(lru[t]) and wt[lru[t][ptr[t]]] != t:
                ptr[t] += 1
            if ptr[t] >= len(lru[t]):
                return False
            v = lru[t][ptr[t]]
            ptr[t] += 1
            wt[v] = t + 1
            free[t] += 1
            free[t + 1] -= 1
            ops.append(Op("move", v, t + 1))
            return True

        for t in range(T - 2, -1, -1):
            while free[t] < reserve[t]:
                if not demote_lru(t):
                    break

        cand = [p for p, c in cur.items()
                if wt[p] > 0 and c >= self.min_touches and self.prev.get(p, 0.0) >= 1
                and e >= ctx.blocked_until[p]]
        cand.sort(key=lambda p: (p + e * 997) % n)
        done = 0
        for p in cand:
            if done >= self.promote_budget:
                break
            dst = wt[p] - 1
            while free[dst] <= reserve[dst]:
                if not demote_lru(dst):
                    break
            if free[dst] <= reserve[dst]:
                continue
            src = wt[p]
            wt[p] = dst
            free[src] += 1
            free[dst] -= 1
            ops.append(Op("move", p, dst))
            done += 1
        self.prev = cur
        return ops


# ------------------------------------------------------------------ score-based policies
class PlannerPolicy(Policy):
    uses_monitor = True

    def __init__(self, name: str, description: str, params: PlannerParams,
                 estimator_use_recency: bool = False) -> None:
        self.name = name
        self.description = description
        self.params = params

    def plan(self, ctx) -> List[Op]:
        return build_plan(ctx, self.params)


class AdaptiveFull(PlannerPolicy):
    """Frequency + recency + hysteresis + cooldown + cost model + feedback control.
    Feedback: if many migrations are reversed within the ping-pong window, widen the hysteresis
    margin and shrink the budget; if migrations are stable, relax both. If the share of accesses
    served by tier 0 falls sharply (a phase change), open the budget fully for this epoch."""

    def __init__(self, base: PlannerParams, h_min: float = 0.10, h_max: float = 0.80,
                 b_min: int = 32, b_max: int = 512) -> None:
        super().__init__("adaptive_full",
                         "Frequency+recency, hysteresis, cooldown, noise-aware cost model, feedback-controlled budget and margin.",
                         base)
        self.h_min, self.h_max, self.b_min, self.b_max = h_min, h_max, b_min, b_max
        self.h = max(h_min, base.hysteresis)
        self.budget = base.budget_pages if base.budget_pages is not None else b_max
        self.share_ewma: Optional[float] = None

    def plan(self, ctx) -> List[Op]:
        p = dataclasses.replace(self.params, hysteresis=self.h, budget_pages=self.budget)
        return build_plan(ctx, p)

    def observe_result(self, res) -> None:
        if res.copies > 0:
            ratio = res.pingpong / res.copies
            if ratio > 0.15:
                self.h = min(self.h_max, self.h * 1.5 + 0.02)
                self.budget = max(self.b_min, self.budget // 2)
            else:
                self.h = max(self.h_min, self.h * 0.9)
                self.budget = min(self.b_max, int(self.budget * 1.25) + 1)
        share = res.tier_access_share[0]
        if self.share_ewma is not None and share < self.share_ewma - 0.10:
            self.budget = self.b_max
            self.h = self.h_min
        self.share_ewma = share if self.share_ewma is None else 0.7 * self.share_ewma + 0.3 * share


POLICY_NAMES = [
    "static_firsttouch", "static_interleave", "os_like", "freq_only", "freq_recency",
    "freq_hysteresis", "freq_cost", "freq_cost_conf", "adaptive_full", "oracle_static", "oracle_epoch",
]
ABLATION = ["static_firsttouch", "freq_only", "freq_recency", "freq_hysteresis", "freq_cost",
            "freq_cost_conf", "adaptive_full"]
BASELINE = "static_firsttouch"


def make_policy(name: str, cfg=None, **overrides) -> Policy:
    if name == "static_firsttouch":
        return StaticFirstTouch()
    if name == "static_interleave":
        return StaticInterleave()
    if name == "oracle_static":
        return OracleStatic()
    if name == "oracle_epoch":
        return OracleEpoch()
    if name == "os_like":
        return OSLike()
    base = dict(hot_thr=2.0, warm_thr=1.0)
    base.update(overrides)
    if name == "freq_only":
        return PlannerPolicy(name, "Frequency (EWMA) only; no recency, hysteresis, cooldown, budget or cost check.",
                             PlannerParams(**base))
    if name == "freq_recency":
        return PlannerPolicy(name, "Frequency x recency; otherwise as freq_only.",
                             PlannerParams(use_recency=True, **base))
    if name == "freq_hysteresis":
        return PlannerPolicy(name, "Frequency + 30% hysteresis + 3-epoch cooldown + 512-page budget.",
                             PlannerParams(hysteresis=0.3, cooldown=3, budget_pages=512, **base))
    if name == "freq_cost":
        return PlannerPolicy(name, "Frequency + cost/benefit check (8-epoch horizon); no hysteresis.",
                             PlannerParams(use_cost=True, horizon=8.0, **base))
    if name == "freq_cost_conf":
        return PlannerPolicy(name, "Frequency + cost/benefit check using confidence bounds on the access rate (noise-aware).",
                             PlannerParams(use_cost=True, horizon=8.0, confidence_z=1.5, **base))
    if name == "adaptive_full":
        return AdaptiveFull(PlannerParams(use_recency=True, hysteresis=0.3, cooldown=3,
                                          budget_pages=256, use_cost=True, horizon=8.0,
                                          confidence_z=1.5, **base))
    raise KeyError(f"unknown policy '{name}'. Known: {POLICY_NAMES}")
