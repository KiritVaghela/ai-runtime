from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is importable so `ai_runtime` resolves.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
