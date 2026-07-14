from __future__ import annotations

import pytest

from ai_runtime.commands import CommandRegistry, Command, default_commands


@pytest.mark.asyncio
async def test_default_commands_present():
    reg = default_commands()
    names = {c.name for c in reg.list()}
    assert {"compact", "context", "clear"} <= names


@pytest.mark.asyncio
async def test_register_and_render():
    reg = CommandRegistry()
    reg.register(Command("summarize", "Summarize", prompt_template="Summarize: {text}"))
    rendered = reg.render("summarize", text="hello")
    assert rendered == "Summarize: hello"


@pytest.mark.asyncio
async def test_unknown_command_returns_none():
    reg = default_commands()
    assert reg.render("nope") is None
