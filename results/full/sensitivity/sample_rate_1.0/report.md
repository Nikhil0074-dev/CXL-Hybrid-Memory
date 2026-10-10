# Sensitivity sample_rate=1.0

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 4096, epochs: 40, accesses/epoch: 10000, seeds: [0, 1, 2, 3, 4]
- monitor sample rate: 1.0, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (512 pages, rd 100 ns, wr 100 ns); cxl_dram (1536 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (4096 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.752 ± 0.248 | 1.725 ± 0.245 | 1.711 ± 0.242 |
| phase | 1.000 ± 0.000 | 1.560 ± 0.066 | 1.577 ± 0.042 | 1.556 ± 0.062 |
| uniform | 1.000 ± 0.000 | 0.569 ± 0.002 | 0.919 ± 0.001 | 0.917 ± 0.001 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 404.3 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.752 ± 0.248 | 188.7 | 1000 | 0.71 | 6.0 | 1.9 | 4.3 | 13.9 | 1 | 36 |
| freq_cost_conf | 1.725 ± 0.245 | 195.6 | 1000 | 0.71 | 4.2 | 1.2 | 2.8 | 13.7 | 0 | 27 |
| adaptive_full | 1.711 ± 0.242 | 197.7 | 1000 | 0.70 | 4.2 | 1.2 | 2.8 | 13.6 | 0 | 24 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 396.0 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.560 ± 0.066 | 200.1 | 1000 | 0.69 | 13.3 | 4.2 | 8.6 | 12.6 | 14 | 39 |
| freq_cost_conf | 1.577 ± 0.042 | 203.9 | 1000 | 0.69 | 9.6 | 2.7 | 6.0 | 12.8 | 4 | 29 |
| adaptive_full | 1.556 ± 0.062 | 207.3 | 1000 | 0.67 | 9.5 | 2.7 | 5.9 | 12.6 | 6 | 26 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 435.3 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.569 ± 0.002 | 435.5 | 1000 | 0.12 | 154.7 | 76.1 | 38.9 | 4.2 | 29835 | 129 |
| freq_cost_conf | 0.919 ± 0.001 | 435.3 | 1000 | 0.12 | 3.2 | 1.6 | 1.3 | 6.8 | 2 | 8 |
| adaptive_full | 0.917 ± 0.001 | 435.2 | 1000 | 0.12 | 3.8 | 1.9 | 1.5 | 6.8 | 6 | 8 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
