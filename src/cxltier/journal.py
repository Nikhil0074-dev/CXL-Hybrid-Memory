"""Write-ahead migration journal for the persistent tier.

Protocol (copy-then-switch):
  1. begin(group)   : record the intended page moves. Data is still valid in the source tier.
  2. copy the data, update the mapping, flush/persist the destination.
  3. commit(group)  : record completion.
After a crash, replay() applies only COMMITTED groups to the last durable snapshot. A group with
BEGIN but no COMMIT is rolled back (the source copy was never discarded).

This models the bookkeeping only. It does NOT prove durability of real hardware: real persistent
memory also needs cache-line write-back and ordering barriers (see docs/PERSISTENCE.md)."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

Copy = Tuple[int, int, int]  # (page, src_tier, dst_tier)


class JournalError(Exception):
    pass


class Journal:
    def __init__(self, path: Optional[str] = None, fsync: bool = True) -> None:
        self.records: List[dict] = []
        self.path = path
        self.fsync = fsync
        self._fh = open(path, "a", encoding="utf-8") if path else None
        self._next_gid = 1

    def _write(self, rec: dict) -> None:
        self.records.append(rec)
        if self._fh is not None:
            self._fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
            self._fh.flush()
            if self.fsync:
                os.fsync(self._fh.fileno())

    def begin(self, copies: Sequence[Copy]) -> int:
        gid = self._next_gid
        self._next_gid += 1
        self._write({"op": "BEGIN", "gid": gid, "copies": [list(c) for c in copies]})
        return gid

    def commit(self, gid: int) -> None:
        self._write({"op": "COMMIT", "gid": gid})

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    @staticmethod
    def load(path: str) -> List[dict]:
        """Read a journal file. A torn (partially written) LAST line is ignored."""
        out: List[dict] = []
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for i, line in enumerate(lines):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                if i == len(lines) - 1:
                    break
                raise JournalError(f"corrupt journal record at line {i + 1}")
        return out


def replay(snapshot: Sequence[int], records: Sequence[dict]) -> Tuple[List[int], List[int]]:
    """Rebuild the page->tier mapping from a snapshot plus the journal.
    Returns (mapping, rolled_back_group_ids)."""
    mapping = list(snapshot)
    pending: Dict[int, List[Copy]] = {}
    order: List[int] = []
    committed = set()
    for rec in records:
        if rec["op"] == "BEGIN":
            pending[rec["gid"]] = [tuple(c) for c in rec["copies"]]  # type: ignore[misc]
            order.append(rec["gid"])
        elif rec["op"] == "COMMIT":
            if rec["gid"] not in pending:
                raise JournalError(f"COMMIT without BEGIN for group {rec['gid']}")
            committed.add(rec["gid"])
        else:
            raise JournalError(f"unknown record {rec}")
    rolled_back = []
    for gid in order:
        if gid not in committed:
            rolled_back.append(gid)
            continue
        for p, src, dst in pending[gid]:
            if mapping[p] != src:
                raise JournalError(f"group {gid}: page {p} expected in tier {src}, found {mapping[p]}")
        for p, src, dst in pending[gid]:
            mapping[p] = dst
    return mapping, rolled_back
