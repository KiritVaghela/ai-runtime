# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.4] - 2026-07-20

### Added
- **Three high-level agent modes** (`ai_runtime.agents.modes.AgentMode`):
  `ask`, `plan`, and `agent`. Each maps to a low-level execution transport
  (chat/stream/plan) plus a capability profile.
  - **Ask** — query/answer with no tools (stream, or chat fallback).
  - **Plan** — read-only planning via plan mode; no execution, no tools.
  - **Agent** — full capabilities (tools, sub-agents, skills, hooks,
    permissions); streaming by default, chat fallback when unsupported.
- **Transport resolution**: `AgentMode.transport_mode(capabilities)` resolves
  the actual transport from the provider's `ProviderCapabilities` (stream when
  supported, else chat; plan for plan mode). `Agent.transport_mode()` delegates
  to it.
- **Tool gating by mode**: Ask/Plan modes automatically receive an empty tool
  registry so the model cannot request tool calls; Agent mode keeps the full
  registry.
- **Web UI mode selector**: the settings menu now offers Ask / Plan / Agent
  (replacing the old Chat / Plan toggle), and the command palette exposes
  `Ask mode`, `Plan mode`, `Agent mode`.
- **CLI `--mode`**: now accepts `ask` / `plan` / `agent` (default `agent`),
  mapping to the resolved transport and capability profile.

### Changed
- **Web session mode**: `Manager.set_session_mode()` now rebuilds the agent
  with the chosen agent mode (tools/transport updated accordingly) instead of
  only toggling `chat`/`plan`. `Session` carries `mode` (ask/plan/agent) and a
  resolved `transport`.
- **Web streaming**: `_stream_turn` branches on the session's stored agent mode
  (`plan` → planner; otherwise → streaming runner) rather than the raw client
  `mode` string.

## [0.8.3] - 2026-07-20

### Added
- **Human-in-the-loop tool permissions in the web UI**: when a tool call hits
  an `ASK` permission rule, the server pushes a `PermissionEvent` over the
  WebSocket and the UI shows a popup with **Approve**, **Always approve for
  session**, **Deny**, and **Always deny for session**. The answer is sent back
  as a `permission_response` action; "always" options persist an allow/deny
  rule for the rest of the session.
- **Tool execution in streaming mode**: `ExecutionEngine.stream()` now runs the
  tool-call loop inline (previously tools only ran in chat mode), so streamed
  tool calls are executed and their results are fed back to the LLM within the
  same turn.

### Changed
- **Tool-call event accumulation**: `LiteLLMStreamParser` now buffers
  fragmented tool-call chunks and emits a single `ToolCallEvent` per completed
  call (instead of one event per chunk), so the UI renders one `🔧 tool()` card
  instead of several.
- **Outgoing request serialization**: `LiteLLMMapper.to_message()` now serializes
  `tool_calls` and `tool_call_id` so the provider sees the full function-calling
  context when re-invoked with tool results.
- **WebSocket concurrency**: the web receive loop now runs the stream as a
  background task so it can process `permission_response` / `stop` messages
  while a stream is paused awaiting permission (fixes a deadlock that left the
  UI stuck after a tool-call request).

### Fixed
- Web UI no longer hangs after a tool-call request: the permission prompt is
  shown and the tool result merges into the same tool-call card (`✓`/`✗`).

## [0.8.2] - 2026-07-16

### Added (Web app integration of built-ins)
- **Built-in agents panel** in the web UI: list and run the `reviewer`,
  `explainer`, `tester`, `summarizer`, `router`, and `critic` presets.
  - `GET /api/builtin/agents` — catalog of built-in agent presets.
  - `POST /api/builtin/agents/run` — run a preset against a task
    (`{session_id, agent, task}`); `router`/`critic` return their
    higher-level result shapes.
- **Built-in skills panel**: compose built-in skills into a session's agent
  system prompt and track active skills.
  - `GET /api/builtin/skills` — catalog from `default_builtin_skills()`.
  - `POST /api/builtin/skills/apply` — `{session_id, skill}`; appends the
    skill's system prompt and records it in `session.metadata["skills"]`.
