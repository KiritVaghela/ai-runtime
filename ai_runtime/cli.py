from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ai_runtime.agents import Agent
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers import ProviderConfig
from ai_runtime.server.agent_server import AgentServer
from ai_runtime.server.protocol import AgentRequest
from ai_runtime.tools.builtin import register_builtin_tools
from ai_runtime.tools import ToolRegistry, GuardedToolExecutor, PermissionPolicy
from ai_runtime.agents.config_files import load_project_instructions


def _build_agent(args) -> Agent:
    config = ProviderConfig(
        provider=ProviderType(args.provider),
        model=args.model,
        api_key=os.getenv(args.api_key_env),
        reasoning_effort=args.reasoning_effort,
    )
    registry = ToolRegistry()
    register_builtin_tools(registry, base_dir=args.cwd)
    executor = GuardedToolExecutor(
        registry.executor if hasattr(registry, "executor") else __import__(
            "ai_runtime.tools.executor", fromlist=["ToolExecutor"]
        ).ToolExecutor(registry),
        PermissionPolicy.permissive() if args.yolo else PermissionPolicy.default(),
    )
    return Agent(
        name="cli-agent",
        provider=config,
        system_prompt=load_project_instructions(args.cwd),
        tool_registry=registry,
    )


async def _run(args) -> None:
    agent = _build_agent(args)
    server = AgentServer(agent)
    req = AgentRequest(session_id="cli", message=args.prompt, mode=args.mode)
    if args.mode == "stream":
        async for line in server.stream(req):
            sys.stdout.write(line)
    else:
        resp = await server.handle(req)
        print(resp.content)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-runtime", description="ai_runtime agent CLI")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument("--provider", default="openai", help="Provider type")
    parser.add_argument("--model", required=True, help="Model id")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY", help="Env var with API key")
    parser.add_argument("--mode", default="chat", choices=["chat", "stream", "plan"])
    parser.add_argument("--cwd", default=os.getcwd(), help="Project root / sandbox dir")
    parser.add_argument("--reasoning-effort", default=None, help="low|medium|high")
    parser.add_argument("--yolo", action="store_true", help="Allow all tools without prompting")
    parser.add_argument("--serve", action="store_true", help="Start stdio server")
    parser.add_argument("--http", action="store_true", help="Start HTTP server")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    if args.serve:
        agent = _build_agent(args)
        asyncio.run(AgentServer(agent).serve_stdio())
    elif args.http:
        agent = _build_agent(args)
        asyncio.run(AgentServer(agent).serve_http(port=args.port))
    elif args.prompt:
        asyncio.run(_run(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
