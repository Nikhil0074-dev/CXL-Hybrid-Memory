# Sensitivity stall_fraction=1.0

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 1024, epochs: 20, accesses/epoch: 4000, seeds: [0, 1]
- monitor sample rate: 0.2, stall fraction: 1.0, pinned pages: 1.0%
- tiers: local_ddr5 (128 pages, rd 100 ns, wr 100 ns); cxl_dram (384 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (1024 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.545 ± 0.238 | 1.711 ± 0.059 | 1.687 ± 0.004 |
| phase | 1.000 ± 0.000 | 1.561 ± 1.575 | 1.673 ± 2.179 | 1.660 ± 2.375 |
| uniform | 1.000 ± 0.000 | 0.519 ± 0.185 | 0.944 ± 0.028 | 0.945 ± 0.007 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 417.9 | 1000 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.545 ± 0.238 | 206.0 | 1000 | 0.66 | 3.3 | 1.2 | 21.2 | 2.7 | 30 | 8 |
| freq_cost_conf | 1.711 ± 0.059 | 224.8 | 1000 | 0.64 | 0.7 | 0.2 | 4.9 | 3.0 | 0 | 3 |
| adaptive_full | 1.687 ± 0.004 | 227.5 | 1000 | 0.63 | 0.8 | 0.2 | 5.2 | 2.9 | 0 | 2 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 422.3 | 1000 | 0.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.561 ± 1.575 | 208.4 | 1000 | 0.66 | 3.2 | 1.2 | 20.3 | 2.7 | 26 | 10 |
| freq_cost_conf | 1.673 ± 2.179 | 228.6 | 1000 | 0.60 | 1.0 | 0.4 | 6.7 | 2.9 | 1 | 4 |
| adaptive_full | 1.660 ± 2.375 | 231.8 | 1000 | 0.62 | 1.0 | 0.3 | 6.3 | 2.8 | 2 | 4 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 434.7 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.519 ± 0.185 | 434.6 | 1000 | 0.12 | 21.8 | 9.3 | 47.3 | 0.9 | 3059 | 18 |
| freq_cost_conf | 0.944 ± 0.028 | 435.0 | 1000 | 0.12 | 0.9 | 0.5 | 3.9 | 1.6 | 3 | 2 |
| adaptive_full | 0.945 ± 0.007 | 434.6 | 1000 | 0.12 | 0.9 | 0.5 | 3.9 | 1.6 | 5 | 0 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