- **Built-in command palette**: invoke categorized commands from the UI.
  - `GET /api/builtin/commands` — catalog from `default_commands()`.
  - `POST /api/builtin/commands/run` — `{session_id, name, args}`; renders
    the command template and runs it through the session runner.
- **Self-review toggle**: `POST /api/builtin/self-review`
  (`{session_id, enabled}`) flips `runner.self_review` per session.
- **Frontend**: new "Agents" and "Skills" nav panels, command palette
  entries, and CSS for the new cards/results/skill chips.
- **Tests**: `tests/web/test_web_builtin.py` (13 tests) covering all new
  endpoints with a fake provider.

## [0.8.1] - 2026-07-16

### Added (Built-in agents, skills, commands + self-agentic wiring)
- **Built-in agents** (`ai_runtime.agents.builtin`): ready-to-use factories
  `reviewer_agent`, `explainer_agent`, `tester_agent`, `summarizer_agent`,
  plus `critic_agent` (Reflexion loop) and `router_agent` (intent router with
  default review/explain/test routes).
- **Built-in skills** (`ai_runtime.skills.builtin`): `self_review_skill`,
  `explain_code_skill`, `generate_tests_skill`, `summarize_skill`,
  `no_secrets_guardrail` (secret-blocking `GuardrailSkill`), `retrieval_skill`
  (RAG-backed), and `default_builtin_skills()`.
- **Built-in commands** (`ai_runtime.commands.builtin`): reusable `Command`
  factories (`review_command`, `explain_command`, `test_command`,
  `workflow_command`, `compact_command`, `context_command`, `clear_command`)
  consumed by `default_commands()`; no behavior change to the `/` menu.
- **Self-agentic framework wiring**:
  - `AgentRunner(self_review=True)` applies a `CriticAgent` self-review
    (reflexion) pass over its own output before returning, in both `run()`
    and `stream()`.
  - `CompactionStage` now uses the framework's own `summarizer_agent` as an
    LLM-backed compaction summarizer when a provider is present (via
    `make_agentic_compaction_summarizer`), instead of naively dropping turns.
    `ContextWindow.fit_async()` awaits coroutine summarizers.
  - `ai_runtime.agents.self_agentic` exposes `agentic_summarize`,
    `make_agentic_compaction_summarizer`, `make_self_reviewer`.
- **Tests**: `tests/agents/test_builtin.py` (14 tests) covering built-in
  factories and the self-agentic wiring.

### Changed
- `ContextWindow.fit()` now has an async sibling `fit_async()` that awaits
  coroutine summarizers; `CompactionStage` calls `fit_async()`.

## [0.8.0] - 2026-07-16

### Added (Agentic workflow types)
- **New agent types** (`ai_runtime.agents.types`):
  - `WorkflowAgent` — declarative DAG of `WorkflowStep`s executed in dependency
    order with concurrent layers (bounded by `max_concurrency`); each step's
    output is exposed to downstream steps via `{step_name}` placeholders.
    Steps may render a slash `command`, compose a `skill` for their agent,
    `map_result`, and `max_retries`.
  - `RouterAgent` — intent-based dispatcher routing a message to a specialist
    `Agent` via explicit `when` predicate, `keywords`, or an LLM classifier,
    falling back to `default_agent`.
  - `CriticAgent` — Reflexion-style actor/critic loop: produces a candidate with
    an `actor`, evaluates via a `critic` (or `validator` callable), and feeds
    critiques back for up to `max_iterations` until approved; returns
    `CriticResult`.
- **New skill types** (`ai_runtime.skills.types`):
  - `RetrievalSkill` — RAG-backed skill that injects retrieved context (via a
    `ai_runtime.rag.Retriever`) into the prompt before the LLM call.
  - `GuardrailSkill` — validation hook gating model output via a `guardrail`
    callable, with `reject` / `warn` / `rewrite` on-fail policies; returns
    `GuardrailOutcome`.
  - `Skill` gained optional `retriever` / `retrieval_top_k` /
    `retrieval_query_template` and `guardrail` / `guardrail_on_fail` fields.
  - `ComposedSkills` gained `retrieval_skills`, `guardrail_skills`,
    `async retrieval_context(task)`, and `apply_guardrails(output)`.
