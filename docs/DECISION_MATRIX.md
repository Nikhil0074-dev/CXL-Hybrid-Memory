# Weighted decision matrix

Scores 1 (worst) to 5 (best). For 'cost/complexity' criteria a higher score means cheaper/simpler.

| Criterion | Weight | A | B | C | D | E |
|---|---|---|---|---|---|---|
| Technical feasibility | 10 | 5 | 3 | 4 | 1 | 5 |
| Models all three tiers | 8 | 2 | 3 | 5 | 2 | 5 |
| Realism of migration behaviour | 8 | 1 | 4 | 3 | 5 | 2 |
| Experimental reproducibility | 10 | 4 | 2 | 5 | 1 | 5 |
| Measurement accuracy | 6 | 3 | 4 | 2 | 5 | 2 |
| Development simplicity | 8 | 5 | 3 | 3 | 1 | 4 |
| Low hardware dependence | 8 | 3 | 2 | 4 | 1 | 5 |
| Low kernel-integration need | 6 | 5 | 4 | 4 | 1 | 5 |
| Safety and correctness | 6 | 5 | 3 | 4 | 1 | 5 |
| Performance potential | 5 | 1 | 3 | 4 | 5 | 2 |
| Scalability | 3 | 3 | 3 | 3 | 5 | 3 |
| Maintainability | 4 | 5 | 3 | 4 | 1 | 4 |
| Research contribution | 10 | 1 | 2 | 4 | 5 | 2 |
| Cost and schedule | 8 | 5 | 3 | 4 | 1 | 5 |
| **Weighted total (out of 5)** | 100 | **3.40** | **2.92** | **3.87** | **2.36** | **3.95** |

Alternatives:

- **A** = Static placement
- **B** = Frequency controller (Linux user space)
- **C** = Adaptive cost-aware controller, simulator-first
- **D** = Kernel-integrated tier controller
- **E** = Plain trace simulator (baseline policies only)

**Gate (pass/fail, applied before ranking):** Must contain a new placement policy that can be compared against baselines (research question RQ1).

- A: FAIL
- B: pass
- C: pass
- D: pass
- E: FAIL

**Selected: C Adaptive cost-aware controller, simulator-first** (highest weighted total among alternatives that pass the gate).

Note: E Plain trace simulator (baseline policies only) has the highest raw total (3.95) but fails the gate. It is kept as the test bench inside the selected solution, not as the project.