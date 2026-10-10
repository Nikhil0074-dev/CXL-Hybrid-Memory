# Main comparison

**SIMULATION RESULTS. Not real hardware.** Latencies and bandwidths are assumptions (docs/ASSUMPTIONS.md).
The persistent tier is EMULATED. Speedup = static_firsttouch total time / policy total time, paired per seed;
value is mean ± 95% confidence half-width (Student t). >1 is faster than static first-touch.

- pages: 4096, epochs: 40, accesses/epoch: 10000, seeds: [0, 1, 2, 3, 4]
- monitor sample rate: 0.2, stall fraction: 0.5, pinned pages: 1.0%
- tiers: local_ddr5 (512 pages, rd 100 ns, wr 100 ns); cxl_dram (1536 pages, rd 250 ns, wr 250 ns); cxl_persistent_emulated (4096 pages, rd 500 ns, wr 1000 ns)

## Speedup summary

| workload | static_firsttouch | static_interleave | os_like | freq_only | freq_recency | freq_hysteresis | freq_cost | freq_cost_conf | adaptive_full | oracle_static | oracle_epoch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sequential | 1.000 ± 0.000 | 0.876 ± 0.000 | 0.733 ± 0.001 | 0.433 ± 0.001 | 0.443 ± 0.002 | 0.709 ± 0.000 | 0.666 ± 0.002 | 0.946 ± 0.001 | 0.941 ± 0.001 | 1.017 ± 0.000 | 1.414 ± 0.001 |
| uniform | 1.000 ± 0.000 | 0.860 ± 0.001 | 0.776 ± 0.001 | 0.515 ± 0.001 | 0.522 ± 0.002 | 0.746 ± 0.001 | 0.673 ± 0.001 | 0.937 ± 0.001 | 0.931 ± 0.002 | 1.051 ± 0.001 | 1.420 ± 0.003 |
| hotset | 1.000 ± 0.000 | 0.883 ± 0.020 | 2.377 ± 0.025 | 2.489 ± 0.030 | 2.490 ± 0.042 | 2.509 ± 0.032 | 2.525 ± 0.037 | 2.592 ± 0.031 | 2.532 ± 0.029 | 3.224 ± 0.024 | 3.471 ± 0.024 |
| zipf | 1.000 ± 0.000 | 0.861 ± 0.099 | 1.694 ± 0.228 | 1.759 ± 0.243 | 1.756 ± 0.250 | 1.835 ± 0.255 | 1.794 ± 0.256 | 1.897 ± 0.269 | 1.883 ± 0.263 | 2.491 ± 0.367 | 2.872 ± 0.394 |
| phase | 1.000 ± 0.000 | 0.837 ± 0.028 | 1.474 ± 0.044 | 1.517 ± 0.123 | 1.489 ± 0.142 | 1.569 ± 0.080 | 1.540 ± 0.178 | 1.650 ± 0.127 | 1.658 ± 0.139 | 2.369 ± 0.059 | 3.084 ± 0.092 |
| scan_hot | 1.000 ± 0.000 | 0.885 ± 0.080 | 1.184 ± 0.045 | 0.959 ± 0.037 | 0.964 ± 0.033 | 1.154 ± 0.040 | 1.074 ± 0.039 | 1.359 ± 0.049 | 1.358 ± 0.053 | 1.596 ± 0.076 | 1.986 ± 0.090 |
| write_heavy | 1.000 ± 0.000 | 0.833 ± 0.109 | 1.978 ± 0.229 | 2.075 ± 0.262 | 2.082 ± 0.256 | 2.142 ± 0.268 | 2.080 ± 0.262 | 2.160 ± 0.258 | 2.147 ± 0.265 | 3.005 ± 0.359 | 3.800 ± 0.402 |

## Where each policy wins or loses (vs static_firsttouch, mean speedup)

- **static_interleave**: faster on 0/7 workloads (none); slower on 7 (sequential, uniform, hotset, zipf, phase, scan_hot, write_heavy).
- **os_like**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_only**: faster on 4/7 workloads (hotset, zipf, phase, write_heavy); slower on 3 (sequential, uniform, scan_hot).
- **freq_recency**: faster on 4/7 workloads (hotset, zipf, phase, write_heavy); slower on 3 (sequential, uniform, scan_hot).
- **freq_hysteresis**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_cost**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **freq_cost_conf**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **adaptive_full**: faster on 5/7 workloads (hotset, zipf, phase, scan_hot, write_heavy); slower on 2 (sequential, uniform).
- **oracle_static**: faster on 6/7 workloads (uniform, hotset, zipf, phase, scan_hot, write_heavy); slower on 0 (none).
- **oracle_epoch**: faster on 7/7 workloads (sequential, uniform, hotset, zipf, phase, scan_hot, write_heavy); slower on 0 (none).

