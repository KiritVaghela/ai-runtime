from __future__ import annotations

import asyncio

import pytest

from ai_runtime.execution.background import BackgroundTaskRegistry, TaskStatus


@pytest.mark.asyncio
async def test_background_task_runs_and_completes():
    reg = BackgroundTaskRegistry()

    async def work():
        return 42

    task = reg.submit(work)
    reg.start(task)
    result = await reg.wait(task.id)
    assert result.status == TaskStatus.COMPLETED
    assert result.result == 42


@pytest.mark.asyncio
async def test_background_task_failure_recorded():
    reg = BackgroundTaskRegistry()

    async def boom():
        raise ValueError("nope")

    task = reg.submit(boom)
    reg.start(task)
    result = await reg.wait(task.id)
    assert result.status == TaskStatus.FAILED
    assert "nope" in result.error


@pytest.mark.asyncio
async def test_background_task_cancel():
    reg = BackgroundTaskRegistry()

    async def slow():
        await asyncio.sleep(10)

    task = reg.submit(slow)
    reg.start(task)
    assert reg.cancel(task.id)
    try:
        await asyncio.wait_for(task._task, timeout=1.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    assert reg.get(task.id).status == TaskStatus.CANCELLED
