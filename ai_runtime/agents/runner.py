from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_runtime.conversation import ChatMessage, ChatRequest
from ai_runtime.execution.plan import Plan
from ai_runtime.streaming import StreamEvent
from collections.abc import AsyncIterator

if TYPE_CHECKING:
    from ai_runtime.execution import ExecutionEngine

from ai_runtime.execution.context import ExecutionContext

from .agent import Agent


class AgentRunner:
    """Orchestrates agent execution over the runtime pipeline.

    For each `run`, the runner:
      1. Loads persisted conversation memory.
      2. Prepends the agent's (skill-composed) system prompt.
      3. Executes via `ExecutionEngine` (which includes the tool-call loop).
      4. Persists the updated conversation back to memory.
    """

    def __init__(
        self,
        agent: Agent,
        engine: ExecutionEngine | None = None,
        self_review: bool = False,
        compaction_summarizer: Any | None = None,
    ):
        if engine is None:
            from ai_runtime.execution import ExecutionEngine

            engine = ExecutionEngine()
        self.agent = agent
        self.engine = engine
        self.self_review = self_review
        self.compaction_summarizer = compaction_summarizer
        self.last_plan: Plan | None = None
        self.last_plan_text: str = ""

    async def run(
        self,
        message: str | ChatMessage | ChatRequest,
        system_prompt: str | None = None,
    ):
        await self.agent.ensure_memory_loaded()

        context = ExecutionContext(
            provider=self.agent.provider,
            tool_executor=self.agent.tool_executor,
        )
        context.agent = self.agent
        context._engine = self.engine

        # Seed conversation with system prompt + persisted history.
        prompt = system_prompt or self.agent.effective_system_prompt()
        if prompt:
            context.conversation.add(ChatMessage.system(prompt))
        for msg in self.agent.memory.conversation.messages:
            context.conversation.add(msg)

        if isinstance(message, str):
            user_msg = ChatMessage.user(message)
        elif isinstance(message, ChatMessage):
            user_msg = message
        else:
            user_msg = ChatMessage.user(message.messages[-1].content)

        response = await self.engine.chat(context, user_msg)

        # Optional self-review (reflexion) pass over the produced answer.
        if self.self_review:
            response = await self._apply_self_review(response, user_msg)

        # Persist the new turns (exclude the prepended system prompt).
        if prompt:
            persisted = context.conversation.copy()
            persisted.messages = persisted.messages[1:]
            self.agent.memory._conversation = persisted
        else:
            self.agent.memory._conversation = context.conversation.copy()
        await self.agent.memory.save()

        return response

    async def _apply_self_review(self, response, user_msg) -> Any:
        """Critique and improve the agent's answer before returning it.

        Uses a `CriticAgent` whose actor is this runner's agent and whose
        critic is a built-in `reviewer_agent`. This makes the runtime apply
        its own review capability to its own output.
        """
        from .builtin import reviewer_agent
        from .types import CriticAgent

        critic = CriticAgent(
            name="self-review",
            actor=self.agent,
            critic=reviewer_agent(self.agent.provider),
            max_iterations=2,
        )
        task = getattr(user_msg, "content", str(user_msg))
        candidate = getattr(response.message, "content", "") or ""
        # Feed the candidate as the task so the actor revises it directly.
        result = await critic.run(f"{task}\n\nDraft answer:\n{candidate}")
        if result.approved:
            response.message = ChatMessage.assistant(result.output)
        return response

    async def stream(
        self,
        message: str | ChatMessage | ChatRequest,
        system_prompt: str | None = None,
    ):
        await self.agent.ensure_memory_loaded()

        context = ExecutionContext(
            provider=self.agent.provider,
            tool_executor=self.agent.tool_executor,
        )
        context.agent = self.agent
        context._engine = self.engine

        prompt = system_prompt or self.agent.effective_system_prompt()
        if prompt:
            context.conversation.add(ChatMessage.system(prompt))
        for msg in self.agent.memory.conversation.messages:
            context.conversation.add(msg)

        if isinstance(message, str):
            user_msg = ChatMessage.user(message)
        elif isinstance(message, ChatMessage):
            user_msg = message
        else:
            user_msg = ChatMessage.user(message.messages[-1].content)

        async for event in self.engine.stream(context, user_msg):
            yield event

        # Optional self-review (reflexion) pass on the streamed answer.
        if self.self_review:
            draft = context.assistant_text or ""
            reviewed = await self._review_text(draft, user_msg)
            if reviewed is not None:
                context.assistant_text = reviewed
                # Surface the reviewed text as a final delta + completion.
                from ai_runtime.streaming import (
                    TextDeltaEvent,
                    CompletedEvent,
                )

                yield TextDeltaEvent(delta=reviewed)
                yield CompletedEvent(finish_reason=context.finish_reason)

        # Persist the new turns back into the agent's memory so commands
        # like /context and /compact see the up-to-date conversation. The
        # engine appends the prepended system prompt to context.conversation,
        # so strip it before storing (mirrors run()).
        if prompt:
            persisted = context.conversation.copy()
            persisted.messages = persisted.messages[1:]
            self.agent.memory._conversation = persisted
        else:
            self.agent.memory._conversation = context.conversation.copy()
        await self.agent.memory.save()

    async def _review_text(self, draft: str, user_msg) -> str | None:
        """Self-review a streamed draft; return reviewed text or None."""
        if not draft:
            return None
        from .builtin import reviewer_agent
        from .types import CriticAgent

        critic = CriticAgent(
            name="self-review",
            actor=self.agent,
            critic=reviewer_agent(self.agent.provider),
            max_iterations=2,
        )
        task = getattr(user_msg, "content", str(user_msg))
        result = await critic.run(f"{task}\n\nDraft answer:\n{draft}")
        return result.output if result.approved else None

    async def plan(
        self,
        message: str | ChatMessage | ChatRequest,
        system_prompt: str | None = None,
    ) -> Plan:
        """Produce a reviewable plan for the agent without executing tools."""
        await self.agent.ensure_memory_loaded()

        context = ExecutionContext(
            provider=self.agent.provider,
            tool_executor=self.agent.tool_executor,
        )

        prompt = system_prompt or self.agent.effective_system_prompt()
        if prompt:
            context.conversation.add(ChatMessage.system(prompt))
        for msg in self.agent.memory.conversation.messages:
            context.conversation.add(msg)

        if isinstance(message, str):
            user_msg = ChatMessage.user(message)
        elif isinstance(message, ChatMessage):
            user_msg = message
        else:
            user_msg = ChatMessage.user(message.messages[-1].content)

        return await self.engine.plan(context, user_msg)

    async def stream_plan(
        self,
        message: str | ChatMessage | ChatRequest,
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a plan (live thinking + placeholder, then the parsed plan).

        The planner parses the model's JSON into a `Plan` during streaming, so
        no second LLM call is needed — the parsed plan is available on
        `self.last_plan` afterwards.
        """
        await self.agent.ensure_memory_loaded()

        context = ExecutionContext(
            provider=self.agent.provider,
            tool_executor=self.agent.tool_executor,
        )
        context.agent = self.agent
        context._engine = self.engine

        prompt = system_prompt or self.agent.effective_system_prompt()
        if prompt:
            context.conversation.add(ChatMessage.system(prompt))
        for msg in self.agent.memory.conversation.messages:
            context.conversation.add(msg)

        if isinstance(message, str):
            user_msg = ChatMessage.user(message)
        elif isinstance(message, ChatMessage):
            user_msg = message
        else:
            user_msg = ChatMessage.user(message.messages[-1].content)

        async for event in self.engine.stream_plan(context, user_msg):
            yield event
        # Capture the parsed plan and the raw streamed text produced during
        # streaming, so the transport can echo back exactly what was shown.
        self.last_plan = context.plan
        self.last_plan_text = context.assistant_text
