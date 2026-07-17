#!/usr/bin/env bash
# Shared environment for all forge-ai-runtime scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV="$PROJECT_ROOT/venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

export TMPDIR="${TMPDIR:-$HOME/ai-runtime-tmp}"
mkdir -p "$TMPDIR"

# Activate venv if present (best-effort; PY/PIP already point at it).
# shellcheck disable=SC1091
source "$VENV/bin/activate" 2>/dev/null || true
