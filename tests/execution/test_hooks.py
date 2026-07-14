from __future__ import annotations

import pytest

from ai_runtime.execution.hooks import (
    HookRegistry,
    HookEvent,
    HookContext,
    HookResult,
)


@pytest.mark.asyncio
async def test_pre_tool_use_can_block():
    reg = HookRegistry()
    blocked = []

    async def hook(ctx: HookContext) -> HookResult:
        if ctx.tool_name == "Bash":
            blocked.append(ctx.tool_name)
            return HookResult(continue_=False, note="no shell")
        return HookResult()

    reg.register(HookEvent.PRE_TOOL_USE, hook)
    res = await reg.trigger(
        HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="Bash")
    )
    assert not res.continue_
    assert blocked == ["Bash"]


@pytest.mark.asyncio
async def test_post_tool_use_observes():
    reg = HookRegistry()
    seen = []

    async def hook(ctx: HookContext) -> HookResult:
        seen.append(ctx.tool_name)
        return HookResult()

    reg.register(HookEvent.POST_TOOL_USE, hook)
    await reg.trigger(
        HookContext(event=HookEvent.POST_TOOL_USE, tool_name="Write")
    )
    assert seen == ["Write"]


@pytest.mark.asyncio
async def test_patch_merges():
    reg = HookRegistry()

    async def hook(ctx: HookContext) -> HookResult:
        return HookResult(patch={"tool_input": {"safe": True}})

    reg.register(HookEvent.PRE_TOOL_USE, hook)
    res = await reg.trigger(
        HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="X")
    )
    assert res.patch["tool_input"] == {"safe": True}
