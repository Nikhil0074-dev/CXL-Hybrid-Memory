"""Shared placement planner used by every score-based policy.

Plan = ordered list of Ops. Op("move", page, dst_tier) or Op("swap", page_a, page_b).
Demotion is pressure-driven (as in Linux reclaim-based demotion): pages leave a fast tier only
to keep headroom or to make room for a hotter page. Promotion needs score >= threshold and
either a free slot above the reserve or a colder victim to exchange with."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Op:
    kind: str   # "move" or "swap"
    a: int
    b: int      # destination tier for "move", partner page for "swap"


@dataclass
class PlannerParams:
    hot_thr: float = 2.0            # relative score needed to enter tier 0
    warm_thr: float = 1.0           # relative score needed to enter tier 1+
    use_recency: bool = False
    hysteresis: float = 0.0         # candidate must beat victim by this fraction; also raises thresholds
    cooldown: int = 0               # epochs a page is frozen after a migration
    budget_pages: Optional[int] = None  # max page copies per epoch
    use_cost: bool = False
    horizon: float = 8.0            # epochs of future benefit assumed
    cost_safety: float = 1.0        # benefit must exceed cost * safety
    confidence_z: float = 0.0       # >0: use lower (promoted page) / upper (victim) confidence bound of access rate


def build_plan(ctx, params: PlannerParams) -> List[Op]:
    n = ctx.n
    T = len(ctx.tiers)
    e = ctx.epoch
    est = ctx.est
    tiers = ctx.tiers
    acc = ctx.accesses_per_epoch
    h = params.hysteresis
    reserve = ctx.headroom
    budget = float("inf") if params.budget_pages is None else params.budget_pages

    factor = [1.0] * n
    if params.use_recency:
        factor = [est.recency_factor(i, e) for i in range(n)]
    sc = [(est.rd[i] + est.wr[i]) * n * factor[i] for i in range(n)]
    elig = [(e - ctx.last_migrated[i] >= params.cooldown) and e >= ctx.blocked_until[i]
            for i in range(n)]

    wt = list(ctx.tier_of)
    free = [tiers[t].capacity_pages for t in range(T)]
    for t in wt:
        free[t] -= 1
    ops: List[Op] = []
    used = [0]

    def do_move(p: int, dst: int) -> None:
        src = wt[p]
        wt[p] = dst
        free[src] += 1
        free[dst] -= 1
        ops.append(Op("move", p, dst))
        used[0] += 1

    def do_swap(p: int, q: int) -> None:
        wt[p], wt[q] = wt[q], wt[p]
        ops.append(Op("swap", p, q))
        used[0] += 2

    def stall_cost(src: int, dst: int) -> float:
        return ctx.cfg.stall_fraction * ctx.cfg.copy_ns(src, dst)

    z = params.confidence_z
    # variance of an EWMA of Poisson counts (steady state), inflated by 1/sample_rate for sampling noise
    var_scale = est.alpha / (2.0 - est.alpha) / ctx.cfg.monitor_sample_rate

    def gain(i: int, a: int, b: int, sign: int) -> float:
        """Expected ns saved per epoch if page i moves from tier a to tier b.
        sign=+1 -> pessimistic (lower-bound) rate, used for the page being promoted;
        sign=-1 -> pessimistic for the victim, i.e. upper-bound rate (its loss is larger)."""
        rr = est.rd[i] * acc * factor[i]
        rw = est.wr[i] * acc * factor[i]
        if z > 0.0:
            tot = rr + rw
            if tot > 0.0:
                adj = max(0.0, tot - sign * z * math.sqrt(tot * var_scale)) / tot
                rr *= adj
                rw *= adj
        return rr * (tiers[a].read_ns - tiers[b].read_ns) + rw * (tiers[a].write_ns - tiers[b].write_ns)

    def benefit_ok(p: int, src: int, target: int, v: Optional[int], vdst: int) -> bool:
        net = gain(p, src, target, +1)
        cost = stall_cost(src, target)
        if v is not None:
            net += gain(v, target, vdst, -1)
            cost += stall_cost(target, vdst)
        return params.horizon * net > cost * params.cost_safety

    # --- Step A: restore headroom (pressure demotion), lowest tier first -------------------
    for t in range(T - 2, -1, -1):
        need = reserve[t] - free[t]
        if need <= 0:
            continue
        victims = sorted((i for i in range(n) if wt[i] == t and elig[i]), key=sc.__getitem__)
        for v in victims:
            if need <= 0 or free[t + 1] <= 0:
                break
            do_move(v, t + 1)
            need -= 1

    # --- Steps B/C: promotions ----------------------------------------------------------------
    def promote_into(target: int, thr: float) -> None:
        cap_t = tiers[target].capacity_pages
        cand = [i for i in range(n) if wt[i] > target and sc[i] >= thr and elig[i]]
        if not cand:
            return
        cand.sort(key=lambda i: -sc[i])
        del cand[cap_t:]
        victims = sorted((i for i in range(n) if wt[i] == target and elig[i]), key=sc.__getitem__)
        vi = 0
        lower = target + 1
        for p in cand:
            if used[0] >= budget:
                break
            src = wt[p]
            if free[target] > reserve[target]:
                if params.use_cost and not benefit_ok(p, src, target, None, src):
                    continue
                do_move(p, target)
                continue
            while vi < len(victims) and wt[victims[vi]] != target:
                vi += 1
            if vi >= len(victims):
                break
            v = victims[vi]
            if sc[p] <= sc[v] or sc[p] < sc[v] * (1.0 + h):
                break
            two_step = lower < T and src > lower and free[lower] > reserve[lower]
            vdst = lower if two_step else src
            if used[0] + 2 > budget:
                break
            if params.use_cost and not benefit_ok(p, src, target, v, vdst):
                continue
            if two_step:
                do_move(v, vdst)
                do_move(p, target)
            else:
                do_swap(p, v)
            vi += 1

    for target in range(T - 1):
        thr = (params.hot_thr if target == 0 else params.warm_thr) * (1.0 + h)
        promote_into(target, thr)
    return ops
