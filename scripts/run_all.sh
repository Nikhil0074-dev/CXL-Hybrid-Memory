#!/bin/sh
# Run tests, then the full experiment suite (about 3-4 minutes on one core).
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=src
python3 -m unittest discover -s tests
python3 -m cxltier suite --seeds 5 --out results/full
echo "Open results/full/main/report.md"
