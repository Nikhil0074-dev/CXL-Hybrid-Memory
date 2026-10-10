# Sensitivity sample_rate=0.05

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 1024, epochs: 20, accesses/epoch: 4000, seeds: [0, 1]
- monitor sample rate: 0.05, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (128 pages, rd 100 ns, wr 100 ns); cxl_dram (384 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (1024 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.280 ± 0.095 | 1.695 ± 0.134 | 1.694 ± 0.054 |
| phase | 1.000 ± 0.000 | 1.181 ± 1.482 | 1.657 ± 2.385 | 1.706 ± 2.097 |
| uniform | 1.000 ± 0.000 | 0.672 ± 0.014 | 0.962 ± 0.017 | 0.960 ± 0.068 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 417.9 | 1000 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.280 ± 0.095 | 218.6 | 1000 | 0.61 | 13.1 | 3.9 | 32.2 | 0.8 | 615 | 14 |
| freq_cost_conf | 1.695 ± 0.134 | 236.6 | 1000 | 0.61 | 0.9 | 0.3 | 2.9 | 1.1 | 2 | 4 |
| adaptive_full | 1.694 ± 0.054 | 236.8 | 1000 | 0.61 | 0.9 | 0.3 | 2.9 | 1.1 | 1 | 4 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 422.3 | 1000 | 0.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.181 ± 1.482 | 263.0 | 1000 | 0.56 | 11.2 | 3.6 | 25.8 | 0.8 | 552 | 16 |
| freq_cost_conf | 1.657 ± 2.385 | 244.4 | 1000 | 0.57 | 1.0 | 0.3 | 3.3 | 1.1 | 2 | 4 |
| adaptive_full | 1.706 ± 2.097 | 236.6 | 1000 | 0.61 | 1.0 | 0.3 | 3.4 | 1.1 | 2 | 2 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 434.7 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.672 ± 0.014 | 433.5 | 1000 | 0.12 | 25.5 | 8.2 | 32.5 | 0.4 | 2926 | 18 |
| freq_cost_conf | 0.962 ± 0.017 | 434.3 | 1000 | 0.12 | 1.7 | 0.7 | 3.3 | 0.6 | 4 | 2 |
| adaptive_full | 0.960 ± 0.068 | 435.2 | 1000 | 0.12 | 1.7 | 0.7 | 3.3 | 0.6 | 8 | 3 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
