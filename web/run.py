from __future__ import annotations

import sys
from pathlib import Path

# Prefer the published `forge-ai-runtime` package (pip install forge-ai-runtime).
# When it is installed we must NOT let the local `ai_runtime/` source tree
# (which lives in the repo root) shadow it. The repo root is only added to the
# path so the `web` package itself can be imported, and it is appended AFTER
# site-packages so the installed `ai_runtime` still wins.
ROOT = Path(__file__).resolve().parent.parent
try:
    import ai_runtime  # noqa: F401  (resolves to the installed package)
except ImportError:
    # Not installed: fall back to the local source tree.
    sys.path.insert(0, str(ROOT))
else:
    # Installed: drop the cwd (which may contain a local ai_runtime/) and only
    # append ROOT at the end so `web` is importable without shadowing the pkg.
    sys.path = [p for p in sys.path if p != ""]
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))

from web.config import load_config  # noqa: E402

config = load_config()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "web.app:app",
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
