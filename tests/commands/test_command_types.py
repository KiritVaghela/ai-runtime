from __future__ import annotations

import pytest

from ai_runtime.commands import CommandRegistry, Command, default_commands


@pytest.mark.asyncio
async def test_new_agentic_commands_present():
    reg = default_commands()
    names = {c.name for c in reg.list()}
    assert {"compact", "context", "clear", "review", "explain", "test", "workflow"} <= names


@pytest.mark.asyncio
async def test_command_categories():
    reg = default_commands()
    by_cat = {}
    for c in reg.list():
        by_cat.setdefault(c.category, []).append(c.name)
    assert by_cat["review"] == ["review"]
    assert by_cat["explain"] == ["explain"]
    assert by_cat["test"] == ["test"]
    assert by_cat["workflow"] == ["workflow"]


@pytest.mark.asyncio
async def test_review_command_renders_diff_arg():
    reg = default_commands()
    rendered = reg.render("review", diff="--- a/file.py\n+++ b/file.py")
    assert "file.py" in rendered


@pytest.mark.asyncio
async def test_workflow_command_renders_name_and_task():
    reg = default_commands()
    rendered = reg.render("workflow", name="release", task="ship it")
    assert "release" in rendered
    assert "ship it" in rendered


@pytest.mark.asyncio
async def test_command_with_args_binds_template():
    cmd = Command(
        "demo",
        "demo",
        prompt_template="Look at {target}: {code}",
        category="explain",
        args=["target", "code"],
    )
    bound = cmd.with_args(target="function", code="def f(): pass")
    assert bound.render() == "Look at function: def f(): pass"
