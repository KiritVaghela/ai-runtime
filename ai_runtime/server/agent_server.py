from __future__ import annotations

import asyncio
import sys
from typing import Any, AsyncIterator

from ai_runtime.agents import Agent, AgentRunner
from ai_runtime.conversation import ChatMessage
from ai_runtime.execution.mode import ExecutionMode

from .protocol import (
    AgentRequest,
    AgentResponse,
    serialize_event,
    parse_request,
)


class AgentServer:
    """Transport-agnostic server exposing an `AgentRunner` to clients.

    The same server powers a stdio server (for VS Code / CLI), an HTTP
    server (for web/desktop), and in-process use. It maps `AgentRequest`
    to runner calls and streams `StreamEvent`s back as JSON lines.
    """

    def __init__(self, agent: Agent):
        self.agent = agent
        self.runner = AgentRunner(agent)

    async def handle(self, request: AgentRequest) -> AgentResponse:
        """Handle a non-streaming (chat/plan) request."""
        if request.mode == "plan":
            plan = await self.runner.plan(request.message)
            return AgentResponse(
                session_id=request.session_id,
                content=str(plan),
                finish_reason="plan",
            )
        response = await self.runner.run(request.message)
        return AgentResponse(
            session_id=request.session_id,
            content=response.message.content or "",
            finish_reason=response.finish_reason,
            usage=response.usage.model_dump() if response.usage else None,
        )

    async def stream(self, request: AgentRequest) -> AsyncIterator[str]:
        """Handle a streaming request, yielding JSON-line `StreamEvent`s."""
        async for event in self.runner.stream(request.message):
            yield serialize_event(event)

    # ---- Transport adapters ----

    async def serve_stdio(self, reader=None, writer=None) -> None:
        """Read JSON-line requests from stdin, write JSON-line responses."""
        r = reader or sys.stdin
        w = writer or sys.stdout
        for line in r:
            line = line.strip()
            if not line:
                continue
            req = parse_request(line)
            if req.mode == "stream":
                async for evt in self.stream(req):
                    w.write(evt + "\n")
                    w.flush()
            else:
                resp = await self.handle(req)
                w.write(serialize_event(resp.__dict__) + "\n")
                w.flush()

    async def serve_http(self, host: str = "127.0.0.1", port: int = 8787) -> None:
        """Minimal aiohttp-free HTTP server using stdlib asyncio.

        Exposes POST /chat (JSON in, JSON out) and GET /health.
        """
        import http.server
        import json
        from http.server import BaseHTTPRequestHandler
        from functools import partial

        server_self = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                req = parse_request(body.decode())
                resp = asyncio.get_event_loop().run_until_complete(
                    server_self.handle(req)
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp.__dict__, default=str).encode())

            def do_GET(self):  # noqa: N802
                if self.path == "/health":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass

        httpd = http.server.HTTPServer((host, port), Handler)
        httpd.serve_forever()
