from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """A resumable background task handle (à la `codex resume` / Claude `/tasks`)."""

    id: str
    coroutine: Callable[[], Awaitable[Any]]
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _task: asyncio.Task | None = None


class BackgroundTaskRegistry:
    """Registry of background tasks with submit / await / cancel / resume.

    Provides the asynchronous task model that agentic coding tools expose
    (background agents, `/tasks` panel). Tasks run concurrently and can be
    inspected or resumed after the initiating turn ends.
    """

    def __init__(self):
        self._tasks: dict[str, BackgroundTask] = {}

    def submit(self, coroutine: Callable[[], Awaitable[Any]], metadata: dict | None = None) -> BackgroundTask:
        task = BackgroundTask(
            id=uuid.uuid4().hex[:12],
            coroutine=coroutine,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        return task

    def start(self, task: BackgroundTask) -> BackgroundTask:
        task.status = TaskStatus.RUNNING

        async def _run():
            try:
                task.result = await task.coroutine()
                task.status = TaskStatus.COMPLETED
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                raise
            except Exception as e:  # noqa: BLE001
                task.status = TaskStatus.FAILED
                task.error = str(e)

        task._task = asyncio.create_task(_run())
        return task

    async def wait(self, task_id: str, timeout: float | None = None) -> BackgroundTask:
        task = self._tasks[task_id]
        if task._task is None:
            self.start(task)
        try:
            await asyncio.wait_for(task._task, timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return task

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task._task:
            task._task.cancel()
            task.status = TaskStatus.CANCELLED
            return True
        return False

    def get(self, task_id: str) -> BackgroundTask | None:
        return self._tasks.get(task_id)

    def list(self) -> list[BackgroundTask]:
        return list(self._tasks.values())
