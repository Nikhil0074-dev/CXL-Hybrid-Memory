#!/usr/bin/env python3
"""Print what this Linux host exposes: NUMA nodes, memory tiers, CXL devices. Read-only."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from cxltier.linux_backend import probe  # noqa: E402

print(json.dumps(probe(), indent=2))
