"""Configuration objects. All latency/bandwidth numbers are ASSUMPTIONS to be calibrated
against real hardware (see docs/ASSUMPTIONS.md). Nothing here is a measured result."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

PAGE_BYTES = 4096


@dataclass(frozen=True)
class TierSpec:
    name: str
    capacity_pages: int
    read_ns: float
    write_ns: float
    migrate_bw_gbps: float            # effective page-copy bandwidth in GB/s (= bytes per ns)
    migrate_in_extra_ns: float = 0.0  # extra cost per page copied INTO this tier
    persistent: bool = False
    emulated: bool = False

    def validate(self) -> None:
        if self.capacity_pages <= 0:
            raise ValueError(f"tier {self.name}: capacity must be positive")
        if self.read_ns <= 0 or self.write_ns <= 0:
            raise ValueError(f"tier {self.name}: latencies must be positive")
        if self.migrate_bw_gbps <= 0:
            raise ValueError(f"tier {self.name}: migration bandwidth must be positive")
        if self.migrate_in_extra_ns < 0:
            raise ValueError(f"tier {self.name}: extra cost cannot be negative")


def default_tiers(num_pages: int) -> List[TierSpec]:
    """Tier 0 = local DDR5, tier 1 = CXL DRAM, tier 2 = EMULATED persistent CXL tier."""
    t0 = max(8, int(num_pages * 0.125))
    t1 = max(16, int(num_pages * 0.375))
    t2 = max(num_pages, int(num_pages * 0.75))
    return [
        TierSpec("local_ddr5", t0, read_ns=100.0, write_ns=100.0, migrate_bw_gbps=10.0),
        TierSpec("cxl_dram", t1, read_ns=250.0, write_ns=250.0, migrate_bw_gbps=8.0),
        TierSpec("cxl_persistent_emulated", t2, read_ns=500.0, write_ns=1000.0,
                 migrate_bw_gbps=2.0, migrate_in_extra_ns=2000.0,
                 persistent=True, emulated=True),
    ]


@dataclass
class SimConfig:
    num_pages: int = 4096
    epochs: int = 40
    accesses_per_epoch: int = 10000
    tiers: Optional[List[TierSpec]] = None
    headroom_frac: float = 0.02          # free-slot reserve kept in every non-last tier
    migration_fixed_ns: float = 3000.0   # unmap + TLB shootdown + locking per page
    stall_fraction: float = 0.5          # share of copy time the application actually waits
    monitor_sample_rate: float = 0.2     # fraction of accesses the monitor observes
    monitor_cost_per_sample_ns: float = 30.0
    scan_cost_per_page_ns: float = 5.0   # per tracked page, per epoch
    pinned_fraction: float = 0.01        # pages that can never be migrated
    migration_fail_prob: float = 0.0     # extra random transient failures
    fail_backoff_epochs: int = 10
    pingpong_window: int = 5

    def __post_init__(self) -> None:
        if self.tiers is None:
            self.tiers = default_tiers(self.num_pages)
        self.validate()

    def validate(self) -> None:
        if self.num_pages <= 0 or self.epochs <= 0 or self.accesses_per_epoch <= 0:
            raise ValueError("num_pages, epochs and accesses_per_epoch must be positive")
        if len(self.tiers) < 2:
            raise ValueError("need at least two tiers")
        for t in self.tiers:
            t.validate()
        if not (0.0 < self.monitor_sample_rate <= 1.0):
            raise ValueError("monitor_sample_rate must be in (0, 1]")
        if not (0.0 <= self.stall_fraction <= 1.0):
            raise ValueError("stall_fraction must be in [0, 1]")
        if not (0.0 <= self.pinned_fraction < 1.0):
            raise ValueError("pinned_fraction must be in [0, 1)")
        if not (0.0 <= self.migration_fail_prob < 1.0):
            raise ValueError("migration_fail_prob must be in [0, 1)")
        if not (0.0 <= self.headroom_frac < 0.5):
            raise ValueError("headroom_frac must be in [0, 0.5)")
        caps = [t.capacity_pages for t in self.tiers]
        hr = self.headroom()
        usable = sum(c - h for c, h in zip(caps[:-1], hr[:-1])) + caps[-1]
        if usable < self.num_pages:
            raise ValueError("tier capacities (minus headroom) cannot hold num_pages")

    def headroom(self) -> List[int]:
        """Free pages every tier must keep. The last tier keeps none."""
        out = []
        last = len(self.tiers) - 1
        for i, t in enumerate(self.tiers):
            if i == last or self.headroom_frac <= 0:
                out.append(0)
            else:
                out.append(max(1, int(t.capacity_pages * self.headroom_frac)))
        return out

    def copy_ns(self, src: int, dst: int) -> float:
        """Time to copy one page from tier src to tier dst (before stall_fraction)."""
        a, b = self.tiers[src], self.tiers[dst]
        bw = min(a.migrate_bw_gbps, b.migrate_bw_gbps)
        return self.migration_fixed_ns + PAGE_BYTES / bw + b.migrate_in_extra_ns

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimConfig":
        d = dict(d)
        tiers = d.pop("tiers", None)
        if tiers is not None:
            tiers = [t if isinstance(t, TierSpec) else TierSpec(**t) for t in tiers]
        return cls(tiers=tiers, **d)

    @classmethod
    def from_json(cls, path: str) -> "SimConfig":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def replace(self, **kw: Any) -> "SimConfig":
        """Return a modified copy. Changing num_pages re-derives tiers unless tiers is given."""
        d = self.to_dict()
        tiers = d.pop("tiers")
        if "tiers" in kw:
            tiers = kw.pop("tiers")
        elif "num_pages" in kw and kw["num_pages"] != self.num_pages:
            tiers = None
        d.update(kw)
        if tiers is not None:
            tiers = [t if isinstance(t, TierSpec) else TierSpec(**t) for t in tiers]
        return SimConfig(tiers=tiers, **d)
