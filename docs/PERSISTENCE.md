# Persistent tier: what is and is not claimed

## Facts the design relies on
- Moving a page between tiers does **not** make data durable. Durability needs flush + ordering on the persistent device, and a recoverable record of where each page lives.
- Volatile CXL DRAM loses data on power loss. Only genuinely persistent media (or a battery/flush-backed domain) survives.
- If tier 2 is an NVMe SSD or a file mapping, it is **not** byte-addressable memory. Moving a page there is page-out (block write), moving back is a page-fault read. Costs and failure modes differ.

## What the code implements (`journal.py`)
- Copy-then-switch protocol with a write-ahead journal: BEGIN(group) -> copy -> switch mapping -> COMMIT(group).
- Source copy is kept until COMMIT, so a crash before COMMIT is rolled back safely.
- Recovery = last snapshot + replay of committed groups. Uncommitted groups are reported and discarded.
- Swaps are one group, so a crash can never leave only one half of a swap applied.
- File journal uses flush + `fsync`. A torn last line is ignored; corruption elsewhere raises `JournalError`.
- Tests: crash after BEGIN at 3 different points, recovery equals live state; torn tail; inconsistent journal detection.

## What the code does NOT prove
- No cache-line write-back (e.g., CLWB), no store fence, no persistence-domain (ADR/eADR/GPF) handling. Real hardware needs these.
- No data checksums, no media error handling, no wear/endurance model (only `pm_bytes_written` is counted as a proxy).
- The journal only records mapping intent. It does not move real bytes.

## Before real hardware
1. Confirm tier 2 exposes byte-addressable CXL.mem with a persistence guarantee from the vendor.
2. Use an established persistent-memory library for the data path; do not hand-roll flush logic.
3. Add checksums and a crash-injection harness (power-cut or VM kill) on a disposable machine.
