# Architecture and design

## 1. Problem and scope
- Working sets can exceed local DDR5. Static placement wastes fast memory or pays slow-tier latency on hot pages.
- Goal: place hot pages in DDR5, warm pages in CXL DRAM, cold pages in a persistent/capacity tier, and **show a measurable benefit over baselines**.
- Established facts: tier latencies differ; migration costs time; access counts are noisy. Hypotheses tested here: cost-aware, noise-aware placement beats simple policies (RQ1) and avoids losses on workloads with no locality (RQ2).

## 2. Four environments and what each can prove
| Env | Can show | Cannot show |
|---|---|---|
| A. Real CXL hardware | real latency, bandwidth, kernel behavior | needs hardware; not available here |
| B. Linux host with emulated tiers (e.g., NUMA nodes) | real `move_pages` behavior and costs | CXL-specific latency/persistence |
| C. User-space prototype with controlled tiers | policy plumbing, overhead | true hardware effects |
| D. Trace-driven simulator (**this project, built**) | policy comparison, thrashing, ablation | absolute performance |
A VM or WSL2 does not give realistic CXL; do not assume it does.

## 3. Alternatives considered
- **A** static placement; **B** Linux user-space frequency controller; **C** adaptive cost-aware controller built simulator-first; **D** kernel-integrated controller; **E** plain simulator with baseline policies only.
- Scores are in `docs/DECISION_MATRIX.md`. Raw totals: C 3.87, E 3.95, A 3.40, B 2.92, D 2.36.
- **E has the highest raw total but fails the gate** (no new policy to test, so it cannot answer RQ1). It is kept as the test bench inside C. This is a judgment call; the 0.08 gap is smaller than the uncertainty in my own scoring.

## 4. Preferred solution
- **Solution C, implemented as simulator + policy library.** Implementation type: *simulator* (with a small Linux probe stub).
- Why: reproducible, safe, cheap, can model three tiers, lets all policies see identical traces.
- Cannot prove: real-hardware speedups, kernel interaction, true persistence behavior.
- Evolution path: Environment B (NUMA-emulated tiers, `move_pages`) -> real CXL (see ROADMAP.md).

## 5. Three-tier model
- Tier 0 local DDR5: hot pages. Keeps 2% free headroom.
- Tier 1 CXL DRAM (volatile): warm pages, overflow from tier 0. Keeps 2% headroom.
- Tier 2 persistent tier (**emulated**): cold pages, capacity. Slower writes, extra cost to write in. Moving pages here does not make them durable (docs/PERSISTENCE.md).
- Migration paths: any tier to any tier, as a single move (free slot) or an atomic swap (full destination).

## 6. Hotness estimator (`hotness.py`)
- Monitor sees each access with probability `s` (default 0.2); estimates are count / s.
- Per page, EWMA of the **fraction of the epoch's accesses** (reads and writes tracked separately). Dividing by the epoch total makes windows comparable.
- Relative heat = EWMA fraction x number of pages. 1.0 = average page.
- Optional recency factor = 1 - w + w x exp(-age / tau), w=0.5, tau=2 epochs.
- Real systems cannot read exact per-page counts from user space. Real sources: page-table accessed-bit scans, NUMA hinting faults, DAMON, PEBS/IBS samples. Not modeled in detail.

## 7. Placement policy (`planner.py`)
- Promote a page into tier t when relative score >= threshold (hot 2.0 for tier 0, warm 1.0 for tier 1) AND:
  - there is a free slot above the headroom reserve, or
  - a colder victim exists (score lower by the hysteresis margin).
- Victim goes to the next tier down if it has space; otherwise it swaps places with the promoted page.
- Demotion is **pressure-driven**: only to restore headroom or make room. No demotion just because a page is "cold" (it would cost copy time for no gain).
- New pages: first-touch fill DDR5 (minus headroom), then CXL DRAM, then persistent tier.
- Unmovable pages: failed move marks the page blocked for 10 epochs. Capacity exhaustion: plan skips; executor refuses moves into a full tier.

