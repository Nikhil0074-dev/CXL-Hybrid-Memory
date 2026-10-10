# Policy comparison

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 4096, epochs: 40, accesses/epoch: 10000, seeds: [0, 1, 2]
- monitor sample rate: 0.2, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (512 pages, rd 100 ns, wr 100 ns); cxl_dram (1536 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (4096 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_recency | freq_hysteresis | freq_cost | freq_cost_conf | adaptive_full |
|---|---|---|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.664 ± 0.513 | 1.657 ± 0.525 | 1.735 ± 0.535 | 1.697 ± 0.553 | 1.790 ± 0.563 | 1.778 ± 0.550 |
| phase | 1.000 ± 0.000 | 1.465 ± 0.240 | 1.448 ± 0.290 | 1.537 ± 0.149 | 1.536 ± 0.433 | 1.602 ± 0.267 | 1.615 ± 0.332 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/2 workloads (zipf, phase); slower on 0 (none).
- **freq_recency**: faster on 2/2 workloads (zipf, phase); slower on 0 (none).
- **freq_hysteresis**: faster on 2/2 workloads (zipf, phase); slower on 0 (none).
- **freq_cost**: faster on 2/2 workloads (zipf, phase); slower on 0 (none).
- **freq_cost_conf**: faster on 2/2 workloads (zipf, phase); slower on 0 (none).
- **adaptive_full**: faster on 2/2 workloads (zipf, phase); slower on 0 (none).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 381.7 | 1000 | 0.18 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.664 ± 0.513 | 184.9 | 1000 | 0.72 | 21.3 | 7.6 | 15.8 | 3.5 | 307 | 82 |
| freq_recency | 1.657 ± 0.525 | 185.6 | 1000 | 0.72 | 21.5 | 7.7 | 15.9 | 3.5 | 338 | 84 |
| freq_hysteresis | 1.735 ± 0.535 | 187.1 | 1000 | 0.71 | 14.1 | 5.5 | 11.3 | 3.7 | 61 | 61 |
| freq_cost | 1.697 ± 0.553 | 185.4 | 1000 | 0.72 | 18.7 | 6.4 | 14.0 | 3.6 | 276 | 76 |
| freq_cost_conf | 1.790 ± 0.563 | 198.8 | 1000 | 0.71 | 3.6 | 1.3 | 2.9 | 3.8 | 4 | 26 |
| adaptive_full | 1.778 ± 0.550 | 200.2 | 1000 | 0.71 | 3.8 | 1.3 | 2.9 | 3.8 | 1 | 24 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 395.2 | 1000 | 0.16 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.465 ± 0.240 | 220.5 | 1000 | 0.64 | 24.6 | 8.7 | 15.5 | 3.0 | 207 | 66 |
| freq_recency | 1.448 ± 0.290 | 224.1 | 1000 | 0.64 | 24.6 | 8.7 | 15.3 | 3.0 | 209 | 70 |
| freq_hysteresis | 1.537 ± 0.149 | 216.9 | 1000 | 0.64 | 19.1 | 6.9 | 12.7 | 3.1 | 89 | 59 |
| freq_cost | 1.536 ± 0.433 | 213.1 | 1000 | 0.67 | 22.6 | 7.8 | 14.8 | 3.1 | 164 | 65 |
| freq_cost_conf | 1.602 ± 0.267 | 227.4 | 1000 | 0.62 | 7.1 | 2.3 | 4.8 | 3.3 | 9 | 27 |
| adaptive_full | 1.615 ± 0.332 | 225.8 | 1000 | 0.64 | 7.1 | 2.4 | 4.8 | 3.3 | 10 | 30 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
