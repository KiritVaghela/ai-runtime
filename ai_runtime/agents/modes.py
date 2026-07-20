from __future__ import annotations

from enum import Enum

from ai_runtime.providers.capabilities import ProviderCapabilities


class AgentMode(str, Enum):
    """High-level agent modes the user selects in the UI / CLI.

    Each mode maps to a low-level :class:`ExecutionMode` (chat/stream/plan)
    plus a capability profile:

    * ``ASK``   — simple query/answer, no tools. Uses stream (or chat
      fallback). Mirrors a plain chat completion.
    * ``PLAN``  — read-only planning. Uses plan mode; no execution, no tools.
    * ``AGENT`` — full agent: stream (or chat fallback) with all capabilities
      (tools, sub-agents, skills, hooks, permissions) enabled by default.
    """

    ASK = "ask"
    PLAN = "plan"
    AGENT = "agent"

    @property
    def uses_tools(self) -> bool:
        """Whether this mode exposes tools to the model."""
        return self is AgentMode.AGENT

    @property
    def execution_mode(self) -> str:
        """The low-level execution mode this agent mode maps to."""
        if self is AgentMode.PLAN:
            return "plan"
        return "stream"  # resolved to chat at runtime if unsupported

    def transport_mode(self, capabilities: ProviderCapabilities | None) -> str:
        """Resolve the actual transport (stream/chat) for this agent mode.

        Stream is used when the provider supports it; otherwise chat. Plan
        mode always uses its own plan transport regardless of streaming.
        """
        if self is AgentMode.PLAN:
            return "plan"
        if capabilities is not None and not capabilities.streaming:
            return "chat"
        return "stream"


# Backwards-compatible alias used by the web/CLI layer.
AGENT_MODES = [m.value for m in AgentMode]
