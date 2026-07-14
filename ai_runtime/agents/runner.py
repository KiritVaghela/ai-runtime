from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_runtime.conversation import ChatMessage, ChatRequest
from ai_runtime.execution.plan import Plan
from ai_runtime.streaming import StreamEvent

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

    def __init__(self, agent: Agent, engine: ExecutionEngine | None = None):
        if engine is None:
            from ai_runtime.execution import ExecutionEngine

            engine = ExecutionEngine()
        self.agent = agent
        self.engine = engine

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

        # Persist the new turns (exclude the prepended system prompt).
        if prompt:
            persisted = context.conversation.copy()
            persisted.messages = persisted.messages[1:]
            self.agent.memory._conversation = persisted
        else:
            self.agent.memory._conversation = context.conversation.copy()
        await self.agent.memory.save()

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

        await self.agent.memory.save()

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
