# Sensitivity stall_fraction=0.25

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 4096, epochs: 40, accesses/epoch: 10000, seeds: [0, 1, 2, 3, 4]
- monitor sample rate: 0.2, stall fraction: 0.25, pinned pages: 1.0%
- tiers: local_ddr5 (512 pages, rd 100 ns, wr 100 ns); cxl_dram (1536 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (4096 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.911 ± 0.265 | 1.949 ± 0.276 | 1.934 ± 0.269 |
| phase | 1.000 ± 0.000 | 1.650 ± 0.143 | 1.701 ± 0.144 | 1.723 ± 0.105 |
| uniform | 1.000 ± 0.000 | 0.675 ± 0.001 | 0.943 ± 0.001 | 0.937 ± 0.001 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 404.3 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.911 ± 0.265 | 185.3 | 1000 | 0.72 | 21.4 | 7.6 | 8.6 | 3.8 | 318 | 78 |
| freq_cost_conf | 1.949 ± 0.276 | 194.2 | 1000 | 0.72 | 6.1 | 2.1 | 2.5 | 3.9 | 12 | 33 |
| adaptive_full | 1.934 ± 0.269 | 195.6 | 1000 | 0.71 | 6.4 | 2.0 | 2.5 | 3.9 | 8 | 35 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 396.0 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.650 ± 0.143 | 211.8 | 1000 | 0.66 | 24.8 | 8.7 | 8.7 | 3.3 | 208 | 64 |
| freq_cost_conf | 1.701 ± 0.144 | 216.8 | 1000 | 0.66 | 10.7 | 3.3 | 3.7 | 3.5 | 16 | 32 |
| adaptive_full | 1.723 ± 0.105 | 213.6 | 1000 | 0.66 | 10.5 | 3.2 | 3.7 | 3.5 | 15 | 33 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 435.3 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.675 ± 0.001 | 435.6 | 1000 | 0.12 | 223.6 | 92.6 | 31.2 | 1.2 | 32266 | 161 |
| freq_cost_conf | 0.943 ± 0.001 | 435.5 | 1000 | 0.12 | 19.9 | 8.3 | 3.9 | 1.7 | 126 | 46 |
| adaptive_full | 0.937 ± 0.001 | 435.3 | 1000 | 0.12 | 23.4 | 9.8 | 4.5 | 1.7 | 214 | 55 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
