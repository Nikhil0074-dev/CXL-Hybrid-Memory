# Sensitivity sample_rate=0.05

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 4096, epochs: 40, accesses/epoch: 10000, seeds: [0, 1, 2, 3, 4]
- monitor sample rate: 0.05, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (512 pages, rd 100 ns, wr 100 ns); cxl_dram (1536 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (4096 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_cost_conf | adaptive_full |
|---|---|---|---|---|
| zipf | 1.000 ± 0.000 | 1.323 ± 0.191 | 1.794 ± 0.248 | 1.798 ± 0.251 |
| phase | 1.000 ± 0.000 | 1.321 ± 0.110 | 1.556 ± 0.121 | 1.579 ± 0.083 |
| uniform | 1.000 ± 0.000 | 0.572 ± 0.002 | 0.969 ± 0.001 | 0.968 ± 0.002 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **freq_cost_conf**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).
- **adaptive_full**: faster on 2/3 workloads (zipf, phase); slower on 1 (uniform).

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 404.3 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.323 ± 0.191 | 201.0 | 1000 | 0.67 | 63.0 | 18.6 | 33.1 | 1.2 | 2565 | 96 |
| freq_cost_conf | 1.794 ± 0.248 | 217.1 | 1000 | 0.66 | 2.8 | 0.9 | 2.0 | 1.6 | 2 | 13 |
| adaptive_full | 1.798 ± 0.251 | 216.7 | 1000 | 0.66 | 2.7 | 0.9 | 2.0 | 1.6 | 2 | 15 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 396.0 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.321 ± 0.110 | 227.2 | 1000 | 0.62 | 42.7 | 13.4 | 23.3 | 1.2 | 2456 | 73 |
| freq_cost_conf | 1.556 ± 0.121 | 244.0 | 1000 | 0.59 | 4.7 | 1.5 | 3.0 | 1.4 | 7 | 17 |
| adaptive_full | 1.579 ± 0.083 | 239.8 | 1000 | 0.59 | 4.6 | 1.5 | 3.1 | 1.4 | 6 | 15 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 435.3 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.572 ± 0.002 | 435.7 | 1000 | 0.12 | 187.6 | 68.1 | 42.3 | 0.5 | 10044 | 146 |
| freq_cost_conf | 0.969 ± 0.001 | 435.3 | 1000 | 0.12 | 5.9 | 2.3 | 2.3 | 0.8 | 17 | 17 |
| adaptive_full | 0.968 ± 0.002 | 435.4 | 1000 | 0.12 | 6.1 | 2.4 | 2.4 | 0.8 | 16 | 16 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
