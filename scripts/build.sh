#!/usr/bin/env bash
# Build wheel + sdist, then self-validate that web/ and PUBLISHING.md are
# excluded from the package. Exits 1 if anything leaked in.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

rm -rf dist build *.egg-info
"$PY" -m build

WHEEL=$(ls -t dist/*.whl | head -1)
SDIST=$(ls -t dist/*.tar.gz | head -1)

web_wheel=$(unzip -l "$WHEEL" | grep -c "web/")
web_sdist=$(tar tzf "$SDIST" | grep -c "web/")
pub_wheel=$(unzip -l "$WHEEL" | grep -c "PUBLISHING.md")
pub_sdist=$(tar tzf "$SDIST" | grep -c "PUBLISHING.md")

if [ "$web_wheel" -ne 0 ] || [ "$web_sdist" -ne 0 ] || [ "$pub_wheel" -ne 0 ] || [ "$pub_sdist" -ne 0 ]; then
  echo "ERROR: web/ or PUBLISHING.md leaked into the package" >&2
  echo "  web/ in wheel=$web_wheel sdist=$web_sdist" >&2
  echo "  PUBLISHING.md in wheel=$pub_wheel sdist=$pub_sdist" >&2
  exit 1
fi

echo "OK: package clean (web/ and PUBLISHING.md excluded)"
echo "  wheel: $WHEEL"
echo "  sdist: $SDIST"
