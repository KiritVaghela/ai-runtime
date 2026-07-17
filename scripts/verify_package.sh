#!/usr/bin/env bash
# Install the freshly built wheel into a clean venv and confirm imports work.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

WHEEL=$(ls -t dist/*.whl | head -1)
python3 -m venv /tmp/pkgtest
/tmp/pkgtest/bin/pip install "$WHEEL"
/tmp/pkgtest/bin/python -c "
import ai_runtime
print('version:', ai_runtime.__version__)
from ai_runtime.providers.default_registry import create_default_registry
print('providers:', [p.value for p in create_default_registry().list_providers()])
"
rm -rf /tmp/pkgtest
echo "OK: clean install works"