## 8. Cost model and confidence bounds
- Benefit per epoch for moving page i from tier a to b = reads x (read_a - read_b) + writes x (write_a - write_b), using predicted access counts per epoch.
- Move only if `horizon x (gain of promoted page + loss of victim) > stall_fraction x (copy cost of both pages)`.
- **Noise-aware step (the project's main idea):** use the lower confidence bound for the promoted page's rate and the upper bound for the victim's rate. Variance of an EWMA of Poisson counts = mean x alpha/(2-alpha), divided by the sample rate. z = 1.5.
- Not included: cache effects, bandwidth contention, policy CPU cost beyond the monitor charge.

## 9. Thrashing control
- Hysteresis margin (candidate must beat victim by 30%) and raised thresholds.
- Cooldown (3 epochs), per-epoch budget (256-512 page copies).
- `adaptive_full` adds feedback: if >15% of copies are reversals within 5 epochs, widen margin and halve budget; if tier-0 access share drops by 10 points, open the budget. **Results show no proven gain from this feedback** (docs/RESULTS.md).

## 10. Correctness (what the real system must do)
- Use the kernel's migration path (`move_pages`, NUMA/tier demotion/promotion). Never copy physical pages by hand: the kernel handles page-table updates, TLB shootdown, page locks, refcounts, writeback state.
- Kernel responsibilities: virtual address stays the same, concurrent access blocking, COW, huge-page splitting, pinned/device pages refusal.
- Controller responsibilities: choose pages, respect budgets, handle failures (back off), keep its own metadata consistent.
- Simulator mirrors this: pinned pages refuse, random failures, atomic swap groups, capacity checks at execution time.

## 11. Components (as built)
| Component | File | Runs where in a real system |
|---|---|---|
| Access monitor | monitor.py | kernel/PMU-assisted; user space reads results |
| Hotness estimator | hotness.py | user space |
| Placement policy + planner | planner.py, policies.py | user space |
| Migration executor | simulator.py (`_execute`) | kernel via `move_pages` |
| Persistent-tier adapter / journal | journal.py | user space + device library |
| Statistics, reports | experiments.py, report.py | user space |
| Linux backend | linux_backend.py | user space (Phase 2) |

## 12. Metadata
- Ephemeral: per-page EWMA, last-access epoch, cooldown. Lives in memory; losing it only costs re-learning.
- Durable: migration journal (persistent tier only) and experiment logs (`runs.csv`). Per-access events are never stored; only per-epoch aggregates.

## 13. Experiment design
- Workloads (7): sequential, uniform, hotset, zipf, phase, scan_hot, write_heavy.
- Baselines: static_firsttouch, static_interleave, os_like (approximation), freq_only, plus ablation steps; oracle_static and oracle_epoch as bounds.
- 5 seeds, paired comparison, 95% CI. Metrics measured in the simulator: total time, average and p99 access latency, tier access share, bytes migrated, persistent bytes written, ping-pong count, failed ops, monitor/migration time share.
- Not measured: energy, real tail latency under contention.

## 14. Safety
- Simulator is unprivileged and safe. For real hardware: least privilege, bounded migration budget per epoch, kill-switch that stops migration, test on a disposable machine, never migrate pinned/device pages.

## 15. Risks
| Risk | Effect | Mitigation |
|---|---|---|
| Assumed costs are wrong | wrong conclusions | calibrate with microbenchmarks (ROADMAP) |
| Random-order baseline too weak | speedups overstated | add real allocation-order traces |
| Synthetic traces unrealistic | poor transfer | replay real traces (DAMON/PEBS) |
| Hand-set thresholds | overfitting | tune on separate workloads |
| Real monitor is much noisier | policy degrades | test sample-rate sweep (done in simulation only) |
| Persistent tier semantics | data loss on crash | follow PERSISTENCE.md |
