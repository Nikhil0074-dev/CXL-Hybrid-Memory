"""Weighted decision matrix (weights sum to 100). Totals are computed here, never typed by hand."""
from __future__ import annotations

from typing import Dict, List, Tuple

CRITERIA: List[Tuple[str, int]] = [
    ("Technical feasibility", 10), ("Models all three tiers", 8), ("Realism of migration behaviour", 8),
    ("Experimental reproducibility", 10), ("Measurement accuracy", 6), ("Development simplicity", 8),
    ("Low hardware dependence", 8), ("Low kernel-integration need", 6), ("Safety and correctness", 6),
    ("Performance potential", 5), ("Scalability", 3), ("Maintainability", 4),
    ("Research contribution", 10), ("Cost and schedule", 8),
]
ALTERNATIVES = {
    "A Static placement": [5, 2, 1, 4, 3, 5, 3, 5, 5, 1, 3, 5, 1, 5],
    "B Frequency controller (Linux user space)": [3, 3, 4, 2, 4, 3, 2, 4, 3, 3, 3, 3, 2, 3],
    "C Adaptive cost-aware controller, simulator-first": [4, 5, 3, 5, 2, 3, 4, 4, 4, 4, 3, 4, 4, 4],
    "D Kernel-integrated tier controller": [1, 2, 5, 1, 5, 1, 1, 1, 1, 5, 5, 1, 5, 1],
    "E Plain trace simulator (baseline policies only)": [5, 5, 2, 5, 2, 4, 5, 5, 5, 2, 3, 4, 2, 5],
}
GATE = "Must contain a new placement policy that can be compared against baselines (research question RQ1)."
GATE_PASS = {"A Static placement": False, "B Frequency controller (Linux user space)": True,
             "C Adaptive cost-aware controller, simulator-first": True,
             "D Kernel-integrated tier controller": True,
             "E Plain trace simulator (baseline policies only)": False}


def validate() -> None:
    if sum(w for _, w in CRITERIA) != 100:
        raise ValueError("weights must total 100")
    for name, sc in ALTERNATIVES.items():
        if len(sc) != len(CRITERIA):
            raise ValueError(f"{name}: wrong number of scores")
        if any(not (1 <= s <= 5) for s in sc):
            raise ValueError(f"{name}: scores must be 1..5")


def totals() -> Dict[str, float]:
    validate()
    return {n: sum(s * w for s, (_, w) in zip(sc, CRITERIA)) / 100.0 for n, sc in ALTERNATIVES.items()}


def winner() -> str:
    t = totals()
    eligible = {n: v for n, v in t.items() if GATE_PASS[n]}
    return max(eligible, key=eligible.get)


def to_markdown() -> str:
    t = totals()
    names = list(ALTERNATIVES)
    L = ["# Weighted decision matrix", "", "Scores 1 (worst) to 5 (best). For 'cost/complexity' criteria a higher score means cheaper/simpler.", "",
         "| Criterion | Weight | " + " | ".join(n.split(" ")[0] for n in names) + " |",
         "|---|---|" + "---|" * len(names)]
    for i, (c, w) in enumerate(CRITERIA):
        L.append(f"| {c} | {w} | " + " | ".join(str(ALTERNATIVES[n][i]) for n in names) + " |")
    L.append("| **Weighted total (out of 5)** | 100 | " + " | ".join(f"**{t[n]:.2f}**" for n in names) + " |")
    L += ["", "Alternatives:", ""] + [f"- **{n.split(' ')[0]}** = {n[2:]}" for n in names]
    L += ["", f"**Gate (pass/fail, applied before ranking):** {GATE}", ""]
    for n in names:
        L.append(f"- {n.split(' ')[0]}: {'pass' if GATE_PASS[n] else 'FAIL'}")
    L += ["", f"**Selected: {winner()}** (highest weighted total among alternatives that pass the gate).", ""]
    best = max(t, key=t.get)
    if best != winner():
        L.append(f"Note: {best} has the highest raw total ({t[best]:.2f}) but fails the gate. It is kept as the test bench inside the selected solution, not as the project.")
    return "\n".join(L)
