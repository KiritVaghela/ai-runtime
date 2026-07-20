from ai_runtime.conversation import ChatRequest

from .stage import ExecutionStage
from ..mode import ExecutionMode
from ..context import ExecutionContext

class RequestBuilderStage(ExecutionStage):
    """
    Builds a ChatRequest from the current ExecutionContext.
    """

    async def execute(
        self,
        context: ExecutionContext,
    ):

        # Surface the agent's registered tools to the provider so it can
        # emit tool calls. The provider mapper only forwards `tools` when the
        # provider advertises the `tools` capability, so this is a no-op for
        # providers that don't support function calling.
        tools = None
        if context.agent is not None:
            registry = getattr(context.agent, "tool_registry", None)
            if registry is not None:
                tools = [t.to_schema() for t in registry.list()]

        context.request = ChatRequest(
            messages=list(
                context.conversation.messages
            ),
            temperature=context.temperature,
            max_tokens=context.max_tokens,
            stream=context.mode == ExecutionMode.STREAM,
            timeout=context.stream_timeout,
            tools=tools,
        )

        return context