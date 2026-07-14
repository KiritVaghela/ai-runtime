from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from ai_runtime.agents import Agent, AgentRunner
from ai_runtime.agents.subagent import SubAgentSpec
from ai_runtime.providers import ProviderConfig, ProviderRegistry
from ai_runtime.providers.default_registry import create_default_registry
from ai_runtime.providers.enums import ProviderType
from ai_runtime.tools import ToolRegistry, PermissionPolicy, PermissionRule, PermissionDecision
from ai_runtime.tools.builtin import register_builtin_tools
from ai_runtime.tools.guarded_executor import GuardedToolExecutor
from ai_runtime.tools.checkpoints import CheckpointManager
from ai_runtime.workspace import Project
from ai_runtime.commands import default_commands, CommandRegistry
from ai_runtime.execution.background import BackgroundTaskRegistry
from ai_runtime.execution.hooks import HookRegistry, HookEvent, HookContext, HookResult

import logging

from .config import WebConfig

logger = logging.getLogger("ai_runtime.web")


@dataclass
class Session:
    """A chat session bound to a project + agent."""

    id: str
    project: Project
    agent: Agent
    runner: AgentRunner
    name: str = "New chat"
    named: bool = False
    mode: str = "chat"  # chat | plan — per-session
    commands: CommandRegistry = field(default_factory=default_commands)
    history: list[dict[str, Any]] = field(default_factory=list)


class Manager:
    """In-memory registry of projects, agents, and sessions for the web app.

    This is the server-side state that the browser UI drives. Each session
    owns a `Project` (scoped tools/memory/permissions) and an `AgentRunner`.
    """

    def __init__(self, config: WebConfig):
        self.config = config
        self.registry = create_default_registry()
        self.projects: dict[str, Project] = {}
        self.sessions: dict[str, Session] = {}
        self.background = BackgroundTaskRegistry()
        self.hooks = HookRegistry()
        self._register_default_hooks()

    # ---- Projects ----

    def create_project(self, root: str, name: str | None = None) -> Project:
        proj = Project(root=root, name=name)
        proj.install_builtin_tools()
        self.projects[proj.name] = proj
        return proj

    def get_project(self, name: str) -> Project | None:
        return self.projects.get(name)

    # ---- Agents / Sessions ----

    def _build_agent(self, project: Project, system_prompt: str | None = None) -> Agent:
        # Build a real provider instance (not just a config) via the registry.
        cfg = ProviderConfig(
            provider=ProviderType(self.config.provider),
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            reasoning_effort=self.config.reasoning_effort,
        )
        try:
            provider = self.registry.create(cfg)
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to create provider for %s", self.config.provider)
            raise RuntimeError(f"Provider creation failed: {e}") from e

        # Guarded executor enforces the project's permission policy.
        executor = GuardedToolExecutor(
            project.tool_registry.executor
            if hasattr(project.tool_registry, "executor")
            else __import__("ai_runtime.tools.executor", fromlist=["ToolExecutor"]).ToolExecutor(
                project.tool_registry
            ),
            project.permission_policy,
        )
        agent = Agent(
            name=f"{project.name}-agent",
            provider=provider,
            system_prompt=project.as_system_prompt(system_prompt),
            tool_registry=project.tool_registry,
            memory_store=project.memory_store,
        )
        agent.tool_executor = executor
        return agent

    def create_session(
        self,
        project_name: str,
        system_prompt: str | None = None,
        name: str | None = None,
    ) -> Session:
        project = self.projects.get(project_name)
        if project is None:
            project = self.create_project(self.config.default_project_root, project_name)
        agent = self._build_agent(project, system_prompt)
        runner = AgentRunner(agent)
        session = Session(
            id=uuid.uuid4().hex[:12],
            project=project,
            agent=agent,
            runner=runner,
            name=name or "New chat",
            named=name is not None,
        )
        self.sessions[session.id] = session
        return session

    def rename_session(self, session_id: str, name: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.name = name
        session.named = True
        return session

    def set_session_mode(self, session_id: str, mode: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if mode not in ("chat", "plan"):
            mode = "chat"
        session.mode = mode
        return session

    def set_provider(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        """Switch the active LLM backend and rebuild every session's agent."""
        self.config.provider = provider
        self.config.model = model
        if api_key is not None:
            self.config.api_key = api_key
        if base_url is not None:
            self.config.base_url = base_url
        if reasoning_effort is not None:
            self.config.reasoning_effort = reasoning_effort

        # Rebuild the provider for each existing session's agent in place.
        for session in self.sessions.values():
            new_agent = self._build_agent(session.project, session.agent.system_prompt)
            session.agent.provider = new_agent.provider
            session.agent.tool_executor = new_agent.tool_executor

    def get_session(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    # ---- Sub-agents ----

    def add_subagent(self, session: Session, spec: SubAgentSpec) -> None:
        session.agent.sub_agents.append(spec)

    # ---- Permissions ----

    def set_permission_rule(
        self, project_name: str, tool: str, params: str, decision: str
    ) -> None:
        project = self.projects.get(project_name)
        if project is None:
            return
        project.permission_policy.rules.append(
            PermissionRule(tool, params, PermissionDecision(decision))
        )

    # ---- Hooks ----

    def _register_default_hooks(self) -> None:
        # Log every tool call (observability hook).
        async def log_tool(ctx: HookContext) -> HookResult:
            return HookResult()

        self.hooks.register(HookEvent.POST_TOOL_USE, log_tool)
