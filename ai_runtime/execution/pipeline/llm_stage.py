from .stage import ExecutionStage
from ..context import ExecutionContext
from ..mode import ExecutionMode
from ..hooks import HookEvent, HookContext


class LLMStage(ExecutionStage):

    async def execute(
        self,
        context: ExecutionContext,
    ):

        if context.request is None:
            raise RuntimeError(
                "RequestBuilderStage must execute first."
            )

        # PreLLM hook: may patch the request or short-circuit.
        if context.hooks is not None:
            res = await context.hooks.trigger(
                HookContext(event=HookEvent.PRE_LLM, agent=context.agent)
            )
            if not res.continue_:
                return context
            if "request" in res.patch:
                context.request = res.patch["request"]

        if context.mode == ExecutionMode.CHAT:

            context.response = await context.provider.chat(
                context.request
            )

        else:

            context.stream = context.provider.stream(
                context.request
            )

        # PostLLM hook: may observe/annotate the response.
        if context.hooks is not None and context.mode == ExecutionMode.CHAT:
            await context.hooks.trigger(
                HookContext(
                    event=HookEvent.POST_LLM,
                    agent=context.agent,
                    message=context.response.message if context.response else None,
                )
            )

        return context