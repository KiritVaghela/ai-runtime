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

### Agentic capabilities

`ai_runtime` closes the gap with agentic coding tools (Claude Code,
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

### Agentic workflow types

Beyond the single-agent loop, `ai_runtime` ships the higher-level agent
primitives that modern agentic frameworks (LangGraph, AutoGen, CrewAI,
Reflexion) are built from. They compose with the existing `Agent`, `Skill`,
`Command`, and pipeline machinery.

**New agent types** (`ai_runtime.agents`):

-   **`WorkflowAgent`** — a declarative DAG of `WorkflowStep`s. Steps run in
    dependency order with concurrent layers (bounded by `max_concurrency`);
    each step's output is exposed to downstream steps via `{step_name}`
    placeholders. Mirrors the graph/orchestration layer of LangGraph/AutoGen.
-   **`RouterAgent`** — intent-based dispatcher. Routes a message to a
    specialist `Agent` via explicit predicates, keyword matching, or an LLM
    classifier, falling back to a `default_agent`. Mirrors multi-agent
    orchestrators (CrewAI routers, AutoGen groups).
-   **`CriticAgent`** — Reflexion-style actor/critic loop. Produces a candidate
    with an `actor`, evaluates it with a `critic` (or a `validator` callable),
    and feeds critiques back for up to `max_iterations` until approved. Mirrors
    self-reflection / CriticGPT patterns.

**New skill types** (`ai_runtime.skills`):

-   **`RetrievalSkill`** — RAG-backed skill that injects retrieved context
    (via a `ai_runtime.rag.Retriever`) into the prompt before the LLM call.
-   **`GuardrailSkill`** — validation hook that gates model output via a
    `guardrail` callable, with `reject` / `warn` / `rewrite` on-fail policies.
    `ComposedSkills` aggregates retrieval context and applies guardrails
    automatically.

**New command types** (`ai_runtime.commands`):

-   Categorized slash commands: `/review`, `/explain`, `/test`, `/workflow`
    (plus the existing `/compact`, `/context`, `/clear`). Commands carry a
    `category` and `args` and support `with_args()` binding.

**New streaming event**:

-   **`WorkflowEvent`** — surfaces DAG/router/critic progress (`queued` →
    `running` → `completed`/`failed`) so clients can render step status, and is
    recorded on `ExecutionContext.metadata["workflow_steps"]`.

### Agent modes

Every `Agent` carries a high-level `agent_mode` (`ai_runtime.agents.modes`)
that selects both the low-level execution transport and the capability
profile. The web UI and CLI expose three modes:

-   **Ask** (`ask`) — simple query/answer with **no tools**. Uses streaming
    when the provider supports it, otherwise falls back to chat. Mirrors a
    plain chat completion.
-   **Plan** (`plan`) — read-only planning. Uses plan mode (no execution, no
    tools); the model proposes a plan that the user can approve before any
    action is taken.
-   **Agent** (`agent`) — full agent: streaming (or chat fallback) with all
    capabilities enabled by default — tools, sub-agents, skills, hooks, and
    human-in-the-loop permissions. This is the default.

The transport is resolved at agent-build time from the provider's
`ProviderCapabilities`: `AgentMode.transport_mode(capabilities)` returns
`"plan"` for Plan mode, `"chat"` when streaming is unsupported, and
`"stream"` otherwise. Ask/Plan modes automatically receive an empty tool
registry so the model cannot request tool calls.

### Built-in agents, skills & commands

The framework ships ready-to-use presets so you don't have to hand-roll common
agents/skills/commands, and it uses them on *itself* to become more agentic.

**Built-in agents** (`ai_runtime.agents.builtin`): `reviewer_agent`,
`explainer_agent`, `tester_agent`, `summarizer_agent`, plus `critic_agent`
(Reflexion loop) and `router_agent` (intent router with default
review/explain/test routes).

**Built-in skills** (`ai_runtime.skills.builtin`): `self_review_skill`,
`explain_code_skill`, `generate_tests_skill`, `summarize_skill`,
`no_secrets_guardrail` (secret-blocking `GuardrailSkill`), `retrieval_skill`
(RAG-backed), and `default_builtin_skills()`.

**Built-in commands** (`ai_runtime.commands.builtin`): reusable `Command`
factories (`review_command`, `explain_command`, `test_command`,
`workflow_command`, `compact_command`, `context_command`, `clear_command`)
consumed by `default_commands()`.

**Self-agentic wiring** — the runtime turns its own primitives on itself:

-   `AgentRunner(self_review=True)` runs a `CriticAgent` self-review (reflexion)
    pass over its own output before returning, in both `run()` and `stream()`.
-   `CompactionStage` uses the framework's own `summarizer_agent` as an
    LLM-backed compaction summarizer (via `make_agentic_compaction_summarizer`)
    when a provider is present, instead of naively dropping old turns.

### Integration surfaces

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

### Web application (`web/`)

A ready-to-run web UI + REST/WebSocket API that exercises the full framework:

```bash
export AI_RUNTIME_API_KEY=sk-...      # or AI_RUNTIME_PROVIDER/AI_RUNTIME_BASE_URL
./venv/bin/python web/run.py          # serves http://127.0.0.1:8787
```

Features exposed in the UI:
- **Streaming chat** (WebSocket streams `StreamEvent`s: text, tool calls, tool
  results, thinking, usage, completion)
- **Plan mode** (`/api/chat` with `mode: plan` returns a reviewable `Plan`)
- **Projects** — `Project` scoping with auto-loaded instruction files + sandboxed
  built-in tools (Read/Write/Edit/Glob/Grep/Bash)
- **Checkpoints / undo** — snapshot + restore files before agent edits
- **Permissions** — `PermissionPolicy` allow/deny/ask rules per tool + params.
  When the policy says *ask*, the web UI shows a human-in-the-loop popup with
  **Approve**, **Always approve for session**, **Deny**, and
  **Always deny for session**; the tool runs (or is blocked) and its result
  merges into the tool-call card.
- **Sub-agents** — configure `SubAgentSpec`s; supervisor fans them out
- **Background tasks** — submit/resume/cancel via `BackgroundTaskRegistry`
- **Slash commands** — `/compact`, `/context`, `/clear`, plus categorized
  agentic commands `/review`, `/explain`, `/test`, `/workflow`
- **MCP** — connect a stdio MCP server and register its tools
- **Reasoning controls** — `reasoning_effort` / `thinking_enabled` per request
- **Built-in agents panel** — run `reviewer` / `explainer` / `tester` /
  `summarizer` / `router` / `critic` presets from the UI
  (`GET /api/builtin/agents`, `POST /api/builtin/agents/run`)
- **Built-in skills panel** — compose `self_review`, `explain_code`,
  `generate_tests`, `summarize`, `no_secrets_guardrail`, `retrieval` skills
  into a session (`GET /api/builtin/skills`, `POST /api/builtin/skills/apply`)
- **Built-in command palette** — invoke categorized commands from the UI
  (`GET /api/builtin/commands`, `POST /api/builtin/commands/run`).
  Both the composer slash-autocomplete and the command palette show a worked
  **example** for each command (e.g. `/review def add(a, b): …`).
- **Self-review toggle** — enable the reflexion self-review pass per session
  (`POST /api/builtin/self-review`)

See `web/README.md` for the full API reference.

### Built-in commands

The web UI (and CLI) ship a categorized `/` command menu. Type `/` in the
composer to see the full list with live examples, or open the command palette
(Cmd/Ctrl+K). Every command accepts free-form text after its name:

| Command | Category | Example |
|----------|----------|----------|
| `/compact` | general | `/compact` — summarize the conversation to free context |
| `/context` | general | `/context` — show a token/context breakdown |
| `/clear` | general | `/clear` — clear the conversation history |
| `/review` | review | `/review def add(a, b):\n    return a + b` |
| `/explain` | explain | `/explain the quicksort implementation in sort.py` |
| `/test` | test | `/test def divide(a, b):\n    return a / b` |
| `/workflow` | workflow | `/workflow refactor Extract the parser into its own module` |

- **General commands** (`/compact`, `/context`, `/clear`) run as side effects
  against the active session.
- **Agentic commands** (`/review`, `/explain`, `/test`, `/workflow`) render
  their prompt template with the supplied text and run it through the session's
  own agent runner, streaming the result back into the chat.

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


