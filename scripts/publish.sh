#!/usr/bin/env bash
# Upload the built dist/ to PyPI. Pass "testpypi" for a dry-run upload.
# Usage: scripts/publish.sh [testpypi]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

if [ "${1:-}" = "testpypi" ]; then
  REPO="--repository testpypi"; echo "==> Uploading to TestPyPI"
else
  REPO=""; echo "==> Uploading to PyPI (real index)"
fi

"$PY" -m twine upload $REPO dist/*
