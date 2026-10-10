# CXL Hybrid Memory: Access-Frequency-Based Page Migration Across DDR5, CXL DRAM, and Persistent Memory

## 1. Project Overview

The **CXL Hybrid Memory Simulator** is a trace-driven simulation framework designed to evaluate intelligent memory page placement and migration across three memory tiers:

- **Local DDR5 Memory:** Provides low-latency access for frequently accessed pages.
- **CXL-Attached DRAM:** Provides additional memory capacity with different access costs.
- **Persistent CXL Memory Tier:** Emulates a high-capacity persistent memory tier with different latency and performance characteristics.

The primary objective is to investigate whether intelligent, access-frequency-based page placement performs better than conventional memory placement strategies and to identify the workloads and conditions under which it may reduce performance.

The project implements a collection of memory placement policies, a configurable cost model, a migration planner, a trace-driven simulator, and automated experiment reporting.

## 2. Project Scope and Limitations

### What the project includes

- A trace-driven simulator for evaluating hybrid memory systems.
- Multiple page placement and migration policies, including baseline, adaptive, ablation, and oracle strategies.
- Access-frequency and recency estimation using an exponentially weighted moving average (EWMA).
- A cost-aware planner for page promotion and demotion.
- Migration failure handling, migration overhead modelling, and page-movement tracking.
- A write-ahead journal and simulated crash-recovery mechanism.
- Automated experiments, performance reports, CSV summaries, JSON results, and SVG visualizations.
- A standard-library-only Python implementation targeting Python 3.9 and later.

### What the project does not include

- It is not a production hardware memory controller or a Linux kernel module.
- It does not provide direct proof of performance improvements on real CXL hardware.
- It does not use actual persistent CXL memory; the persistent tier is simulated.
- Its latency, bandwidth, and migration costs are model assumptions that require calibration against real hardware measurements.
- Its Linux backend is an experimental Phase 2 stub containing a sysfs capability probe and a guarded `move_pages` wrapper. It was tested only on a system with one NUMA node and no CXL hardware.

**Important:** Simulation results indicate potential performance behaviour under the configured assumptions. They should not be interpreted as real-hardware benchmarks.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.9+ |
| Dependencies | Python standard library only |
| Testing framework | `unittest` |
| Experiment execution | Custom command-line interface |
| Results storage | CSV and JSON |
| Report generation | Markdown |
| Performance visualization | SVG |
| Linux memory interface | sysfs and `move_pages` wrapper |
| Memory architecture | DDR5, CXL DRAM, and an emulated persistent tier |

## 4. Quick Start and Execution

### Step 1: Navigate to the project directory

```bash
cd cxl_hybrid_memory
```

### Step 2: Configure the Python module path

For Linux or macOS:

```bash
export PYTHONPATH=src
```

For Windows Command Prompt:

```cmd
set PYTHONPATH=src
```

For Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
```

### Step 3: Execute the unit tests

```bash
python -m unittest discover -s tests -v
```

The project documentation specifies 31 unit tests. A successful run should finish without test failures or import errors.

### Step 4: Run a quick experiment suite

```bash
python -m cxltier suite --quick --out results/quick
```

The quick suite is intended to provide an initial evaluation of the implemented memory placement policies.

### Step 5: Run the complete experiment suite

```bash
python -m cxltier suite --seeds 5 --out results/full
```

This command runs experiments using five random seeds. The documented expected execution time is approximately three to four minutes, depending on the system.

### Step 6: Compare selected workloads and policies

```bash
python -m cxltier run --workloads zipf,phase --policies ablation --seeds 3 --out results/mine
```

This experiment evaluates the selected Zipf-distributed and phase-changing workloads using the ablation policy group across three seeds.

### Step 7: Display the memory placement decision matrix

```bash
python -m cxltier matrix
```

This command displays the decision matrix used to examine memory placement choices.

### Step 8: Probe Linux memory capabilities

```bash
python -m cxltier probe
```

This command checks the operating system interfaces exposed by the Linux backend. On Windows, Linux-specific functionality may be unavailable and should be tested in a suitable Linux environment.

## 5. Project Architecture

| File or directory | Responsibility |
|---|---|
| `src/cxltier/config.py` | Defines memory tiers, access costs, configuration, and validation. |
| `src/cxltier/workloads.py` | Generates seven synthetic memory access traces. |
| `src/cxltier/monitor.py` | Models sampled memory access monitoring. |
| `src/cxltier/hotness.py` | Estimates page access frequency and recency using EWMA. |
| `src/cxltier/planner.py` | Implements the shared promotion and demotion planner with a cost model. |
| `src/cxltier/policies.py` | Defines 11 memory placement policies, including baselines, adaptive methods, ablations, and oracles. |
| `src/cxltier/simulator.py` | Implements the simulation loop, migration execution, failure handling, and migration ping-pong counting. |
| `src/cxltier/journal.py` | Models write-ahead journaling and crash recovery. |
| `src/cxltier/experiments.py` | Coordinates experiment execution. |
| `src/cxltier/report.py` | Generates experiment reports. |
| `src/cxltier/plotting.py` | Produces performance visualizations. |
| `src/cxltier/cli.py` | Provides the command-line interface. |
| `src/cxltier/linux_backend.py` | Implements the Linux sysfs probe and guarded page-migration wrapper. |
| `tests/test_core.py` | Contains the project's 31 documented unit tests. |
| `docs/` | Contains architecture, assumptions, persistence, results, and roadmap documentation. |
| `results/full/` | Stores previously generated experiment results, if present in the project checkout. |

## 6. Experiment Outputs

Each experiment output directory is designed to contain the following files:

- `report.md` — Summary and interpretation of experiment results.
- `runs.csv` — Per-run measurements and experiment metadata.
- `summary.json` — Machine-readable aggregated results.
- `speedup.svg` — Visualization of relative performance.
- `phase_timeline.svg` — Visualization of performance behaviour across workload phases.

The actual files and metrics depend on the experiment configuration and whether the commands complete successfully.

## 7. Recommended Documentation Reading Order

Before modifying the implementation or interpreting the experimental results, review the following documents.

**1. `docs/RESULTS.md` — Experimental Findings**

Review the measured simulation outcomes, comparisons against baseline policies, and cases where the proposed policy does not improve performance. Pay attention to negative results as well as positive ones.

**2. `docs/ARCHITECTURE.md` — System Design**

Understand the simulation architecture, memory placement policies, migration planner, cost model, and correctness considerations.

**3. `docs/ASSUMPTIONS.md` — Model Assumptions**

Examine the latency, bandwidth, migration, and other model parameters. These assumptions must be validated and calibrated before drawing conclusions about real CXL systems.

## 8. Expected Research Outcome

The project aims to establish an experimental framework for answering the following research question:

*Can access-frequency-aware, cost-sensitive page migration improve performance in a three-tier hybrid memory system compared with simpler placement policies, and under what workload conditions does migration overhead outweigh its benefits?*

The evaluation should compare policies using relevant metrics such as simulated access cost, execution time, migration overhead, promotion and demotion counts, and migration ping-pong frequency, where those metrics are implemented and reported by the simulator.

The results can support further research into adaptive memory placement, migration thresholds, workload phase changes, and the trade-offs between memory capacity, access latency, and migration cost.

## 9. Conclusion

The CXL Hybrid Memory project provides a reproducible, dependency-free simulation environment for investigating access-frequency-based memory page placement across DDR5, CXL DRAM, and an emulated persistent memory tier. Its configurable policies, synthetic workloads, testing framework, and automated reporting make it suitable for academic experimentation and comparative analysis.

The principal contribution is an experimental method for studying when intelligent memory placement can help, when it can hurt, and which assumptions need to be validated before considering implementation on real CXL-enabled systems.