## Workload: sequential

Sliding sequential sweep, 4 touches/page, 10% writes. No stable hot set: migration should not help.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 384.6 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.876 ± 0.000 | 438.8 | 1000 | 0.08 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 0.733 ± 0.001 | 394.9 | 1000 | 0.11 | 75.4 | 22.9 | 23.2 | 1.5 | 5828 | 99 |
| freq_only | 0.433 ± 0.001 | 409.4 | 1000 | 0.09 | 261.7 | 109.4 | 53.0 | 0.9 | 37729 | 156 |
| freq_recency | 0.443 ± 0.002 | 408.6 | 1000 | 0.09 | 251.7 | 104.1 | 52.0 | 0.9 | 36045 | 156 |
| freq_hysteresis | 0.709 ± 0.000 | 392.7 | 1000 | 0.12 | 76.8 | 34.1 | 26.1 | 1.5 | 5511 | 122 |
| freq_cost | 0.666 ± 0.002 | 395.3 | 1000 | 0.10 | 99.2 | 38.4 | 30.1 | 1.4 | 7491 | 119 |
| freq_cost_conf | 0.946 ± 0.001 | 385.8 | 1000 | 0.12 | 6.9 | 3.2 | 3.2 | 2.0 | 12 | 17 |
| adaptive_full | 0.941 ± 0.001 | 386.0 | 1000 | 0.12 | 7.8 | 3.5 | 3.5 | 2.0 | 15 | 20 |
| oracle_static | 1.017 ± 0.000 | 378.0 | 1000 | 0.13 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 1.414 ± 0.001 | 272.0 | 500 | 0.20 | 469.1 | 217.4 | 0.0 | 0.0 | 0 | 0 |

## Workload: uniform

Uniform random, 30% writes. No locality at all: migration should not help (negative-control).

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 435.3 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.860 ± 0.001 | 506.0 | 1000 | 0.08 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 0.776 ± 0.001 | 435.7 | 1000 | 0.12 | 75.6 | 19.6 | 20.8 | 1.4 | 6209 | 99 |
| freq_only | 0.515 ± 0.001 | 435.6 | 1000 | 0.12 | 223.6 | 92.6 | 47.5 | 1.0 | 32266 | 161 |
| freq_recency | 0.522 ± 0.002 | 435.2 | 1000 | 0.12 | 218.4 | 89.8 | 46.9 | 1.0 | 31003 | 153 |
| freq_hysteresis | 0.746 ± 0.001 | 435.4 | 1000 | 0.12 | 76.5 | 33.4 | 24.0 | 1.4 | 5505 | 124 |
| freq_cost | 0.673 ± 0.001 | 435.4 | 1000 | 0.12 | 114.5 | 46.0 | 31.4 | 1.2 | 10507 | 131 |
| freq_cost_conf | 0.937 ± 0.001 | 435.3 | 1000 | 0.12 | 11.2 | 5.2 | 4.5 | 1.7 | 36 | 28 |
| adaptive_full | 0.931 ± 0.002 | 435.3 | 1000 | 0.12 | 12.9 | 5.9 | 5.1 | 1.7 | 69 | 34 |
| oracle_static | 1.051 ± 0.001 | 414.3 | 1000 | 0.14 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 1.420 ± 0.003 | 306.5 | 1000 | 0.25 | 360.1 | 151.2 | 0.0 | 0.0 | 0 | 0 |

## Workload: hotset