- **New command types** (`ai_runtime.commands`):
  - Categorized slash commands `/review`, `/explain`, `/test`, `/workflow`
    (plus existing `/compact`, `/context`, `/clear`).
  - `Command` gained `category` (general|review|explain|test|workflow), `args`,
    and `with_args()` binding.
- **New streaming event** (`ai_runtime.streaming.workflow`):
  - `WorkflowEvent` (type `workflow`) surfaces DAG/router/critic progress
    (`queued` → `running` → `completed`/`failed`); recorded on
    `ExecutionContext.metadata["workflow_steps"]` via `EventProcessor`.
- **Tests**: `tests/agents/test_agent_types.py`,
  `tests/skills/test_skill_types.py`, `tests/commands/test_command_types.py`
  (19 new tests, all passing).

### Changed
- Bumped version to `0.8.0`.
- `CommandRegistry.render()` renamed its first parameter to `command_name` to
  avoid a clash with the `name` template arg used by the `/workflow` command.

## [0.7.0] - 2026-07-14

### Added (Web application)
- **`web/` app**: FastAPI + WebSocket web UI exercising the full framework —
  streaming chat, plan mode, projects (scoped tools/instructions), checkpoints
  (undo), permissions, sub-agents, background tasks, slash commands, and MCP
  connect. Served via `web/run.py` (default `http://127.0.0.1:8787`).
- `web/managers.py`: in-memory `Manager` registry of `Project`s, `Session`s,
  `BackgroundTaskRegistry`, and `HookRegistry`; wires `GuardedToolExecutor`
  to each project's `PermissionPolicy`.
- `web/app.py`: REST + WebSocket routes (`/api/*`, `/ws/{session_id}`).
- `web/static/`: vanilla-JS SPA (`index.html`, `app.js`, `styles.css`) — no
  build step, served by FastAPI.
- `tests/web/test_web_app.py`: integration tests (health, project/session/chat,
  plan mode, permissions, background tasks) using a fake provider.

### Fixed
- **Web chat 500**: `web/managers._build_agent` passed a `ProviderConfig` (a
  pydantic model) as the agent's `provider` instead of a real provider
  instance. Now uses `ProviderRegistry.create(config)` to build a
  `LiteLLMProvider` (with `.chat`/`.stream`), matching `AgentRuntime`.
- Added `logging.basicConfig` (INFO) and a global `Exception` handler that
  returns `{"error": "<Type>: <message>"}` with full tracebacks logged, plus
  per-request logging in `/api/chat` and the WebSocket stream handler.

### Added (Integration-surface gaps vs Claude Code / Codex / Cursor / Copilot)
- **Built-in tools**: `ReadFileTool`, `WriteFileTool`, `EditFileTool`,
  `GlobTool`, `GrepTool`, `BashTool` in `tools/builtin/`; `register_builtin_tools()`
  scopes them to a sandbox root (workspace trust).
- **Checkpoints**: `CheckpointManager` snapshots files before edits for
  rollback (à la Cursor/Claude/Copilot checkpoints).
- **Agent config files**: `load_project_instructions()` / `discover_instructions()`
  discover `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`,
  `.cursor/rules` from a project root.
- **Transport-agnostic server**: `AgentServer` with `serve_stdio()` (VS Code /
  CLI) and `serve_http()` (web / desktop); `AgentRequest` / `AgentResponse` /
  `serialize_event` wire protocol in `server/`.
- **CLI**: `ai-runtime` console script (`--model`, `--mode plan|stream`,
  `--serve`, `--http`, `--yolo`, `--cwd`).
- **Workspace**: `Project` scopes memory, tools, permissions, checkpoints, and
  instructions to a project root.
- **Slash commands**: `CommandRegistry` / `default_commands()` (`/compact`,
  `/context`, `/clear`).
- **BYO provider**: `ProviderConfig.from_env()` reads `COPILOT_PROVIDER_*`
  vars for Ollama / vLLM / OpenAI-compatible endpoints.

### Changed
- Bumped version to `0.7.0`.

## [0.6.0] - 2026-07-15

