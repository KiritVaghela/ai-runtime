# AI Runtime

AI Runtime is a provider-agnostic Python runtime for building AI
applications and agent workflows.

## Features

-   Provider abstraction with a unified LLM contract
-   Built-in default provider registry and plugin discovery
-   Custom provider registration with test doubles
-   Conversation management and session-based execution
-   Streaming responses with event processing
-   Streaming timeout/cancellation boundary handling
-   Automatic tool-calling loop (model requests tools → runtime executes → re-invokes)
-   Capability-gated request mapping (tools, structured output, vision, metadata)
-   Expanded provider contract: chat, stream, embeddings, image, transcription
-   Retries via `ProviderConfig.max_retries` (forwarded to the backend)
-   Uniform events: `chat()` and `stream()` both emit `StreamEvent`s
-   Rich streaming events: text, usage, tool call, tool result, thinking, permission
-   Execution engine and pipeline stages
-   Provider metadata, capabilities, and request mapping
-   Fully tested runtime and provider integration coverage

### Agentic capabilities (v0.6.0)

`ai_runtime` now closes the gap with agentic coding tools (Claude Code,
OpenAI Codex, Cursor):

-   **Plan mode** — `AgentRunner.plan()` / `ExecutionEngine.plan()` produce a
    reviewable `Plan` (read-only, no tools run) before execution.
-   **Sub-agents** — declare `SubAgentSpec`s on an `Agent`; the `SupervisorStage`
    fans them out in parallel with isolated contexts and aggregates results.
-   **Permissions** — `PermissionPolicy` + `GuardedToolExecutor` enforce
    allow/deny/ask rules (glob-matched) over tool calls, mirroring tiered
    permission modes.
-   **Hooks** — `HookRegistry` with `PreToolUse` / `PostToolUse` / `PreLLM` /
    `PostLLM` / `OnPlan` / `OnCompact` / `OnError` lifecycle hooks.
-   **Auto compaction** — `CompactionStage` summarizes or drops old turns when
    the context window exceeds its token budget.
-   **Memory consolidation** — `MemoryConsolidationStage` writes durable
    learnings (`LEARNING: ...`) back to the agent's `MemoryStore`.
-   **MCP client** — `MCPClient` + `StdioTransport` speak JSON-RPC over stdio;
    `register_mcp_tools()` wraps server tools as runtime `Tool`s.
-   **Background tasks** — `BackgroundTaskRegistry` for resumable async tasks
    (à la `codex resume` / Claude `/tasks`).
-   **Skill scoping** — `Skill` gains `paths` / `globs` / `disable_model_invocation`.
-   **Reasoning controls** — `ProviderConfig.reasoning_effort` / `thinking_enabled`
    / `thinking_budget_tokens`, forwarded when the provider supports reasoning.

### Integration surfaces (v0.7.0)

To embed `ai_runtime` in a **web app, desktop app, VS Code, or CLI** like
Claude Code / Codex / Cursor / Copilot, the framework now ships:

-   **Built-in tools** — `ReadFileTool`, `WriteFileTool`, `EditFileTool`,
    `GlobTool`, `GrepTool`, `BashTool` (scoped to a sandbox root via
    `register_builtin_tools`). These mirror the file/shell/grep primitives of
    the four tools.
-   **Checkpoints / undo** — `CheckpointManager` snapshots files before edits
    so the UI can roll back (à la Cursor/Claude/Copilot checkpoints).
-   **Agent config files** — `load_project_instructions()` discovers
    `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`,
    `.cursor/rules` from the project root and folds them into the system prompt.
-   **Transport-agnostic server** — `AgentServer` exposes an `Agent` over a
    JSON-line protocol (`AgentRequest` / `AgentResponse` / `StreamEvent`) via
    `serve_stdio()` (VS Code / CLI) and `serve_http()` (web / desktop).
-   **CLI** — `ai-runtime` console script: `ai-runtime "prompt" --model ...`,
    `--mode plan|stream`, `--serve` (stdio), `--http` (HTTP server), `--yolo`.
-   **Workspace / project** — `Project` scopes memory, tools, permissions, and
    checkpoints to a project root (the unit you mount in a client).
-   **Slash commands** — `CommandRegistry` / `default_commands()`
    (`/compact`, `/context`, `/clear`) mirroring Copilot's `/` menu.
-   **BYO provider** — `ProviderConfig.from_env()` reads `COPILOT_PROVIDER_*`
    vars to point at Ollama / vLLM / any OpenAI-compatible endpoint.

## Installation

### From PyPI

```bash
pip install ai-runtime
```

### From source

```bash
git clone https://github.com/KiritVaghela/ai-runtime.git
cd ai-runtime
pip install -e .
```

## Quick Start

