"""Linux capability probe and a guarded move_pages() wrapper (Phase 2, NOT used by the simulator).

Honest status: this module was exercised only on a machine WITHOUT CXL hardware. It reads sysfs and
can call move_pages(2) in dry-run (default) or real mode. It has never been run on real CXL memory.
Real migration needs: Linux with CONFIG_NUMA, CONFIG_MIGRATION, CXL memory onlined as a NUMA node
(CONFIG_CXL_BUS, CONFIG_CXL_PCI, CONFIG_CXL_MEM, memory hotplug), and CAP_SYS_NICE for pages of
other processes."""
from __future__ import annotations

import ctypes
import ctypes.util
import os
import platform
from typing import Dict, List, Optional, Sequence

SYS_NODE = "/sys/devices/system/node"
SYS_TIERS = "/sys/devices/virtual/memory_tiering"
SYS_CXL = "/sys/bus/cxl/devices"
MPOL_MF_MOVE = 1 << 1
_SYSCALL_MOVE_PAGES = {"x86_64": 279, "aarch64": 239}


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return None


def discover_numa_nodes(root: str = SYS_NODE) -> List[Dict[str, object]]:
    nodes: List[Dict[str, object]] = []
    try:
        names = sorted(n for n in os.listdir(root) if n.startswith("node") and n[4:].isdigit())
    except OSError:
        return nodes
    for name in names:
        nid = int(name[4:])
        cpulist = _read(f"{root}/{name}/cpulist") or ""
        mem_kb = None
        info = _read(f"{root}/{name}/meminfo")
        if info:
            for line in info.splitlines():
                if "MemTotal" in line:
                    parts = line.split()
                    try:
                        mem_kb = int(parts[-2])
                    except (ValueError, IndexError):
                        mem_kb = None
        nodes.append({"node": nid, "cpulist": cpulist, "mem_total_kb": mem_kb,
                      "cpuless": cpulist == "", "distance": _read(f"{root}/{name}/distance")})
    return nodes


def discover_memory_tiers(root: str = SYS_TIERS) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        for name in sorted(os.listdir(root)):
            nl = _read(f"{root}/{name}/nodelist")
            if nl is not None:
                out[name] = nl
    except OSError:
        pass
    return out


def discover_cxl_devices(root: str = SYS_CXL) -> List[str]:
    try:
        return sorted(os.listdir(root))
    except OSError:
        return []


def probe() -> Dict[str, object]:
    return {
        "kernel": platform.release(), "machine": platform.machine(),
        "numa_nodes": discover_numa_nodes(),
        "memory_tiers": discover_memory_tiers(),
        "cxl_devices": discover_cxl_devices(),
        "demotion_enabled": _read("/sys/kernel/mm/numa/demotion_enabled"),
        "numa_balancing": _read("/proc/sys/kernel/numa_balancing"),
        "damon_present": os.path.isdir("/sys/kernel/mm/damon"),
        "note": "Real CXL hardware is present only if cxl_devices is non-empty AND a CPU-less NUMA node exists.",
    }


class MigrationError(Exception):
    pass


class LinuxMigrator:
    """Wraps move_pages(2). dry_run=True never calls the kernel."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self._libc = None
        if not dry_run:
            if platform.system() != "Linux":
                raise MigrationError("move_pages is Linux-only")
            self._libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
            if platform.machine() not in _SYSCALL_MOVE_PAGES:
                raise MigrationError(f"unsupported architecture {platform.machine()}")

    def move(self, pid: int, addrs: Sequence[int], nodes: Sequence[int]) -> List[int]:
        """Request page moves. Returns per-page status (node id >= 0, or negative errno)."""
        if len(addrs) != len(nodes):
            raise ValueError("addrs and nodes must have equal length")
        if not addrs:
            return []
        if self.dry_run:
            return list(nodes)
        n = len(addrs)
        pages = (ctypes.c_void_p * n)(*addrs)
        nds = (ctypes.c_int * n)(*nodes)
        status = (ctypes.c_int * n)()
        nr = _SYSCALL_MOVE_PAGES[platform.machine()]
        self._libc.syscall.restype = ctypes.c_long
        rc = self._libc.syscall(ctypes.c_long(nr), ctypes.c_int(pid), ctypes.c_ulong(n), pages, nds,
                                status, ctypes.c_int(MPOL_MF_MOVE))
        if rc < 0:
            err = ctypes.get_errno()
            raise MigrationError(f"move_pages failed: errno {err} ({os.strerror(err)})")
        return list(status)

    def query_nodes(self, pid: int, addrs: Sequence[int]) -> List[int]:
        """Ask the kernel which node each page is on (nodes=NULL query mode)."""
        if self.dry_run:
            raise MigrationError("query requires dry_run=False")
        n = len(addrs)
        if n == 0:
            return []
        pages = (ctypes.c_void_p * n)(*addrs)
        status = (ctypes.c_int * n)()
        nr = _SYSCALL_MOVE_PAGES[platform.machine()]
        self._libc.syscall.restype = ctypes.c_long
        rc = self._libc.syscall(ctypes.c_long(nr), ctypes.c_int(pid), ctypes.c_ulong(n), pages,
                                None, status, ctypes.c_int(0))
        if rc < 0:
            err = ctypes.get_errno()
            raise MigrationError(f"move_pages query failed: errno {err} ({os.strerror(err)})")
        return list(status)
