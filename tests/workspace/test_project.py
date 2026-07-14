from __future__ import annotations

import pytest

from ai_runtime.workspace import Project


@pytest.mark.asyncio
async def test_project_scopes_tools_and_instructions(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("Use ruff.")
    proj = Project(root=str(tmp_path))
    assert proj.name == tmp_path.name
    assert "Use ruff." in (proj.instructions or "")

    proj.install_builtin_tools()
    assert {"Read", "Write", "Edit", "Glob", "Grep", "Bash"} <= set(proj.tool_registry._tools.keys())


@pytest.mark.asyncio
async def test_project_system_prompt_combines_instructions():
    proj = Project(root="/tmp", instructions="Be terse.")
    prompt = proj.as_system_prompt("You are a helper.")
    assert "You are a helper." in prompt and "Be terse." in prompt
