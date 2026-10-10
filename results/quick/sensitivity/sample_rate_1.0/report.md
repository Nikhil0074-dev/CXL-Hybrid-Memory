# Sensitivity sample_rate=1.0

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 1024, epochs: 20, accesses/epoch: 4000, seeds: [0, 1]
- monitor sample rate: 1.0, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (128 pages, rd 100 ns, wr 100 ns); cxl_dram (384 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (1024 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.647 ± 0.050 | 1.644 ± 0.044 | 1.617 ± 0.048 |
| phase | 1.000 ± 0.000 | 1.625 ± 1.759 | 1.625 ± 1.753 | 1.613 ± 1.827 |
| uniform | 1.000 ± 0.000 | 0.698 ± 0.001 | 0.925 ± 0.007 | 0.923 ± 0.009 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 417.9 | 1000 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.647 ± 0.050 | 211.5 | 1000 | 0.64 | 1.3 | 0.4 | 4.3 | 12.3 | 0 | 2 |
| freq_cost_conf | 1.644 ± 0.044 | 212.5 | 1000 | 0.64 | 1.3 | 0.4 | 4.1 | 12.3 | 0 | 2 |
| adaptive_full | 1.617 ± 0.048 | 217.8 | 1000 | 0.62 | 1.2 | 0.3 | 3.6 | 12.1 | 0 | 2 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 422.3 | 1000 | 0.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.625 ± 1.759 | 214.5 | 1000 | 0.65 | 1.7 | 0.5 | 5.4 | 12.0 | 2 | 6 |
| freq_cost_conf | 1.625 ± 1.753 | 214.9 | 1000 | 0.65 | 1.7 | 0.5 | 5.3 | 12.0 | 2 | 6 |
| adaptive_full | 1.613 ± 1.827 | 218.2 | 1000 | 0.63 | 1.5 | 0.5 | 4.8 | 11.9 | 2 | 6 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 434.7 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.698 ± 0.001 | 434.7 | 1000 | 0.12 | 16.2 | 8.1 | 25.2 | 5.0 | 2880 | 16 |
| freq_cost_conf | 0.925 ± 0.007 | 434.4 | 1000 | 0.12 | 0.4 | 0.2 | 0.9 | 6.7 | 0 | 0 |
| adaptive_full | 0.923 ± 0.009 | 434.1 | 1000 | 0.12 | 0.6 | 0.3 | 1.1 | 6.6 | 2 | 0 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