### Added (Agentic gap remediation vs Claude Code / Codex / Cursor)
- **Plan mode**: `ExecutionMode.PLAN`, `Plan`/`PlanStep` models, `PlannerStage`,
  and `ExecutionEngine.plan()` / `AgentRunner.plan()` for reviewable,
  read-only planning before execution.
- **Sub-agents**: `SubAgentSpec` / `SubAgentResult`, `Agent.sub_agents`, and
  `SupervisorStage` that fans out child agents in parallel with isolated
  contexts and aggregates results into the parent conversation.
- **Permissions**: `PermissionPolicy`, `PermissionRule`, `PermissionDecision`,
  and `GuardedToolExecutor` enforcing allow/deny/ask rules (glob-matched over
  tool name + rendered params) before tool execution.
- **Hooks**: `HookRegistry` + `HookEvent` (`PreToolUse`, `PostToolUse`,
  `PreLLM`, `PostLLM`, `OnPlan`, `OnCompact`, `OnError`) wired into
  `LLMStage` and `ToolLoopStage` via `ExecutionContext.hooks`.
- **Auto compaction**: `CompactionStage` summarizes/drops old turns when the
  conversation exceeds the token budget; fires an `OnCompact` hook.
- **Memory consolidation**: `MemoryConsolidationStage` extracts `LEARNING:`
  lines and persists them to the agent's `MemoryStore` after a task.
- **MCP client**: `MCPClient`, `MCPTransport`, `StdioTransport` (JSON-RPC over
  stdio), and `MCPTool` / `register_mcp_tools()` to wrap server tools as
  runtime `Tool`s.
- **Background tasks**: `BackgroundTaskRegistry` / `BackgroundTask` with
  submit / start / wait / cancel / resume semantics.
- **Skill scoping**: `Skill` gains `paths`, `globs`, and
  `disable_model_invocation` fields.
- **Reasoning controls**: `ProviderConfig.reasoning_effort`,
  `thinking_enabled`, `thinking_budget_tokens` forwarded by `LiteLLMMapper`
  when `capabilities.reasoning` is set.

### Changed
- Default execution pipeline now composes: `CompactionStage` →
  `RequestBuilderStage` → `SupervisorStage` → `LLMStage` → `ToolLoopStage` →
  `MemoryConsolidationStage`.
- Bumped version to `0.6.0`.

## [0.5.0] - 2026-07-14

### Added (P2 — contract breadth)
- **Expanded provider contract**: `LLMProvider` now declares optional
  capability-gated `embed()`, `generate_image()`, and `transcribe()` methods
  (default: `NotImplementedError`).
- `LiteLLMProvider.embed()` implemented via `litellm.aembedding`, gated on
  `capabilities.embeddings` and raising `NotImplementedError` otherwise.
- `ProviderCapabilities` gained a `transcription` flag.
- **Retries**: `LiteLLMProvider` forwards `ProviderConfig.max_retries` to
  LiteLLM as `num_retries` for both chat and stream paths.
- **Uniform events**: `chat()` mode now emits the same `StreamEvent` types
  (`TextDeltaEvent`, `UsageEvent`, `CompletedEvent`) as `stream()` via
  `EventProcessor.process_response`, so `EventBus` subscribers are consistent.

### Changed (P3 — cleanup)
- Removed dead/duplicate modules: `execution/executor.py` (`LLMExecutor`),
  `execution/result.py` (`ExecutionResult`), `execution/pipeline/conversation_stage.py`
  (`ConversationStage`), `execution/pipeline/tool_stage.py` (`ToolStage`,
  superseded by `ToolLoopStage`), `providers/litellm_exceptions.py` (orphaned
  duplicate of `providers/exceptions.py`), `adapters/litellm/exceptions.py`
  (unused `AdapterError` stub), and `adapters/litellm/request_adapter.py`
  (duplicate of `LiteLLMMapper`).
- Removed the corresponding tests (`test_conversation_stage.py`,
  `test_request_adapter.py`).
- `ConversationStage` no longer exported from the pipeline package.

## [0.4.0] - 2026-07-14

### Added
- **Context management** (`ai_runtime.context`): `ContextWindow` with token
  budgeting, `DropOldestStrategy` truncation (preserves system messages), and
  a pluggable `summarizer` hook for semantic compaction.
