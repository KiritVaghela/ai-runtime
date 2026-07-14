# ai_runtime Web Application

A browser UI + REST/WebSocket API that exercises the full `ai_runtime`
feature set (chat, streaming, plan mode, projects, built-in tools,
checkpoints, permissions, sub-agents, background tasks, MCP, slash commands).

## Run

```bash
# Install web deps (already in the venv if you ran the framework install)
./venv/bin/pip install -r web/requirements.txt

# Configure a provider (any OpenAI-compatible endpoint works)
export AI_RUNTIME_API_KEY=sk-...
export AI_RUNTIME_MODEL=gpt-4o
# Optional BYO endpoint:
# export AI_RUNTIME_PROVIDER=openai
# export AI_RUNTIME_BASE_URL=http://localhost:11434

./venv/bin/python web/run.py
# → http://127.0.0.1:8787
```

Environment variables: `AI_RUNTIME_PROVIDER`, `AI_RUNTIME_MODEL`,
`AI_RUNTIME_API_KEY`, `AI_RUNTIME_BASE_URL`, `AI_RUNTIME_WEB_HOST`,
`AI_RUNTIME_WEB_PORT`, `AI_RUNTIME_PROJECT_ROOT`, `AI_RUNTIME_REASONING_EFFORT`.

## Architecture

```
web/
  run.py            # uvicorn entrypoint
  app.py            # FastAPI app: REST + WebSocket routes
  config.py         # WebConfig (env-driven)
  managers.py       # in-memory registry of projects/sessions/tasks/hooks
  static/
    index.html      # SPA shell
    app.js          # frontend (WS + REST, no build step)
    styles.css
  requirements.txt
```

`managers.Manager` wraps the framework: each `Session` owns a `Project`
(scoped tools/memory/permissions/checkpoints) and an `AgentRunner`. The
WebSocket route streams `StreamEvent`s produced by the runner's pipeline.

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| POST | `/api/projects` | create a `Project(root, name)` |
| GET | `/api/projects` | list projects + their tools |
| POST | `/api/sessions` | create a chat session for a project |
| GET | `/api/sessions` | list sessions |
| POST | `/api/chat` | non-streaming chat or plan (`mode: plan`) |
| WS | `/ws/{session_id}` | streaming chat (StreamEvents as JSON lines) |
| POST | `/api/permissions` | add a `PermissionRule` (allow/deny/ask) |
| POST | `/api/subagents` | attach a `SubAgentSpec` to a session |
| POST | `/api/checkpoints/snapshot` | snapshot files |
| POST | `/api/checkpoints/restore` | restore last checkpoint (undo) |
| POST | `/api/tasks` | submit a background task |
| GET | `/api/tasks` | list background tasks |
| POST | `/api/commands/{name}` | run a slash command (`compact`/`clear`/…) |
| POST | `/api/mcp/connect` | connect a stdio MCP server, register its tools |

## Notes

- State is in-memory (resets on restart). Swap `managers.Manager` for a
  persistent store (Redis/SQL) to make sessions durable.
- The built-in tools are scoped to the project `root` (workspace trust).
- The same `AgentServer` protocol powers the CLI and VS Code integration.
- **Logging / errors**: the app configures `logging.basicConfig` at INFO. All
  unhandled exceptions return a JSON `{"error": "<Type>: <message>"}` with a
  500 status, and are logged with full tracebacks via `logger.exception`. The
  `/api/chat` and `/ws/{session_id}` paths log request start/completion and any
  failure. Check the server console (or `web/run.py` stdout) for details.
