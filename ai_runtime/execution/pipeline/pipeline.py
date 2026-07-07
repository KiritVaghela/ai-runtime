from ai_runtime.execution.context import ExecutionContext

from .stage import ExecutionStage


class ExecutionPipeline:

    def __init__(self):
        self._stages: list[ExecutionStage] = []

    @property
    def stages(self):
        return list(self._stages)

    def add(
        self,
        stage: ExecutionStage,
    ) -> "ExecutionPipeline":
        self._stages.append(stage)
        return self

    def remove(
        self,
        stage: ExecutionStage,
    ) -> None:
        self._stages.remove(stage)

    def clear(self) -> None:
        self._stages.clear()

    async def execute(
        self,
        context: ExecutionContext,
    ) -> ExecutionContext:

        for stage in self._stages:
            context = await stage.execute(context)

        return context