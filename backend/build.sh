#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD START: $(date) ==="
echo "Working dir: $(pwd)"
python -V
which python || true
python -m pip install --upgrade pip setuptools wheel
# prefer wheels, print pip debug info
python -m pip install --prefer-binary -r requirements.txt --verbose
echo "=== BUILD END: $(date) ==="
