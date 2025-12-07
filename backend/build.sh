#!/usr/bin/env bash
set -euo pipefail
echo "=== build.sh: starting ==="

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

echo "=== build.sh: finished ==="

