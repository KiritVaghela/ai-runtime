# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
