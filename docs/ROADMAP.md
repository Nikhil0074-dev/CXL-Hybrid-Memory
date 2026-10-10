# Roadmap to real hardware

Status: milestones 1-10 and 12 below are done in simulation. Milestone 11 is not started.

| # | Milestone | Status | Acceptance |
|---|---|---|---|
| 1 | Literature and feasibility | **partly done.** Needs a proper citation pass | cite primary sources, see below |
| 2 | Requirements and architecture | done | docs/ARCHITECTURE.md |
| 3 | Workload generator | done | 7 workloads, deterministic, tested |
| 4 | Tiered simulator | done | invariants tested |
| 5 | Access collection | done (model only) | sampled monitor |
| 6 | Hotness classification | done | normalized EWMA |
| 7 | Placement and migration | done | planner + executor |
| 8 | Stability controls | done | hysteresis, cooldown, budget, feedback |
| 9 | Baselines and benchmarks | done | 11 policies |
| 10 | Analysis | done | docs/RESULTS.md |
| 11 | Real hardware | **not started** | see steps below |
| 12 | Testing and docs | done | 31 tests |

## Milestone 11 steps
1. Run `python3 -m cxltier probe` on the target. Check for CXL devices, CPU-less NUMA nodes, memory tiers, `demotion_enabled`.
2. If no CXL: use a two-socket machine and treat the remote node as the slow tier (Environment B). Measure read/write latency and copy bandwidth per node pair; put them in `configs/`.
3. Replace assumed numbers in `config.py` with measured ones. Re-run the suite. Note which conclusions change.
4. Build an access source: DAMON, or PEBS-style sampling, or accessed-bit scans. Feed per-epoch counts into `HotnessEstimator`.
5. Use `LinuxMigrator(dry_run=True)` first, then real moves on a test process only, with a small budget.
6. Compare against the kernel's own tiering (NUMA balancing + memory-tier demotion) with the same workload.
7. Only then consider a persistent tier, after confirming real persistence support (docs/PERSISTENCE.md).

## Related work to read and cite (from memory; verify details before citing)
- Linux kernel docs: NUMA memory policy, `move_pages(2)`, memory tiering and demotion, CXL driver docs, DAMON.
- TPP: Transparent Page Placement for CXL-Enabled Tiered Memory (Meta; ASPLOS 2023).
- HeMem (SOSP 2021) and Memtis (SOSP 2023): tiered memory management with sampling.
- Nimble page management for tiered memory (ASPLOS 2019).
- CXL specification (CXL Consortium) for CXL.mem and Type-3 devices.
I did not browse the web for this session, so check titles, venues and claims against the primary sources.