```python
import os

from ai_runtime import AgentRuntime
from ai_runtime.conversation import ChatMessage
from ai_runtime.providers.enums import ProviderType

runtime = AgentRuntime.from_provider(
    provider=ProviderType.GROQ,
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)

session = runtime.create_session()

response = await session.chat(
    ChatMessage.user("Hello!")
)

print(response.message.content)
```

## Streaming

```python
from ai_runtime.conversation import ChatMessage
from ai_runtime.streaming import TextDeltaEvent

async for event in session.stream(
    ChatMessage.user("Write a haiku.")
):
    if isinstance(event, TextDeltaEvent):
        print(event.delta, end="")
```

## Streaming with timeout

The runtime supports stream timeout propagation through `ChatRequest.timeout`.
If a provider stream stalls, an `ErrorEvent` is emitted and the stream stops.

```python
from ai_runtime.conversation import ChatMessage, ChatRequest
from ai_runtime.streaming import ErrorEvent, TextDeltaEvent

request = ChatRequest(
    messages=[ChatMessage.user("Generate a poem.")],
    timeout=10.0,
)

async for event in session.stream(request):
    if isinstance(event, TextDeltaEvent):
        print(event.delta, end="")
    elif isinstance(event, ErrorEvent):
        print("\nStream timed out or failed:", event.message)
```

## Provider registry

The runtime uses a provider registry so you can register custom providers or
replace the default provider implementation during tests.

```python
from ai_runtime import AgentRuntime
from ai_runtime.providers import ProviderRegistry
from ai_runtime.providers.enums import ProviderType

registry = ProviderRegistry()
registry.register(ProviderType.OPENAI, MyCustomProvider)

runtime = AgentRuntime.from_provider(
    provider=ProviderType.OPENAI,
    model="gpt-4.1",
    api_key=os.getenv("OPENAI_API_KEY"),
    registry=registry,
)
```

## Architecture

    AgentRuntime
        └── Session
              └── ExecutionEngine
                    └── ExecutionPipeline
                          ├── RequestBuilderStage
                          ├── LLMStage
                          └── ToolLoopStage
                                └── EventProcessor

## Tools

Register tools with a `ToolRegistry`, wrap it in a `ToolExecutor`, and attach
it to the session context. When the model requests a tool, the runtime
executes it and feeds the result back automatically.

```python
from ai_runtime.tools import ToolRegistry, ToolExecutor, FunctionTool
from ai_runtime.conversation import ChatMessage

registry = ToolRegistry()
registry.register(
    FunctionTool("get_weather", lambda ctx, inp: f"Weather in {inp['city']}: sunny")
)

session.context.tool_executor = ToolExecutor(registry)

response = await session.chat(
    ChatMessage.user("What is the weather in Paris?")
)
print(response.message.content)
```

## Agents

An `Agent` bundles a provider, system prompt, tools, memory, and skills.
`AgentRunner` drives execution (including the automatic tool-call loop) and
persists conversation memory across turns.

```python
from ai_runtime import AgentRuntime, Agent, AgentRunner
from ai_runtime.tools import ToolRegistry, ToolExecutor, FunctionTool

runtime = AgentRuntime.from_provider(
    provider=ProviderType.GROQ,
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)

registry = ToolRegistry()
registry.register(FunctionTool("ping", lambda ctx, inp: "pong"))

agent = runtime.create_agent(
    name="helper",
    system_prompt="You are a helpful assistant.",
    tool_registry=registry,
)

runner = AgentRunner(agent)
response = await runner.run("Ping the tool for me.")
print(response.message.content)
```

## Memory, RAG & Skills

- `ai_runtime.memory` — `MemoryStore`, `ConversationMemory`, `SemanticMemory`.
- `ai_runtime.rag` — `Document`, `VectorStore`, `Retriever` for retrieval.
- `ai_runtime.skills` — `Skill` + `SkillRegistry` for composable behaviors.
- `ai_runtime.context` — `ContextWindow` for token budgeting/truncation.

## Documentation

-   [Migration Guide](docs/migration_guide.md)
-   [Adapter Tutorial](docs/adapter_tutorial.md)
-   [Examples](docs/examples.md)
-   [Release Checklist](docs/release_checklist.md)

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Testing

```bash
pytest
```

Current status:

-   Provider registry with custom provider registration
-   Streaming response support with timeouts and completion events
-   Session-based execution and conversation accumulation
-   Provider integration coverage with test doubles

## Roadmap

### v0.3.x

-   Tool registry
-   Tool execution
-   Permission manager
-   Filesystem tools
-   Bash tools

### Future

-   MCP support
-   Multi-agent workflows
-   Desktop and terminal integrations
-   AI Factory integration

## Publishing to PyPI

1.  Update version in `pyproject.toml`.
2.  Build:

```bash
python -m build
```

3.  Check:

```bash
twine check dist/*
```

4.  Upload to TestPyPI:

```bash
twine upload --repository testpypi dist/*
```

5.  Upload to PyPI:

```bash
twine upload dist/*
```

