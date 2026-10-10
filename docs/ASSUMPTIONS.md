# Assumptions (all unmeasured; calibrate before trusting any result)

## Tier model (defaults in `config.py`)
| Tier | Role | Read ns | Write ns | Copy GB/s | Notes |
|---|---|---|---|---|---|
| 0 | local DDR5 | 100 | 100 | 10 | 12.5% of pages |
| 1 | CXL DRAM (volatile) | 250 | 250 | 8 | 37.5% of pages |
| 2 | EMULATED persistent CXL | 500 | 1000 | 2 (+2000 ns per page in) | holds all pages if needed |

- These are plausible round numbers, not measurements of any product.
- Tier 2 is emulated. Real byte-addressable persistent CXL memory is not assumed to exist on your platform. Check first (`python3 -m cxltier probe`).
- Tier 1 (volatile DRAM) and tier 2 (persistent) are different things. The simulator never treats them as equal.

## Cost model
- Accesses are serialized. No memory-level parallelism, no CPU caches, no bandwidth contention.
- Migration copy time = 3000 ns fixed (unmap, TLB shootdown, locking) + 4096 B / min(bandwidth) + extra for destination.
- The application waits for 50% of copy time (`stall_fraction`). Sensitivity runs use 25% and 100%.
- Monitor cost: 30 ns per sampled access + 5 ns per tracked page per epoch. Default sample rate 20%.
- 1% of pages are pinned (cannot move). Moves that fail are retried only after 10 epochs.

## Workloads and baseline
- Traces are synthetic. They keep only per-page read/write counts per epoch, not order.
- "static_firsttouch" fills DDR5 with pages in a **random** allocation order. Real first-touch order is not random; it often correlates with hotness (hot data is allocated early). So the baseline may be weaker here than in a real system, and speedups may be overstated.
- Hot/cold behavior of real applications is more complex than these 7 patterns.

## Not modeled
- Huge pages, shared/COW pages, page-cache pages, device-pinned memory (only a flat "pinned" fraction).
- Interference between application threads and the migration thread beyond `stall_fraction`.
- Energy. NUMA topology beyond three flat tiers. Multi-process isolation.
