from __future__ import annotations

import pytest

from ai_runtime.tools import (
    PermissionPolicy,
    PermissionRule,
    PermissionDecision,
    PermissionError,
    GuardedToolExecutor,
    ToolExecutor,
    ToolRegistry,
    ToolResult,
)
from ai_runtime.tools.tool import Tool


class _EchoTool(Tool):
    name = "Bash"
    description = "run a command"

    def run(self, context, input):
        return ToolResult(success=True, output=input)


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(_EchoTool())
    return reg


@pytest.mark.asyncio
async def test_deny_rule_blocks_execution(registry):
    policy = PermissionPolicy(
        rules=[PermissionRule("Bash", "git push *", PermissionDecision.DENY)],
        default=PermissionDecision.ALLOW,
    )
    guarded = GuardedToolExecutor(ToolExecutor(registry), policy)

    # Allowed command runs.
    ok = await guarded.execute("Bash", None, {"cmd": "ls"})
    assert ok.success

    # Denied command is blocked.
    blocked = await guarded.execute("Bash", None, {"cmd": "git push origin"})
    assert not blocked.success
    assert "denied" in blocked.error.lower()


@pytest.mark.asyncio
async def test_ask_defers_to_callback(registry):
    policy = PermissionPolicy(default=PermissionDecision.ASK)
    calls = []

    async def on_ask(name, params):
        calls.append((name, params))
        return name == "Bash"

    guarded = GuardedToolExecutor(ToolExecutor(registry), policy, on_ask=on_ask)
    res = await guarded.execute("Bash", None, {"cmd": "rm -rf"})
    assert res.success
    assert calls == [("Bash", "cmd=rm -rf")]


@pytest.mark.asyncio
async def test_ask_without_callback_is_denied(registry):
    policy = PermissionPolicy(default=PermissionDecision.ASK)
    guarded = GuardedToolExecutor(ToolExecutor(registry), policy)
    res = await guarded.execute("Bash", None, {"cmd": "x"})
    assert not res.success
    assert "Permission required" in res.error
