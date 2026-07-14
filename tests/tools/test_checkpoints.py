from __future__ import annotations

import pytest

from ai_runtime.tools.checkpoints import CheckpointManager


@pytest.mark.asyncio
async def test_checkpoint_snapshot_and_restore(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("original")

    mgr = CheckpointManager(str(tmp_path / ".ckpt"))
    ckpt = mgr.snapshot([str(f)])
    assert ckpt.id in mgr.list()

    f.write_text("mutated")
    assert f.read_text() == "mutated"

    mgr.restore(ckpt)
    assert f.read_text() == "original"
