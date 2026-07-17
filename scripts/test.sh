#!/usr/bin/env bash
# Run the full test suite. Exits non-zero on failure (set -e propagates pytest).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

"$PY" -m pytest -q
