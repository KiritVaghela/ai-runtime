from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ai_runtime.agents import Agent
from ai_runtime.agents.modes import AgentMode
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers import ProviderConfig
from ai_runtime.providers.capabilities import ProviderCapabilities
from ai_runtime.server.agent_server import AgentServer
from ai_runtime.server.protocol import AgentRequest
from ai_runtime.tools.builtin import register_builtin_tools
from ai_runtime.tools import ToolRegistry, GuardedToolExecutor, PermissionPolicy
from ai_runtime.tools.executor import ToolExecutor
from ai_runtime.agents.config_files import load_project_instructions


def _build_agent(args, agent_mode: AgentMode = AgentMode.AGENT) -> Agent:
    config = ProviderConfig(
        provider=ProviderType(args.provider),
        model=args.model,
        api_key=os.getenv(args.api_key_env),
        reasoning_effort=args.reasoning_effort,
    )
    # Ask/Plan modes run without tools; Agent mode gets the full registry.
    if agent_mode.uses_tools:
        registry = ToolRegistry()
        register_builtin_tools(registry, base_dir=args.cwd)
    else:
        registry = None
    executor = GuardedToolExecutor(
        ToolExecutor(registry) if registry is not None else None,
        PermissionPolicy.permissive() if args.yolo else PermissionPolicy.default(),
    )
    return Agent(
        name="cli-agent",
        provider=config,
        system_prompt=load_project_instructions(args.cwd),
        tool_registry=registry,
        agent_mode=agent_mode,
    )


async def _run(args) -> None:
    amode = _normalize_mode(args.mode)
    agent = _build_agent(args, amode)
    server = AgentServer(agent)
    # Resolve the low-level transport from the agent mode + provider capabilities.
    transport = amode.transport_mode(ProviderCapabilities())
    req = AgentRequest(session_id="cli", message=args.prompt, mode=transport)
    if transport == "stream":
        async for line in server.stream(req):
            sys.stdout.write(line)
    else:
        resp = await server.handle(req)
        print(resp.content)


def _normalize_mode(mode: str) -> AgentMode:
    try:
        return AgentMode(mode)
    except ValueError:
        return AgentMode.AGENT


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-runtime", description="ai_runtime agent CLI")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument("--provider", default="openai", help="Provider type")
    parser.add_argument("--model", required=True, help="Model id")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY", help="Env var with API key")
    parser.add_argument("--mode", default="agent", choices=["ask", "plan", "agent"])
    parser.add_argument("--cwd", default=os.getcwd(), help="Project root / sandbox dir")
    parser.add_argument("--reasoning-effort", default=None, help="low|medium|high")
    parser.add_argument("--yolo", action="store_true", help="Allow all tools without prompting")
    parser.add_argument("--serve", action="store_true", help="Start stdio server")
    parser.add_argument("--http", action="store_true", help="Start HTTP server")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    if args.serve:
        agent = _build_agent(args, _normalize_mode(args.mode))
        asyncio.run(AgentServer(agent).serve_stdio())
    elif args.http:
        agent = _build_agent(args, _normalize_mode(args.mode))
        asyncio.run(AgentServer(agent).serve_http(port=args.port))
    elif args.prompt:
        asyncio.run(_run(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
