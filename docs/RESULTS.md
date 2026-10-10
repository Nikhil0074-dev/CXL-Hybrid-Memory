# Results (simulation, 5 seeds, 4096 pages, 40 epochs; produced by `cxltier suite`)

Source files: `results/full/main`, `results/full/ablation`, `results/full/sensitivity/*`.
Speedup = static_firsttouch time / policy time, paired per seed, mean ± 95% CI. These are simulated results under assumed costs.

## Main findings
- **Skewed workloads: dynamic placement roughly doubles speed.** hotset 2.4-2.6x, write_heavy 2.0-2.2x, zipf 1.7-1.9x, phase 1.5-1.65x.
- **Workloads with no locality: every dynamic policy loses.** Best case 0.93-0.95x (sequential, uniform). Cause: monitoring cost plus moves driven by noise.
- **freq_only (naive) is dangerous.** It runs at 0.43x on sequential and 0.52x on uniform because it chases noise and thrashes.
- **The os_like approximation is close on skewed workloads** (hotset 2.38x vs 2.59x best). The gain over a kernel-style policy is modest (about 9-12% on hotset/zipf/write_heavy), bigger on scan_hot (1.36x vs 1.18x) and uniform/sequential (0.94x vs 0.78x/0.73x).
- **Big gap to the clairvoyant bound.** oracle_static reaches 3.22x on hotset. Learning time and monitoring cost keep real policies well below it.

## Ablation (what each mechanism is worth)
| Mechanism added | Evidence |
|---|---|
| Recency | No measurable gain. freq_recency ~ freq_only on every workload. **Not worth its complexity here.** |
| Hysteresis + cooldown + budget | Large gain where thrashing hurts: uniform 0.52 -> 0.75, sequential 0.43 -> 0.71, scan_hot 0.96 -> 1.15. |
| Cost model (benefit > cost) | Moderate gain on no-locality workloads (0.52 -> 0.67) but still thrashes. |
| **Confidence bounds on rates** (`freq_cost_conf`) | **Best single addition.** uniform 0.52 -> 0.94, sequential 0.43 -> 0.95, scan_hot 0.96 -> 1.36, and best or tied on every skewed workload. |
| Feedback controller (`adaptive_full`) | **No clear gain over freq_cost_conf.** Equal within error everywhere (phase 1.658 vs 1.650; hotset 2.53 vs 2.59). |

## Honest conclusions
- The useful contribution is the **noise-aware cost model** (promote only if the lower confidence bound of the access rate pays back the migration cost). It is cheap and explains most of the protection against thrashing.
- The adaptive feedback controller is **not justified** by these results. Treat it as a hypothesis for harsher workloads, not a win.
- With a clean monitor (sample rate 100%), confidence bounds are slightly conservative (zipf 1.725 vs 1.752 for freq_only). They help when sampling is sparse: at 5% sampling freq_only falls to 1.32x on zipf while confidence-bound policies hold 1.79x.
- Results get worse for everything when migration stalls the app fully (stall 100%): freq_only on uniform drops to 0.35x, confidence policies stay about 0.95x.

## Threats to validity
- Synthetic traces, assumed latencies, no caches or parallelism, random-order baseline (see ASSUMPTIONS.md).
- Wide confidence intervals on zipf/write_heavy (about ±0.25) come from different random allocations per seed. Conclusions about ordering between close policies (e.g., 1.90 vs 1.88) are not reliable.
- Thresholds (hot 2.0x, warm 1.0x, horizon 8 epochs, z=1.5) were chosen by hand and not tuned on held-out workloads. The phase workload length (10 epochs) matches the horizon, which favors the cost model.
- Nothing here has been checked against real CXL hardware.
