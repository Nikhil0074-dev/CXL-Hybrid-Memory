# Ablation study

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 1024, epochs: 20, accesses/epoch: 4000, seeds: [0, 1]
- monitor sample rate: 0.2, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (128 pages, rd 100 ns, wr 100 ns); cxl_dram (384 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (1024 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | freq_only | freq_recency | freq_hysteresis | freq_cost | freq_cost_conf | adaptive_full |
|---|---|---|---|---|---|---|---|
| sequential | 1.000 ± 0.000 | 0.658 ± 0.111 | 0.660 ± 0.118 | 0.814 ± 0.022 | 0.772 ± 0.042 | 0.952 ± 0.021 | 0.949 ± 0.015 |
| uniform | 1.000 ± 0.000 | 0.679 ± 0.162 | 0.685 ± 0.078 | 0.828 ± 0.007 | 0.757 ± 0.035 | 0.940 ± 0.008 | 0.931 ± 0.006 |
| hotset | 1.000 ± 0.000 | 2.324 ± 1.196 | 2.361 ± 0.725 | 2.330 ± 0.936 | 2.337 ± 0.949 | 2.390 ± 0.872 | 2.335 ± 1.157 |
| zipf | 1.000 ± 0.000 | 1.728 ± 0.179 | 1.736 ± 0.045 | 1.754 ± 0.111 | 1.735 ± 0.026 | 1.778 ± 0.025 | 1.759 ± 0.033 |
| phase | 1.000 ± 0.000 | 1.737 ± 1.793 | 1.708 ± 2.591 | 1.744 ± 1.722 | 1.708 ± 2.049 | 1.746 ± 2.423 | 1.718 ± 2.413 |
| scan_hot | 1.000 ± 0.000 | 1.059 ± 0.407 | 1.064 ± 0.424 | 1.204 ± 0.450 | 1.092 ± 0.485 | 1.270 ± 0.470 | 1.260 ± 0.537 |
| write_heavy | 1.000 ± 0.000 | 1.654 ± 0.722 | 1.652 ± 0.702 | 1.648 ± 0.790 | 1.655 ± 0.860 | 1.681 ± 0.669 | 1.661 ± 0.750 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **freq_only**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_recency**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_hysteresis**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_cost**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_cost_conf**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **adaptive_full**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).

## Workload: sequential

Sliding sequential sweep, 4 touches/page, 10% writes. No stable hot set: migration should not help.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 384.4 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.658 ± 0.111 | 384.7 | 1000 | 0.12 | 20.8 | 9.3 | 32.9 | 1.2 | 3098 | 18 |
| freq_recency | 0.660 ± 0.118 | 384.7 | 1000 | 0.12 | 20.6 | 9.2 | 32.7 | 1.2 | 3044 | 20 |
| freq_hysteresis | 0.814 ± 0.022 | 384.5 | 1000 | 0.12 | 8.4 | 4.1 | 17.1 | 1.5 | 785 | 12 |
| freq_cost | 0.772 ± 0.042 | 384.6 | 1000 | 0.12 | 11.9 | 4.8 | 21.3 | 1.5 | 992 | 14 |
| freq_cost_conf | 0.952 ± 0.021 | 384.7 | 1000 | 0.12 | 1.3 | 0.6 | 2.9 | 1.8 | 6 | 4 |
| adaptive_full | 0.949 ± 0.015 | 384.4 | 1000 | 0.12 | 1.4 | 0.6 | 3.3 | 1.8 | 5 | 4 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 434.7 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 0.679 ± 0.162 | 434.6 | 1000 | 0.12 | 21.8 | 9.3 | 31.0 | 1.1 | 3059 | 18 |
| freq_recency | 0.685 ± 0.078 | 434.4 | 1000 | 0.12 | 21.2 | 9.1 | 30.4 | 1.2 | 2914 | 19 |
| freq_hysteresis | 0.828 ± 0.007 | 434.5 | 1000 | 0.12 | 8.7 | 4.2 | 15.8 | 1.4 | 741 | 14 |
| freq_cost | 0.757 ± 0.035 | 434.6 | 1000 | 0.12 | 15.0 | 5.9 | 23.1 | 1.3 | 1456 | 16 |
| freq_cost_conf | 0.940 ± 0.008 | 434.7 | 1000 | 0.12 | 2.2 | 1.0 | 4.4 | 1.6 | 12 | 5 |
| adaptive_full | 0.931 ± 0.006 | 435.0 | 1000 | 0.12 | 2.7 | 1.2 | 5.3 | 1.6 | 26 | 4 |

## Workload: hotset

10% of pages receive 90% of accesses, stable over time, 20% writes. Best case for promotion.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 395.0 | 1000 | 0.14 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 2.324 ± 1.196 | 154.0 | 1000 | 0.84 | 1.0 | 0.4 | 5.1 | 4.3 | 0 | 5 |
| freq_recency | 2.361 ± 0.725 | 151.5 | 1000 | 0.85 | 1.0 | 0.3 | 5.1 | 4.4 | 0 | 3 |
| freq_hysteresis | 2.330 ± 0.936 | 156.0 | 1000 | 0.83 | 0.8 | 0.2 | 3.7 | 4.3 | 0 | 4 |
| freq_cost | 2.337 ± 0.949 | 152.9 | 1000 | 0.85 | 1.1 | 0.4 | 5.2 | 4.3 | 0 | 4 |
| freq_cost_conf | 2.390 ± 0.872 | 152.6 | 1000 | 0.85 | 0.7 | 0.2 | 3.3 | 4.4 | 0 | 4 |
| adaptive_full | 2.335 ± 1.157 | 156.1 | 1000 | 0.83 | 0.8 | 0.2 | 3.5 | 4.3 | 0 | 4 |

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 417.9 | 1000 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.728 ± 0.179 | 206.0 | 1000 | 0.66 | 3.3 | 1.2 | 11.8 | 3.0 | 30 | 8 |
| freq_recency | 1.736 ± 0.045 | 205.1 | 1000 | 0.65 | 3.3 | 1.2 | 11.8 | 3.0 | 36 | 10 |
| freq_hysteresis | 1.754 ± 0.111 | 215.2 | 1000 | 0.62 | 1.9 | 0.7 | 6.6 | 3.1 | 2 | 4 |
| freq_cost | 1.735 ± 0.026 | 205.6 | 1000 | 0.66 | 3.2 | 1.2 | 11.6 | 3.0 | 38 | 10 |
| freq_cost_conf | 1.778 ± 0.025 | 217.1 | 1000 | 0.65 | 1.3 | 0.4 | 4.5 | 3.1 | 1 | 4 |
| adaptive_full | 1.759 ± 0.033 | 219.1 | 1000 | 0.63 | 1.4 | 0.4 | 4.7 | 3.1 | 0 | 5 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 422.3 | 1000 | 0.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.737 ± 1.793 | 208.4 | 1000 | 0.66 | 3.2 | 1.2 | 11.3 | 3.0 | 26 | 10 |
| freq_recency | 1.708 ± 2.591 | 212.4 | 1000 | 0.61 | 3.3 | 1.2 | 11.5 | 3.0 | 23 | 12 |
| freq_hysteresis | 1.744 ± 1.722 | 216.6 | 1000 | 0.63 | 2.2 | 0.7 | 7.5 | 3.0 | 5 | 8 |
| freq_cost | 1.708 ± 2.049 | 210.6 | 1000 | 0.66 | 3.4 | 1.3 | 11.9 | 3.0 | 32 | 10 |
| freq_cost_conf | 1.746 ± 2.423 | 222.2 | 1000 | 0.61 | 1.6 | 0.5 | 5.4 | 3.0 | 2 | 6 |
| adaptive_full | 1.718 ± 2.413 | 225.6 | 1000 | 0.63 | 1.7 | 0.5 | 5.5 | 2.9 | 2 | 5 |

## Workload: scan_hot

Stable Zipf hot set (60%) plus a sequential scan (40%). Tests scan pollution of the fast tier.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 391.8 | 1000 | 0.11 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.059 ± 0.407 | 286.0 | 1000 | 0.43 | 8.4 | 3.6 | 20.7 | 2.0 | 604 | 13 |
| freq_recency | 1.064 ± 0.424 | 286.4 | 1000 | 0.43 | 8.1 | 3.6 | 20.3 | 2.0 | 567 | 14 |
| freq_hysteresis | 1.204 ± 0.450 | 289.2 | 1000 | 0.41 | 3.2 | 1.3 | 8.8 | 2.2 | 47 | 10 |
| freq_cost | 1.092 ± 0.485 | 286.1 | 1000 | 0.43 | 7.2 | 3.1 | 18.2 | 2.0 | 399 | 14 |
| freq_cost_conf | 1.270 ± 0.470 | 289.6 | 1000 | 0.42 | 1.4 | 0.5 | 3.8 | 2.4 | 1 | 5 |
| adaptive_full | 1.260 ± 0.537 | 291.2 | 1000 | 0.41 | 1.5 | 0.5 | 4.0 | 2.3 | 1 | 5 |

## Workload: write_heavy

Zipf(s=1.0) with 70% writes. Tests the cost of writes on the persistent tier.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 457.8 | 1000 | 0.16 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| freq_only | 1.654 ± 0.722 | 241.8 | 1000 | 0.65 | 3.2 | 1.2 | 10.0 | 2.6 | 34 | 10 |
| freq_recency | 1.652 ± 0.702 | 242.3 | 1000 | 0.65 | 3.2 | 1.2 | 10.0 | 2.6 | 30 | 8 |
| freq_hysteresis | 1.648 ± 0.790 | 255.5 | 1000 | 0.62 | 1.8 | 0.6 | 5.4 | 2.6 | 4 | 6 |
| freq_cost | 1.655 ± 0.860 | 241.1 | 1000 | 0.65 | 3.3 | 1.2 | 10.2 | 2.6 | 32 | 8 |
| freq_cost_conf | 1.681 ± 0.669 | 249.9 | 1000 | 0.64 | 1.8 | 0.6 | 5.6 | 2.7 | 3 | 4 |
| adaptive_full | 1.661 ± 0.750 | 253.3 | 1000 | 0.62 | 1.8 | 0.6 | 5.5 | 2.6 | 2 | 4 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
