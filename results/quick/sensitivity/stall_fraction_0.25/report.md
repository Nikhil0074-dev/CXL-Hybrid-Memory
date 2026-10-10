# Sensitivity stall_fraction=0.25

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 1024, epochs: 20, accesses/epoch: 4000, seeds: [0, 1]
- monitor sample rate: 0.2, stall fraction: 0.25, pinned pages: 1.0%
- tiers: local_ddr5 (128 pages, rd 100 ns, wr 100 ns); cxl_dram (384 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (1024 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.837 ± 0.135 | 1.848 ± 0.081 | 1.824 ± 0.053 |
| phase | 1.000 ± 0.000 | 1.841 ± 1.926 | 1.709 ± 3.692 | 1.776 ± 2.543 |
| uniform | 1.000 ± 0.000 | 0.803 ± 0.119 | 0.952 ± 0.014 | 0.947 ± 0.030 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 417.9 | 1000 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.837 ± 0.135 | 206.0 | 1000 | 0.66 | 3.3 | 1.2 | 6.3 | 3.2 | 30 | 8 |
| freq_cost_conf | 1.848 ± 0.081 | 210.8 | 1000 | 0.65 | 1.9 | 0.6 | 3.5 | 3.2 | 4 | 5 |
| adaptive_full | 1.824 ± 0.053 | 213.6 | 1000 | 0.63 | 2.0 | 0.7 | 3.6 | 3.2 | 3 | 6 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 422.3 | 1000 | 0.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.841 ± 1.926 | 208.4 | 1000 | 0.66 | 3.2 | 1.2 | 6.0 | 3.2 | 26 | 10 |
| freq_cost_conf | 1.709 ± 3.692 | 233.9 | 1000 | 0.62 | 2.3 | 0.8 | 3.9 | 2.9 | 8 | 8 |
| adaptive_full | 1.776 ± 2.543 | 222.3 | 1000 | 0.61 | 2.2 | 0.7 | 3.8 | 3.0 | 6 | 6 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 434.7 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.803 ± 0.119 | 434.6 | 1000 | 0.12 | 21.8 | 9.3 | 18.3 | 1.3 | 3059 | 18 |
| freq_cost_conf | 0.952 ± 0.014 | 434.5 | 1000 | 0.12 | 3.3 | 1.4 | 3.2 | 1.6 | 38 | 5 |
| adaptive_full | 0.947 ± 0.030 | 434.4 | 1000 | 0.12 | 3.8 | 1.6 | 3.7 | 1.6 | 64 | 5 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