- **Memory subsystem** (`ai_runtime.memory`): `MemoryStore` interface +
  `InMemoryStore`, `ConversationMemory` for cross-turn persistence, and
  `SemanticMemory` for summarization-based compaction.
- **RAG subsystem** (`ai_runtime.rag`): `Document`, `VectorStore` interface +
  `InMemoryVectorStore` (cosine similarity), and `Retriever` with context
  formatting.
- **Skills subsystem** (`ai_runtime.skills`): `Skill` (system prompt + tools +
  optional run hook) and `SkillRegistry` with `ComposedSkills` aggregation.
- **Agent subsystem** (`ai_runtime.agents`): declarative `Agent` (provider +
  system prompt + tools + memory + skills) and `AgentRunner` orchestration
  that drives the execution pipeline (including the tool-call loop) and
  persists conversation memory.
- `AgentRuntime.create_agent(...)` builds an `Agent` bound to a provider.
- Top-level package now re-exports `ContextWindow`, memory, RAG, skills,
  agent, and tool primitives.

### Changed
- `AgentRuntime` exposes both `create_session()` and `create_agent()`.

## [0.3.0] - 2026-07-14

### Added
- **Automatic tool-calling loop**: new `ToolLoopStage` executes model-requested
  tools via `ToolExecutor` and re-invokes the LLM until a final answer
  (capped by `max_iterations`). Wired into the default execution pipeline.
- **Capability-gated request mapping**: `LiteLLMMapper.to_request` now forwards
  `tools`/`tool_choice` (gated on `capabilities.tools`), `response_format`
  (gated on `structured_output`), and `metadata`; multimodal `content` arrays
  pass through untouched for vision-capable providers.
- **Rich streaming events**: `ToolCallEvent`, `ToolResultEvent`,
  `ThinkingEvent`, and `PermissionEvent` added to the `StreamEvent` hierarchy
  and supported by `StreamEventFactory` and `LiteLLMStreamParser`.
- `ChatMessage` gained `tool_calls`/`tool_call_id` fields and a `ToolCall`
  model; `ChatResponse` carries the raw provider payload for extraction.
- `ChatRequest` gained `tools`, `response_format`, and `tool_choice` fields.
- `FunctionTool` exported from `ai_runtime.tools`; `ToolCall` exported from
  `ai_runtime.conversation`.
- `ExecutionContext` gained `thinking_text` and `tool_executor` fields.

### Changed
- `LiteLLMProvider` passes negotiated `capabilities` into the request mapper
  for both chat and stream paths.
- `EventProcessor` accumulates thinking text and tracks tool inputs/results.
- Default pipeline is now `RequestBuilderStage → LLMStage → ToolLoopStage`.

## [0.2.0] - 2026-07-14

### Added
- Unified `LLMProvider` / `BaseProvider` contract with `chat`, `stream`,
  `list_models`, and `close` methods.
- Immutable `ProviderRegistry` with `freeze()`, `list_providers()`, and
  `discover()` plugin entry-point support.
- Streaming timeout propagation via `ChatRequest.timeout` and
  `ExecutionContext.stream_timeout`. The engine emits an `ErrorEvent` on
  stall or stream failure.
- Provider integration tests using test doubles across OpenAI, Groq,
  Anthropic, and Ollama provider types.
- Documentation: migration guide, adapter tutorial, and examples.
- `ai_runtime.compat` module providing backwards-compatible aliases
  (e.g. `ChatSession` -> `Session`).

### Changed
- `Session` replaces the previous `ChatSession` entrypoint for conversation
  execution.
- `RequestBuilderStage` now propagates `stream_timeout` into the built
  `ChatRequest`.
- Provider package `__all__` exports corrected (`ProviderInfo`,
  `ProviderCapabilities`).

### Deprecated
- `ChatSession` import path — use `ai_runtime.session.Session`.

## [0.1.0] - 2026-06-01

### Added
- Initial provider-agnostic runtime with LiteLLM and OpenAI adapters.
- Conversation management, chat sessions, and streaming responses.
- Execution engine and pipeline stages.
- Event bus for execution events.
- Provider registry and metadata.
