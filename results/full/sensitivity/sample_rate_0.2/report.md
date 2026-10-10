# Sensitivity sample_rate=0.2

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 4096, epochs: 40, accesses/epoch: 10000, seeds: [0, 1, 2, 3, 4]
- monitor sample rate: 0.2, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (512 pages, rd 100 ns, wr 100 ns); cxl_dram (1536 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (4096 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.759 ± 0.243 | 1.897 ± 0.269 | 1.883 ± 0.263 |
| phase | 1.000 ± 0.000 | 1.517 ± 0.123 | 1.650 ± 0.127 | 1.658 ± 0.139 |
| uniform | 1.000 ± 0.000 | 0.515 ± 0.001 | 0.937 ± 0.001 | 0.931 ± 0.002 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 404.3 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.759 ± 0.243 | 185.3 | 1000 | 0.72 | 21.4 | 7.6 | 15.8 | 3.5 | 318 | 78 |
| freq_cost_conf | 1.897 ± 0.269 | 198.8 | 1000 | 0.71 | 3.7 | 1.3 | 2.9 | 3.8 | 4 | 25 |
| adaptive_full | 1.883 ± 0.263 | 200.3 | 1000 | 0.71 | 3.8 | 1.3 | 3.0 | 3.8 | 2 | 23 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 396.0 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.517 ± 0.123 | 211.8 | 1000 | 0.66 | 24.8 | 8.7 | 16.1 | 3.1 | 208 | 64 |
| freq_cost_conf | 1.650 ± 0.127 | 220.7 | 1000 | 0.65 | 7.1 | 2.3 | 4.9 | 3.4 | 8 | 25 |
| adaptive_full | 1.658 ± 0.139 | 219.6 | 1000 | 0.65 | 7.2 | 2.4 | 5.0 | 3.4 | 9 | 25 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 435.3 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.515 ± 0.001 | 435.6 | 1000 | 0.12 | 223.6 | 92.6 | 47.5 | 1.0 | 32266 | 161 |
| freq_cost_conf | 0.937 ± 0.001 | 435.3 | 1000 | 0.12 | 11.2 | 5.2 | 4.5 | 1.7 | 36 | 28 |
| adaptive_full | 0.931 ± 0.002 | 435.3 | 1000 | 0.12 | 12.9 | 5.9 | 5.1 | 1.7 | 69 | 34 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
