from __future__ import annotations

from typing import Any

from ai_runtime.conversation import Conversation

from .agent import Agent
from .builtin import summarizer_agent
from .types import CriticAgent


# ---------------------------------------------------------------------------
# Self-agentic wiring
#
# Helpers that turn the framework *into* a more agentic system by using its
# own agents/skills on itself: an LLM-based conversation summarizer for
# compaction, and a self-review (reflexion) pass applied to agent output.
# ---------------------------------------------------------------------------


async def agentic_summarize(conversation: Conversation, provider: Any) -> str:
    """Summarize a conversation using a `summarizer_agent` (LLM-backed).

    Used as the `summarizer` for `CompactionStage` so compaction is done by
    the runtime's own agent rather than a naive drop. Falls back to a plain
    transcript slice if the provider call fails.
    """
    try:
        transcript = "\n".join(
            f"{m.role.value}: {m.content}" for m in conversation.messages
        )
        agent = summarizer_agent(provider)
        from .runner import AgentRunner

        resp = await AgentRunner(agent).run(
            f"Summarize this conversation:\n\n{transcript}"
        )
        return resp.message.content or transcript
    except Exception:
        # Best-effort: return the most recent messages as a crude summary.
        return "\n".join(
            f"{m.role.value}: {m.content}"
            for m in conversation.messages[-8:]
        )


def make_agentic_compaction_summarizer(provider: Any):
    """Return a `summarizer` callable bound to `agentic_summarize`."""

    async def _summarize(conversation: Conversation) -> str:
        return await agentic_summarize(conversation, provider)

    return _summarize


def make_self_reviewer(provider: Any, max_iterations: int = 2) -> CriticAgent:
    """Build a `CriticAgent` that self-reviews an actor's output.

    The actor is the agent being run; the critic is a `reviewer_agent`. This
    is what `AgentRunner` uses when `self_review=True` to apply a reflexion
    pass before returning.
    """
    return CriticAgent(
        name="self-reviewer",
        actor=summarizer_agent(provider),  # placeholder; replaced per-run
        critic=reviewer_agent(provider),
        max_iterations=max_iterations,
    )
