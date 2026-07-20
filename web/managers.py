from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
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
from ai_runtime.conversation import ChatMessage
from ai_runtime.conversation.enums import MessageRole
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
    # Per-session provider settings (fall back to Manager.config when unset).
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    reasoning_effort: str | None = None
    thinking_enabled: bool = False
    pinned: bool = False
    commands: CommandRegistry = field(default_factory=default_commands)
    history: list[dict[str, Any]] = field(default_factory=list)
    # Active WebSocket connection (set when the client connects) so the
    # permission prompt can be pushed to the right client during a stream.
    ws: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
        # Pending human-in-the-loop permission requests, keyed by request id.
        # Each entry holds an asyncio.Future resolved when the user answers.
        self._permission_requests: dict[str, Any] = {}
        # Restore any persisted provider settings from a local file.
        self._load_provider_store()
        # Restore persisted sessions (metadata + chat history).
        self._load_sessions()
        self._register_default_hooks()

    # ---- Permission prompts (human-in-the-loop) ----
    def create_permission_request(self, session_id: str, tool: str, params: str) -> tuple[str, "asyncio.Future[bool]"]:
        """Register a pending permission request and return (request_id, future).

        The future resolves to True (approved) or False (denied) when the
        user answers via the WebSocket `permission_response` action.
        """
        import asyncio

        request_id = uuid.uuid4().hex[:12]
        future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        self._permission_requests[request_id] = {
            "session_id": session_id,
            "future": future,
            "tool": tool,
            "params": params,
        }
        return request_id, future

    def resolve_permission_request(self, request_id: str, approved: bool) -> bool:
        """Resolve a pending permission request from a user answer."""
        pending = self._permission_requests.pop(request_id, None)
        if pending is None:
            return False
        if not pending["future"].done():
            pending["future"].set_result(approved)
        return True

    # ---- Provider persistence ----
    @property
    def _provider_store_path(self) -> Path:
        base = Path(self.config.default_project_root or Path.cwd())
        return base / ".ai-runtime" / "provider.json"

    def _load_provider_store(self) -> None:
        """Load saved provider settings (if any) and apply to config."""
        path = self._provider_store_path
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            return
        for key in ("provider", "model", "api_key", "base_url", "reasoning_effort"):
            if data.get(key) is not None:
                setattr(self.config, key, data[key])

    def _save_provider_store(self) -> None:
        """Persist the current provider settings to a local JSON file."""
        path = self._provider_store_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "provider": self.config.provider,
                        "model": self.config.model,
                        "api_key": self.config.api_key,
                        "base_url": self.config.base_url,
                        "reasoning_effort": self.config.reasoning_effort,
                    },
                    indent=2,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not persist provider settings to %s", path)

    # ---- Session persistence ----
    @property
    def _sessions_dir(self) -> Path:
        base = Path(self.config.default_project_root or Path.cwd())
        return base / ".ai-runtime" / "sessions"

    def _save_session(self, session: Session) -> None:
        """Persist a session's metadata + chat history to a local JSON file.

        Sessions with no messages yet are not written — a session file only
        appears once the user has actually sent a message.
        """
        if not session.history:
            return
        try:
            self._sessions_dir.mkdir(parents=True, exist_ok=True)
            path = self._sessions_dir / f"{session.id}.json"
            path.write_text(
                json.dumps(
                    {
                        "id": session.id,
                        "name": session.name,
                        "named": session.named,
                        "mode": session.mode,
                        "provider": session.provider,
                        "model": session.model,
                        "api_key": session.api_key,
                        "base_url": session.base_url,
                        "reasoning_effort": session.reasoning_effort,
                        "thinking_enabled": session.thinking_enabled,
                        "pinned": session.pinned,
                        "history": session.history,
                    },
                    indent=2,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not persist session %s", session.id)

    def _load_sessions(self) -> None:
        """Restore persisted sessions (metadata + history) on startup."""
        import asyncio

        d = self._sessions_dir
        if not d.exists():
            return
        for path in sorted(d.glob("*.json")):
            try:
                data = json.loads(path.read_text())
            except Exception:  # noqa: BLE001
                continue
            sid = data.get("id")
            if not sid or sid in self.sessions:
                continue
            project = self.projects.get(data.get("project") or "default")
            if project is None:
                project = self.create_project(
                    self.config.default_project_root, data.get("project") or "default"
                )
            try:
                agent = self._build_agent(
                    project,
                    None,
                    data.get("provider"),
                    data.get("model"),
                    data.get("api_key"),
                    data.get("base_url"),
                    data.get("reasoning_effort"),
                    data.get("thinking_enabled", False),
                    session_id=sid,
                )
            except Exception:  # noqa: BLE001
                logger.warning("Skipping persisted session %s (provider build failed)", sid)
                continue
            runner = AgentRunner(agent)
            session = Session(
                id=sid,
                project=project,
                agent=agent,
                runner=runner,
                name=data.get("name", "New chat"),
                named=data.get("named", False),
                mode=data.get("mode", "chat"),
                provider=data.get("provider"),
                model=data.get("model"),
                api_key=data.get("api_key"),
                base_url=data.get("base_url"),
                reasoning_effort=data.get("reasoning_effort"),
                thinking_enabled=data.get("thinking_enabled", False),
                pinned=data.get("pinned", False),
                history=data.get("history", []),
            )
            self.sessions[sid] = session
            # Rebuild the in-memory conversation from the persisted history so
            # commands like /context report accurate counts for sessions that
            # were restored from disk (their memory starts empty otherwise).
            self._rebuild_conversation_from_history(session)

    def _rebuild_conversation_from_history(self, session: "Session") -> None:
        """Populate ``agent.memory._conversation`` from ``session.history``.

        Live turns append to both ``history`` and the agent's memory, but
        sessions restored from disk only carry ``history``. Without this, the
        memory-backed conversation is empty and context commands report 0
        messages for pre-existing sessions.
        """
        role_map = {
            "user": MessageRole.USER,
            "text": MessageRole.ASSISTANT,
            "assistant": MessageRole.ASSISTANT,
            "system": MessageRole.SYSTEM,
            "tool": MessageRole.TOOL,
        }
        messages = []
        for entry in session.history:
            if not isinstance(entry, dict):
                continue
            etype = entry.get("type") or entry.get("role")
            # ``plan`` entries are UI-only and not part of the LLM conversation.
            if etype in ("plan",):
                continue
            role = role_map.get(etype)
            if role is None:
                continue
            content = entry.get("content")
            if not content:
                continue
            messages.append(ChatMessage(role=role, content=content))
        session.agent.memory._conversation.messages = messages

    # ---- Projects ----

    def create_project(self, root: str, name: str | None = None) -> Project:
        proj = Project(root=root, name=name)
        proj.install_builtin_tools()
        self.projects[proj.name] = proj
        return proj

    def get_project(self, name: str) -> Project | None:
        return self.projects.get(name)

    # ---- Agents / Sessions ----

    def _build_agent(
        self,
        project: Project,
        system_prompt: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        reasoning_effort: str | None = None,
        thinking_enabled: bool = False,
        session_id: str | None = None,
    ) -> Agent:
        # Per-session provider settings override the global config default.
        provider = provider or self.config.provider
        model = model or self.config.model
        api_key = api_key if api_key is not None else self.config.api_key
        base_url = base_url if base_url is not None else self.config.base_url
        reasoning_effort = (
            reasoning_effort if reasoning_effort is not None else self.config.reasoning_effort
        )
        # Per-session thinking flag overrides the global config default.
        if thinking_enabled is None:
            thinking_enabled = self.config.thinking_enabled
        # Build a real provider instance (not just a config) via the registry.
        cfg = ProviderConfig(
            provider=ProviderType(provider),
            model=model,
            api_key=api_key,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
            thinking_enabled=thinking_enabled,
        )
        try:
            provider = self.registry.create(cfg)
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to create provider for %s", self.config.provider)
            raise RuntimeError(f"Provider creation failed: {e}") from e

        # Guarded executor enforces the project's permission policy.
        # When the policy says ASK, pause and prompt the user over the
        # WebSocket (human-in-the-loop) instead of failing silently.
        base_executor = (
            project.tool_registry.executor
            if hasattr(project.tool_registry, "executor")
            else __import__("ai_runtime.tools.executor", fromlist=["ToolExecutor"]).ToolExecutor(
                project.tool_registry
            )
        )

        def _make_on_ask(sid: str | None):
            if sid is None:
                return None

            async def _on_ask(tool_name: str, param_str: str) -> bool:
                request_id, future = self.create_permission_request(
                    sid, tool_name, param_str
                )
                # Push the permission prompt to the client over its WebSocket.
                sess = self.sessions.get(sid)
                if sess is not None and sess.ws is not None:
                    try:
                        from ai_runtime.streaming import PermissionEvent

                        await sess.ws.send_text(
                            PermissionEvent(
                                request_id=request_id,
                                action=f"{tool_name}({param_str})",
                                detail={"tool": tool_name, "params": param_str},
                            ).model_dump_json()
                        )
                    except Exception:  # noqa: BLE001
                        logger.exception("Failed to send permission prompt for %s", sid)
                # Await the user's answer (resolved by the WebSocket handler
                # when it receives the `permission_response` action).
                try:
                    return await future
                except Exception:  # noqa: BLE001
                    return False

            return _on_ask

        executor = GuardedToolExecutor(
            base_executor,
            project.permission_policy,
            on_ask=_make_on_ask(session_id),
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
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        reasoning_effort: str | None = None,
        thinking_enabled: bool = False,
        mode: str = "chat",
    ) -> Session:
        project = self.projects.get(project_name)
        if project is None:
            project = self.create_project(self.config.default_project_root, project_name)
        # Generate the session id first so the guarded executor can route
        # permission prompts back to this exact WebSocket session.
        session_id = uuid.uuid4().hex[:12]
        agent = self._build_agent(
            project, system_prompt, provider, model, api_key, base_url,
            reasoning_effort, thinking_enabled, session_id=session_id,
        )
        runner = AgentRunner(agent)
        session = Session(
            id=session_id,
            project=project,
            agent=agent,
            runner=runner,
            name=name or "New chat",
            named=name is not None,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
            thinking_enabled=thinking_enabled,
            mode=mode if mode in ("chat", "plan") else "chat",
        )
        self.sessions[session.id] = session
        self._save_session(session)
        return session

    def rename_session(self, session_id: str, name: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.name = name
        session.named = True
        self._save_session(session)
        return session

    def pin_session(self, session_id: str, pinned: bool) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.pinned = bool(pinned)
        self._save_session(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        """Remove a session from memory and delete its persisted file."""
        session = self.sessions.pop(session_id, None)
        if session is None:
            return False
        try:
            path = self._sessions_dir / f"{session_id}.json"
            if path.exists():
                path.unlink()
        except Exception:  # noqa: BLE001
            logger.warning("Could not delete session file %s", session_id)
        return True

    def set_session_mode(self, session_id: str, mode: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if mode not in ("chat", "plan"):
            mode = "chat"
        session.mode = mode
        self._save_session(session)
        return session

    def set_session_settings(
        self,
        session_id: str,
        reasoning_effort: str | None = None,
        thinking_enabled: bool | None = None,
    ) -> Session | None:
        """Update a session's reasoning effort / thinking flag and rebuild its agent."""
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if reasoning_effort is not None:
            if reasoning_effort not in ("low", "medium", "high"):
                reasoning_effort = None
            session.reasoning_effort = reasoning_effort
        if thinking_enabled is not None:
            session.thinking_enabled = bool(thinking_enabled)
        # Rebuild the agent so the provider config reflects the new settings.
        new_agent = self._build_agent(
            session.project,
            session.agent.system_prompt,
            session.provider,
            session.model,
            session.api_key,
            session.base_url,
            session.reasoning_effort,
            session.thinking_enabled,
            session_id=session.id,
        )
        session.agent.provider = new_agent.provider
        session.agent.tool_executor = new_agent.tool_executor
        self._save_session(session)
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

        # Persist so the setting survives server / web-app restarts.
        self._save_provider_store()

        # Rebuild the provider for each existing session's agent in place,
        # preserving each session's own effort / thinking settings.
        for session in self.sessions.values():
            new_agent = self._build_agent(
                session.project,
                session.agent.system_prompt,
                session.provider,
                session.model,
                session.api_key,
                session.base_url,
                session.reasoning_effort,
                session.thinking_enabled,
                session_id=session.id,
            )
            session.agent.provider = new_agent.provider
            session.agent.tool_executor = new_agent.tool_executor
            self._save_session(session)

    def get_provider_capabilities(self) -> dict:
        """Return the active provider's advertised capabilities (for the UI)."""
        try:
            provider_type = ProviderType(self.config.provider)
            cls = self.registry.get(provider_type)
            provider = cls(ProviderConfig(provider=provider_type, model=self.config.model))
            return provider.info.capabilities.model_dump()
        except Exception:  # noqa: BLE001
            return {}

    def get_session(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    # ---- Sub-agents ----

    def add_subagent(self, session: Session, spec: SubAgentSpec) -> None:
        session.agent.sub_agents.append(spec)

    # ---- Built-in agents / skills / commands ----
    #
    # The web app exposes the framework's built-in presets (v0.8.1) so users
    # can run a reviewer/explain/tester agent, apply a skill to a session, or
    # invoke a categorized slash command — all driven from the UI.

    def list_builtin_agents(self) -> list[dict[str, Any]]:
        """Catalog of built-in agent presets the UI can instantiate."""
        return [
            {"key": "reviewer", "name": "Code Reviewer", "description": "Senior reviewer that critiques changes for correctness and risks."},
            {"key": "explainer", "name": "Explainer", "description": "Explains code and concepts clearly with examples."},
            {"key": "tester", "name": "Test Writer", "description": "Generates focused, runnable unit tests."},
            {"key": "summarizer", "name": "Summarizer", "description": "Condenses conversations and transcripts."},
            {"key": "router", "name": "Router", "description": "Intent dispatcher that routes work to review/explain/test specialists."},
            {"key": "critic", "name": "Self-Critic", "description": "Reflexion loop that self-reviews generated output before returning."},
        ]

    def list_builtin_skills(self) -> list[dict[str, Any]]:
        """Catalog of built-in skills the UI can compose into a session."""
        from ai_runtime.skills.builtin import default_builtin_skills

        return [
            {"name": s.name, "description": s.description, "category": getattr(s, "category", "general")}
            for s in default_builtin_skills()
        ]

    def list_builtin_commands(self) -> list[dict[str, Any]]:
        """Catalog of built-in slash commands (categorized)."""
        from ai_runtime.commands import default_commands

        return [
            {"name": c.name, "description": c.description, "category": c.category, "args": c.args, "example": c.example}
            for c in default_commands().list()
        ]

    def apply_skill(self, session: Session, skill_name: str) -> dict[str, Any]:
        """Compose a built-in skill into the session's agent system prompt.

        The skill's system prompt is appended to the agent's prompt so the
        capability is active for the rest of the session.
        """
        from ai_runtime.skills.builtin import default_builtin_skills

        skill = next((s for s in default_builtin_skills() if s.name == skill_name), None)
        if skill is None:
            raise KeyError(f"Unknown built-in skill: {skill_name}")
        base = session.agent.system_prompt or ""
        if skill.system_prompt and skill.system_prompt not in base:
            session.agent.system_prompt = (base + "\n\n" + skill.system_prompt).strip()
        # Track applied skills so the UI can show active capabilities.
        applied = session.metadata.setdefault("skills", [])
        if skill_name not in applied:
            applied.append(skill_name)
        self._save_session(session)
        return {"ok": True, "skill": skill_name, "active_skills": applied}

    def set_self_review(self, session: Session, enabled: bool) -> dict[str, Any]:
        """Toggle the agentic self-review (reflexion) pass for a session."""
        session.runner.self_review = bool(enabled)
        session.metadata["self_review"] = bool(enabled)
        self._save_session(session)
        return {"ok": True, "self_review": bool(enabled)}

    async def run_builtin_agent(self, session: Session, agent_key: str, task: str) -> dict[str, Any]:
        """Run a built-in agent preset against `task`, returning its output.

        For `router`/`critic` the framework's higher-level agents are used;
        for the specialist presets a single `AgentRunner` run is performed.
        """
        from ai_runtime.agents.builtin import (
            reviewer_agent,
            explainer_agent,
            tester_agent,
            summarizer_agent,
            critic_agent,
            router_agent,
        )

        provider = session.agent.provider
        if agent_key == "reviewer":
            agent = reviewer_agent(provider)
        elif agent_key == "explainer":
            agent = explainer_agent(provider)
        elif agent_key == "tester":
            agent = tester_agent(provider)
        elif agent_key == "summarizer":
            agent = summarizer_agent(provider)
        elif agent_key == "critic":
            result = await critic_agent(provider).run(task)
            return {"agent": agent_key, "output": result.output, "approved": result.approved, "iterations": result.iterations}
        elif agent_key == "router":
            result = await router_agent(provider).run(task)
            return {"agent": agent_key, "output": result.message.content or ""}
        else:
            raise KeyError(f"Unknown built-in agent: {agent_key}")

        from ai_runtime.agents import AgentRunner

        resp = await AgentRunner(agent).run(task)
        return {"agent": agent_key, "output": resp.message.content or ""}

    async def run_builtin_command(self, session: Session, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a categorized built-in command against the session.

        Commands that need a target (review/explain/test/workflow) render their
        template with the supplied args and run it through the session's own
        runner so the result streams into the conversation like a normal turn.
        """
        args = args or {}
        rendered = session.commands.render(name, **args)
        if rendered is None:
            raise KeyError(f"Unknown command: {name}")
        # General commands handled directly by the route; here we run the
        # agentic ones (review/explain/test/workflow) as a chat turn.
        response = await session.runner.run(rendered)
        return {"command": name, "prompt": rendered, "output": response.message.content or ""}

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
