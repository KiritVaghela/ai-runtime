from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Checkpoint:
    """A snapshot of one or more files taken before a mutating action.

    Mirrors the file checkpoints of Cursor / Claude Code / Copilot: before
    an edit/write, the runtime snapshots affected files so the user can
    roll back. Checkpoints are stored in a `.ai-runtime/checkpoints` dir.
    """

    id: str
    files: dict[str, str] = field(default_factory=dict)  # original path -> backup path


class CheckpointManager:
    """Creates and restores file checkpoints for safe agent edits."""

    def __init__(self, root: str | None = None):
        self._root = Path(root or ".ai-runtime/checkpoints")

    def snapshot(self, paths: list[str]) -> Checkpoint:
        """Snapshot the given file paths; returns a `Checkpoint`."""
        self._root.mkdir(parents=True, exist_ok=True)
        ckpt = Checkpoint(id=uuid.uuid4().hex[:12])
        for p in paths:
            src = Path(p)
            if not src.exists():
                continue
            backup = self._root / ckpt.id / src.name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, backup)
            ckpt.files[str(src.resolve())] = str(backup)
        return ckpt

    def restore(self, checkpoint: Checkpoint) -> None:
        for original, backup in checkpoint.files.items():
            shutil.copy2(backup, original)

    def list(self) -> list[str]:
        if not self._root.exists():
            return []
        return [d.name for d in self._root.iterdir() if d.is_dir()]
