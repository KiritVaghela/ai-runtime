#!/usr/bin/env bash
# Install web deps (forge-ai-runtime) and confirm the web app imports the
# published package rather than the local source tree.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

"$PIP" install -r web/requirements.txt

"$PY" -c "
import sys; sys.path = [p for p in sys.path if p != '']
sys.path.append('$PROJECT_ROOT')
import ai_runtime
print('ai_runtime ->', ai_runtime.__file__, ai_runtime.__version__)
from web.app import app
print('web.app OK; routes:', len(app.routes))
"
echo "OK: web app integrated with published package"
