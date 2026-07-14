from __future__ import annotations

from pathlib import Path
from typing import Any


# Candidate instruction-file locations, checked in priority order.
INSTRUCTION_CANDIDATES = [
    ".github/copilot-instructions.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursor/rules",
    "ai-runtime.md",
]


def discover_instructions(project_root: str) -> list[str]:
    """Return the contents of discovered agent instruction files.

    Mirrors the instruction-file discovery of Copilot (`copilot-instructions.md`),
    Codex/Claude (`AGENTS.md` / `CLAUDE.md`), and Cursor (`.cursor/rules`).
    Returns a list of markdown text blocks to prepend to the system prompt.
    """
    root = Path(project_root)
    blocks: list[str] = []
    for rel in INSTRUCTION_CANDIDATES:
        path = root / rel
        if path.is_file():
            blocks.append(path.read_text(encoding="utf-8", errors="replace"))
        elif path.is_dir():
            for f in sorted(path.glob("*.mdc")) + sorted(path.glob("*.md")):
                blocks.append(f.read_text(encoding="utf-8", errors="replace"))
    return blocks


def load_project_instructions(project_root: str) -> str | None:
    """Concatenate discovered instruction files into a single system block."""
    blocks = discover_instructions(project_root)
    return "\n\n---\n\n".join(blocks) if blocks else None