10% of pages receive 90% of accesses, stable over time, 20% writes. Best case for promotion.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 417.0 | 1000 | 0.12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.883 ± 0.020 | 472.1 | 1000 | 0.09 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 2.377 ± 0.025 | 156.4 | 1000 | 0.84 | 7.4 | 1.7 | 6.3 | 4.6 | 8 | 40 |
| freq_only | 2.489 ± 0.030 | 147.2 | 1000 | 0.87 | 6.9 | 2.8 | 7.3 | 4.8 | 11 | 37 |
| freq_recency | 2.490 ± 0.042 | 147.3 | 1000 | 0.87 | 6.8 | 2.7 | 7.2 | 4.8 | 14 | 39 |
| freq_hysteresis | 2.509 ± 0.032 | 149.0 | 1000 | 0.86 | 5.3 | 2.0 | 5.5 | 4.8 | 4 | 32 |
| freq_cost | 2.525 ± 0.037 | 146.8 | 1000 | 0.87 | 5.9 | 2.3 | 6.2 | 4.9 | 9 | 36 |
| freq_cost_conf | 2.592 ± 0.031 | 148.2 | 1000 | 0.86 | 2.8 | 0.9 | 2.8 | 5.0 | 0 | 24 |
| adaptive_full | 2.532 ± 0.029 | 152.1 | 1000 | 0.85 | 2.8 | 0.8 | 2.7 | 4.9 | 0 | 24 |
| oracle_static | 3.224 ± 0.024 | 129.3 | 500 | 0.90 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 3.471 ± 0.024 | 120.1 | 500 | 0.90 | 177.7 | 79.0 | 0.0 | 0.0 | 0 | 0 |

## Workload: zipf

Zipf(s=1.0) popularity, stable, 20% writes. Skewed but with a long warm tail.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 404.3 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.861 ± 0.099 | 469.2 | 1000 | 0.08 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 1.694 ± 0.228 | 194.8 | 1000 | 0.69 | 25.5 | 4.3 | 15.0 | 3.4 | 1736 | 62 |
| freq_only | 1.759 ± 0.243 | 185.3 | 1000 | 0.72 | 21.4 | 7.6 | 15.8 | 3.5 | 318 | 78 |
| freq_recency | 1.756 ± 0.250 | 185.6 | 1000 | 0.72 | 21.4 | 7.7 | 15.9 | 3.5 | 339 | 79 |
| freq_hysteresis | 1.835 ± 0.255 | 187.5 | 1000 | 0.71 | 14.1 | 5.5 | 11.2 | 3.7 | 64 | 59 |
| freq_cost | 1.794 ± 0.256 | 185.7 | 1000 | 0.72 | 18.8 | 6.4 | 14.0 | 3.6 | 282 | 70 |
| freq_cost_conf | 1.897 ± 0.269 | 198.8 | 1000 | 0.71 | 3.7 | 1.3 | 2.9 | 3.8 | 4 | 25 |
| adaptive_full | 1.883 ± 0.263 | 200.3 | 1000 | 0.71 | 3.8 | 1.3 | 3.0 | 3.8 | 2 | 23 |
| oracle_static | 2.491 ± 0.367 | 162.4 | 1000 | 0.76 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 2.872 ± 0.394 | 140.7 | 500 | 0.77 | 279.7 | 119.0 | 0.0 | 0.0 | 0 | 0 |

## Workload: phase

Zipf(s=1.1) whose hot set moves to new pages every 10 epochs. Tests adaptation speed and thrashing.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 396.0 | 1000 | 0.15 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.837 ± 0.028 | 473.0 | 1000 | 0.08 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 1.474 ± 0.044 | 223.1 | 1000 | 0.62 | 25.3 | 5.6 | 14.0 | 3.0 | 433 | 57 |
| freq_only | 1.517 ± 0.123 | 211.8 | 1000 | 0.66 | 24.8 | 8.7 | 16.1 | 3.1 | 208 | 64 |
| freq_recency | 1.489 ± 0.142 | 217.1 | 1000 | 0.66 | 24.6 | 8.7 | 15.7 | 3.0 | 208 | 71 |
| freq_hysteresis | 1.569 ± 0.080 | 211.9 | 1000 | 0.65 | 19.2 | 7.0 | 13.0 | 3.2 | 90 | 56 |
| freq_cost | 1.540 ± 0.178 | 212.5 | 1000 | 0.67 | 22.7 | 7.8 | 14.9 | 3.1 | 164 | 61 |
| freq_cost_conf | 1.650 ± 0.127 | 220.7 | 1000 | 0.65 | 7.1 | 2.3 | 4.9 | 3.4 | 8 | 25 |
| adaptive_full | 1.658 ± 0.139 | 219.6 | 1000 | 0.65 | 7.2 | 2.4 | 5.0 | 3.4 | 9 | 25 |
| oracle_static | 2.369 ± 0.059 | 167.1 | 1000 | 0.74 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 3.084 ± 0.092 | 128.4 | 450 | 0.84 | 243.1 | 100.5 | 0.0 | 0.0 | 0 | 0 |

