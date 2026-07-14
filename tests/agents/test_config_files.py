from __future__ import annotations

import pytest

from ai_runtime.agents.config_files import (
    discover_instructions,
    load_project_instructions,
)


@pytest.mark.asyncio
async def test_discovers_instruction_files(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("Use pytest.")
    (tmp_path / "AGENTS.md").write_text("Be concise.")

    blocks = discover_instructions(str(tmp_path))
    assert any("Use pytest." in b for b in blocks)
    assert any("Be concise." in b for b in blocks)

    combined = load_project_instructions(str(tmp_path))
    assert "Use pytest." in combined and "Be concise." in combined


@pytest.mark.asyncio
async def test_no_instructions_returns_none(tmp_path):
    assert load_project_instructions(str(tmp_path)) is None
