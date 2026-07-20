from __future__ import annotations


from ai_runtime.memory import MemoryStore, InMemoryStore, ConversationMemory
from ai_runtime.skills import SkillRegistry, ComposedSkills
from ai_runtime.tools import ToolRegistry, ToolExecutor
from .subagent import SubAgentSpec


class Agent:
    """A configured agent: provider + system prompt + tools + memory + skills.

    An `Agent` is a declarative specification. Execution is performed by
    `AgentRunner`, which wires the agent's pieces into the runtime's
    execution pipeline (including the tool-call loop).
    """

    def __init__(
        self,
        name: str,
        provider,
        system_prompt: str | None = None,
        tool_registry: ToolRegistry | None = None,
        memory_store: MemoryStore | None = None,
        skill_registry: SkillRegistry | None = None,
        skills: list[str] | None = None,
        memory: ConversationMemory | None = None,
        sub_agents: list[SubAgentSpec] | None = None,
    ):
        self.name = name
        self.provider = provider
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry or ToolRegistry()
        self.tool_executor = ToolExecutor(self.tool_registry)
        self.memory_store = memory_store or InMemoryStore()
        self.memory = memory or ConversationMemory(self.memory_store, name)
        self.skill_registry = skill_registry
        self.skills: ComposedSkills | None = None
        if skill_registry is not None and skills:
            self.skills = skill_registry.compose(skills)
        self.sub_agents = sub_agents or []

    def effective_system_prompt(self) -> str | None:
        """Combine the agent prompt with any composed skill prompts."""
        parts: list[str] = []
        if self.system_prompt:
            parts.append(self.system_prompt)
        if self.skills is not None and self.skills.system_prompt:
            parts.append(self.skills.system_prompt)
        return "\n\n".join(parts) if parts else None

    def effective_tool_names(self) -> list[str]:
        if self.skills is None:
            return list(self.tool_registry._tools.keys())
        return self.skills.tool_names or list(
            self.tool_registry._tools.keys()
        )

    async def ensure_memory_loaded(self) -> None:
        await self.memory.load()