## Workload: scan_hot

Stable Zipf hot set (60%) plus a sequential scan (40%). Tests scan pollution of the fast tier.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 405.3 | 1000 | 0.14 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.885 ± 0.080 | 459.1 | 1000 | 0.08 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 1.184 ± 0.045 | 280.1 | 1000 | 0.45 | 37.3 | 7.5 | 15.8 | 2.4 | 2573 | 64 |
| freq_only | 0.959 ± 0.037 | 280.7 | 1000 | 0.46 | 75.0 | 30.4 | 31.6 | 1.9 | 5998 | 121 |
| freq_recency | 0.964 ± 0.033 | 281.2 | 1000 | 0.46 | 73.3 | 29.9 | 31.2 | 1.9 | 5664 | 118 |
| freq_hysteresis | 1.154 ± 0.040 | 278.6 | 1000 | 0.46 | 34.8 | 15.6 | 18.4 | 2.3 | 844 | 87 |
| freq_cost | 1.074 ± 0.039 | 281.2 | 1000 | 0.46 | 50.7 | 19.2 | 23.4 | 2.1 | 2241 | 95 |
| freq_cost_conf | 1.359 ± 0.049 | 282.8 | 1000 | 0.46 | 4.1 | 1.6 | 2.4 | 2.7 | 6 | 15 |
| adaptive_full | 1.358 ± 0.053 | 283.0 | 1000 | 0.46 | 4.3 | 1.6 | 2.5 | 2.7 | 3 | 17 |
| oracle_static | 1.596 ± 0.076 | 253.9 | 1000 | 0.51 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 1.986 ± 0.090 | 204.0 | 500 | 0.53 | 457.2 | 215.2 | 0.0 | 0.0 | 0 | 0 |

## Workload: write_heavy

Zipf(s=1.0) with 70% writes. Tests the cost of writes on the persistent tier.

| policy | speedup | avg latency ns | p99 ns | DDR5 access share | migrated MB | persistent writes MB | migration % of time | monitor % of time | ping-pong | failed ops |
|---|---|---|---|---|---|---|---|---|---|---|
| static_firsttouch | 1.000 ± 0.000 | 545.9 | 1000 | 0.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| static_interleave | 0.833 ± 0.109 | 657.5 | 1000 | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| os_like | 1.978 ± 0.229 | 232.0 | 1000 | 0.69 | 25.6 | 4.4 | 13.0 | 2.9 | 1746 | 61 |
| freq_only | 2.075 ± 0.262 | 219.1 | 1000 | 0.72 | 21.2 | 7.5 | 13.7 | 3.1 | 310 | 73 |
| freq_recency | 2.082 ± 0.256 | 218.2 | 1000 | 0.72 | 21.2 | 7.5 | 13.8 | 3.1 | 321 | 71 |
| freq_hysteresis | 2.142 ± 0.268 | 222.0 | 1000 | 0.70 | 14.2 | 5.5 | 9.8 | 3.2 | 59 | 55 |
| freq_cost | 2.080 ± 0.262 | 218.7 | 1000 | 0.72 | 21.2 | 7.5 | 13.7 | 3.1 | 337 | 74 |
| freq_cost_conf | 2.160 ± 0.258 | 236.5 | 1000 | 0.71 | 4.7 | 1.8 | 3.2 | 3.2 | 6 | 26 |
| adaptive_full | 2.147 ± 0.265 | 237.6 | 1000 | 0.70 | 5.1 | 1.8 | 3.4 | 3.2 | 4 | 22 |
| oracle_static | 3.005 ± 0.359 | 181.7 | 1000 | 0.76 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| oracle_epoch | 3.800 ± 0.402 | 143.6 | 600 | 0.77 | 281.0 | 119.9 | 0.0 | 0.0 | 0 | 0 |

## Limits of these results

- Simulation with assumed costs; relative ordering may change on real hardware.
- No CPU caches, no memory-level parallelism, no bandwidth contention, synthetic traces only.
- `oracle_*` rows are clairvoyant bounds, not achievable policies. `os_like` is an approximation, not the Linux kernel.
- p99 is over per-access latency values (tier/read/write), excluding migration stalls.
