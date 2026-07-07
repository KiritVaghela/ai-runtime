

from abc import ABC, abstractmethod

from ai_runtime.execution.context import ExecutionContext


class ExecutionStage(ABC):
    """
    Base class for all execution stages.
    """

    @abstractmethod
    async def execute(
        self,
        context: ExecutionContext,
    ) -> ExecutionContext:
        """
        Execute this stage.
        """