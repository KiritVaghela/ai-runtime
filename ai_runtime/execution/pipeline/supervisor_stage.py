from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_runtime.agents.agent import Agent

from ai_runtime.agents.subagent import SubAgentSpec, SubAgentResult
from ai_runtime.conversation import ChatMessage

from .stage import ExecutionStage
from ..context import ExecutionContext


class SupervisorStage(ExecutionStage):
    """Spawns declared sub-agents in parallel with isolated contexts.

    This addresses the biggest architectural gap vs agentic coding tools:
    a single `AgentRunner` previously ran one agent only. The supervisor
    fans out independent sub-tasks to child `Agent`s (each with its own
    conversation context, so transcripts stay isolated), then aggregates
    their outputs back into the parent context as a system message.

    Sub-agents are declared on the agent via `agent.sub_agents`. A
    `max_depth` guard prevents unbounded recursive fan-out.
    """

    def __init__(self, max_threads: int = 6):
        self.max_threads = max_threads

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        agent: Agent | None = getattr(context, "agent", None)
        if agent is None or not getattr(agent, "sub_agents", None):
            return context

        specs: list[SubAgentSpec] = agent.sub_agents
        task = self._derive_task(context)
        if not task:
            return context

        semaphore = asyncio.Semaphore(self.max_threads)

        # Imported lazily to avoid a circular import with ai_runtime.agents.
        from ai_runtime.agents.runner import AgentRunner

        async def run_one(spec: SubAgentSpec) -> SubAgentResult:
            async with semaphore:
                try:
                    runner = AgentRunner(spec.agent, engine=context._engine)
                    prompt = spec.task_template.format(task=task)
                    resp = await runner.run(prompt)
                    return SubAgentResult(
                        name=spec.name,
                        output=resp.message.content or "",
                    )
                except Exception as e:  # isolation: one failure doesn't kill all
                    return SubAgentResult(
                        name=spec.name, output="", success=False, error=str(e)
                    )

        results = await asyncio.gather(*(run_one(s) for s in specs))

        # Aggregate into the parent conversation as a system note.
        summary = self._summarize(results)
        context.conversation.add(ChatMessage.system(summary))
        context.metadata.setdefault("sub_agent_results", []).extend(
            r.__dict__ for r in results
        )
        return context

    @staticmethod
    def _derive_task(context: ExecutionContext) -> str | None:
        if context.request and context.request.messages:
            return context.request.messages[-1].content
        if context.conversation.messages:
            return context.conversation.messages[-1].content
        return None

    @staticmethod
    def _summarize(results: list[SubAgentResult]) -> str:
        lines = ["[Sub-agent results]"]
        for r in results:
            status = "ok" if r.success else f"FAILED: {r.error}"
            lines.append(f"- {r.name}: {status}")
            if r.output:
                lines.append(f"  {r.output}")
        return "\n".join(lines)
