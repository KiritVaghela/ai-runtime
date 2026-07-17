# PROJECT_CONTEXT.MD

> Single source of truth for the `ai_runtime` framework. Read this first to
> understand the architecture before diving into code. Keep it updated when
> subsystems change.

## 1. What this project is

`ai_runtime` is a **provider-agnostic Python runtime for building AI
applications and agentic workflows** (à la Claude Code / OpenAI Codex /
Cursor / Copilot). It abstracts LLM providers behind a unified contract and
ships the orchestration primitives those tools need: agents, skills, slash
commands, sub-agents, plan mode, permissions, hooks, memory, RAG, MCP, and
background tasks.

- **Package root:** `ai_runtime/`
- **Top-level entry:** `ai_runtime/__init__.py` (re-exports public API)
- **Runtime facade:** `ai_runtime/runtime.py` → `AgentRuntime`
- **Version:** `ai_runtime/version.py`

## 2. Layered architecture

```
AgentRuntime (runtime.py)
   └── Session / Agent
          └── AgentRunner (agents/runner.py)  ← orchestration
                 └── ExecutionEngine (execution/engine.py)
                        └── ExecutionPipeline (execution/pipeline/pipeline.py)
                               └── ExecutionStage(s)  ← composable stages
                                      └── ExecutionContext (execution/context.py)  ← shared state
```

Key principle: **declarative specs + a pipeline of stages**. An `Agent` is a
declarative spec; the `AgentRunner` wires it into the `ExecutionEngine`, which
runs an ordered `ExecutionPipeline` of `ExecutionStage` objects over a shared
`ExecutionContext`.

## 3. Core modules (read these to understand a subsystem)

| Concern | File(s) | Notes |
|---|---|---|
| Provider contract | `providers/base.py`, `providers/provider.py`, `docs/provider_contract.md` | `chat()`, `stream()`, `list_models()`, `info`. Async. |
| Conversation | `conversation/message.py`, `conversation/response.py`, `conversation/request.py`, `conversation/enums.py` | `ChatMessage` (frozen pydantic), roles: system/user/assistant/tool. |
| Streaming events | `streaming/__init__.py`, `streaming/enums.py`, `streaming/event.py` | `StreamEvent` ABC; types: text_delta, usage, completed, error, tool_call, tool_result, thinking, permission. |
| Execution engine | `execution/engine.py` | `chat()`, `plan()`, `stream_plan()`. Builds default pipeline. |
| Pipeline stages | `execution/pipeline/*.py` | `CompactionStage`, `RequestBuilderStage`, `SupervisorStage`, `LLMStage`, `ToolLoopStage`, `PlannerStage`, `MemoryConsolidationStage`. |
| Execution context | `execution/context.py` | Pydantic `BaseModel`, `arbitrary_types_allowed`. Holds provider, conversation, request, response, plan, agent, hooks, metadata, tool_executor, etc. |
| Modes | `execution/mode.py` | `ExecutionMode`: CHAT / STREAM / PLAN. |
| Plan | `execution/plan.py` | `Plan` (goal, steps, risks, raw) + `PlanStep`. |
| Hooks | `execution/hooks.py` | `HookRegistry`, `HookEvent` (PreToolUse, PostToolUse, PreLLM, PostLLM, OnPlan, OnCompact, OnError), `HookContext`, `HookResult`. |
| Tools | `tools/tool.py`, `tools/registry.py`, `tools/executor.py`, `tools/permissions.py`, `tools/guarded_executor.py`, `tools/builtin.py`, `tools/checkpoints.py` | `Tool` ABC (`async run(context, input) -> ToolResult`). `ToolExecutor` runs in threadpool. `GuardedToolExecutor` + `PermissionPolicy` enforce allow/deny/ask. |
| Memory | `memory/store.py`, `memory/conversation_memory.py`, `memory/semantic.py` | `MemoryStore` ABC; `InMemoryStore`; `ConversationMemory`; `SemanticMemory`. |
| RAG | `rag/retriever.py`, `rag/document.py`, `rag/vector_store.py` | `Retriever` over `VectorStore` (`InMemoryVectorStore`). |
| MCP | `mcp/client.py`, `mcp/adapter.py` | `MCPClient` + `StdioTransport` JSON-RPC; `register_mcp_tools()`. |
| Background tasks | `execution/background.py` | `BackgroundTaskRegistry`, `BackgroundTask`, `TaskStatus`. |
| Server | `server/agent_server.py`, `server/protocol.py` | `AgentServer` over `AgentRequest`/`AgentResponse`; stdio + HTTP transports. |
| CLI | `cli.py` | `ai-runtime` console script. |
| Workspace | `workspace/project.py` | `Project` scopes memory/tools/permissions/checkpoints/instructions to a root. |
| Config files | `agents/config_files.py` | Discovers `copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`. |

## 4. Agent subsystem (`ai_runtime/agents/`)

- **`agent.py` → `Agent`** (declarative spec): `name`, `provider`,
  `system_prompt`, `tool_registry`, `memory_store`, `skill_registry`,
  `skills`, `memory`, `sub_agents`. Methods: `effective_system_prompt()`
  (combines prompt + composed skill prompts), `effective_tool_names()`,
  `ensure_memory_loaded()`.
- **`runner.py` → `AgentRunner`**: `run()`, `stream()`, `plan()`,
  `stream_plan()`. Loads memory → seeds system prompt + history → runs engine
  → persists memory.
- **`subagent.py` → `SubAgentSpec`, `SubAgentResult`**: declarative child
  agent spec (`name`, `agent`, `task_template`, `max_depth`, `isolated`).
- **`types.py` → new agentic-workflow agent types** (v0.8.0):
  - `WorkflowStep` + `WorkflowAgent`: declarative DAG; steps run in dependency
    order with concurrent layers (bounded by `max_concurrency`); each step's
    output exposed to downstream steps via `{step_name}` placeholders in
    `prompt_template`; supports `command` (render a slash command), `skill`
    (compose a skill for the step's agent), `map_result`, `max_retries`.
  - `Route` + `RouterAgent`: intent dispatcher; matches via `when` predicate,
    `keywords`, or an LLM classifier (uses `default_agent.provider`); falls
    back to `default_agent`.
  - `CriticResult` + `CriticAgent`: Reflexion actor/critic loop; `actor` +
    `critic` (or `validator` callable) with `max_iterations`; feeds critiques
    back until approved.
- **`builtin.py` → built-in agent presets** (v0.8.1): `reviewer_agent`,
  `explainer_agent`, `tester_agent`, `summarizer_agent`, `critic_agent`
  (Reflexion loop), `router_agent` (default review/explain/test routes).
- **`self_agentic.py` → self-agentic wiring** (v0.8.1): `agentic_summarize`,
  `make_agentic_compaction_summarizer`, `make_self_reviewer`. Used by
  `CompactionStage` (LLM-backed compaction) and `AgentRunner(self_review=True)`.
- **`config_files.py`**: instruction-file discovery.
- **`__init__.py`** exports: `Agent`, `AgentRunner`, `SubAgentSpec`,
  `SubAgentResult`, `WorkflowStep`, `WorkflowAgent`, `Route`, `RouterAgent`,
  `CriticResult`, `CriticAgent`, `reviewer_agent`, `explainer_agent`,
  `tester_agent`, `summarizer_agent`, `critic_agent`, `router_agent`,
  `agentic_summarize`, `make_agentic_compaction_summarizer`, `make_self_reviewer`.

## 5. Skills subsystem (`ai_runtime/skills/`)

- **`skill.py` → `Skill`** (dataclass): `name`, `description`,
  `system_prompt`, `tools`, `metadata`, `run` (callable hook),
  `paths`/`globs` (scoping), `disable_model_invocation`. Also optional
  retrieval config (`retriever`, `retrieval_top_k`, `retrieval_query_template`)
  and guardrail config (`guardrail` callable, `guardrail_on_fail`).
- **`registry.py` → `SkillRegistry`** (`register`, `get`, `list`,
  `compose`) + **`ComposedSkills`** (aggregates `system_prompt` + `tool_names`).
  `ComposedSkills` also exposes `retrieval_skills`, `guardrail_skills`,
  `async retrieval_context(task)`, and `apply_guardrails(output) -> (final, failures)`.
- **`types.py` → new skill types** (v0.8.0): `RetrievalSkill` (RAG-backed,
  `async retrieve_context(task)`) and `GuardrailSkill` (validation hook,
  `evaluate(output) -> GuardrailOutcome` with `reject`/`warn`/`rewrite`).
- **`builtin.py` → built-in skill presets** (v0.8.1): `self_review_skill`,
  `explain_code_skill`, `generate_tests_skill`, `summarize_skill`,
  `no_secrets_guardrail` (secret-blocking `GuardrailSkill`), `retrieval_skill`,
  `default_builtin_skills()`.
- **`__init__.py`** exports: `Skill`, `SkillRegistry`, `ComposedSkills`,
  `RetrievalSkill`, `GuardrailSkill`, `GuardrailOutcome`, `self_review_skill`,
  `explain_code_skill`, `generate_tests_skill`, `summarize_skill`,
  `no_secrets_guardrail`, `retrieval_skill`, `default_builtin_skills`.

## 6. Commands subsystem (`ai_runtime/commands/`)

- **`registry.py` → `Command`** (dataclass): `name`, `description`,
  `prompt_template`, `run`, `category` (general|review|explain|test|workflow),
  `args` (template arg names). `render(**kwargs)` formats the template;
  `with_args(**kwargs)` returns a bound copy.
- **`CommandRegistry`**: `register`, `get`, `list`, `render`.
- **`default_commands()`**: `/compact`, `/context`, `/clear` (general) plus
  `/review`, `/explain`, `/test`, `/workflow` (categorized agentic commands).
  `default_commands()` is built from `builtin.default_builtin_commands()`.
- **`builtin.py` → built-in command factories** (v0.8.1): `compact_command`,
  `context_command`, `clear_command`, `review_command`, `explain_command`,
  `test_command`, `workflow_command`, `default_builtin_commands`.
- **`__init__.py`** exports: `Command`, `CommandRegistry`, `default_commands`,
  `compact_command`, `context_command`, `clear_command`, `review_command`,
  `explain_command`, `test_command`, `workflow_command`, `default_builtin_commands`.

## 7. Extension points (how to add new behavior)

### Add a new Agent type
1. Define a subclass or spec in `agents/` (mirror `SubAgentSpec` pattern).
   New high-level types (WorkflowAgent, RouterAgent, CriticAgent) live in
   `agents/types.py` and reuse `AgentRunner` rather than new pipeline stages.
2. If it needs orchestration, add a stage in `execution/pipeline/` and wire it
   into `ExecutionEngine._create_default_pipeline()` (or a custom pipeline).
3. Export from `agents/__init__.py` and `ai_runtime/__init__.py`.

### Add a new Skill type
1. Extend `Skill` (dataclass) in `skills/skill.py` with new fields.
2. Update `ComposedSkills` in `skills/registry.py` to aggregate the new field.
3. Export from `skills/__init__.py`.

### Add a new Command type
1. Extend `Command` (dataclass) in `commands/registry.py`.
2. Add to `default_commands()` or a registry factory.
3. Export from `commands/__init__.py`.

### Add a new ExecutionStage
1. Subclass `ExecutionStage` (`execution/pipeline/stage.py`), implement
   `async execute(context) -> ExecutionContext`.
2. Add to a pipeline in `execution/engine.py` or `AgentRunner`.
3. Export from `execution/pipeline/__init__.py` if reusable.

### Add a new Tool
1. Subclass `Tool` (`tools/tool.py`), implement `async run(context, input)`.
2. Register in a `ToolRegistry`. For file/shell safety use
   `GuardedToolExecutor` + `PermissionPolicy`.

### Add a new Streaming event
1. Subclass `StreamEvent` (`streaming/event.py`), add a `StreamEventType`
   in `streaming/enums.py`.
2. Handle in `execution/event_processor.py` if it mutates context state.
   `WorkflowEvent` (type `workflow`) records step progress on
   `context.metadata["workflow_steps"]`.

## 8. Patterns & conventions

- **Async everywhere.** Providers, tools, stages, runners are all `async`.
- **Pydantic models** for wire/data types (`ChatMessage`, `ExecutionContext`,
  `Plan`, `StreamEvent`). `ConfigDict(frozen=True)` for events/messages.
- **Dataclasses** for lightweight specs (`Skill`, `Command`, `SubAgentSpec`,
  `ToolResult`, `BackgroundTask`).
- **Mirroring agentic tools** is the explicit design goal — comments
  repeatedly reference Claude Code / Codex / Cursor / Copilot behaviors.
- **Isolation:** sub-agents run in separate contexts; one failure doesn't kill
  the fan-out (`SupervisorStage`).
- **Hooks** are the clean extension point for observing/mutating/blocking
  without touching the pipeline.
- **`from __future__ import annotations`** at the top of every module.
- **Tests:** `tests/` mirrors `ai_runtime/` structure. Use `@pytest.mark.asyncio`.
  Fixtures in `tests/conftest.py` (`openai_key`, `groq_key`). Fake providers
  are plain classes with `async chat()` / `async stream()`.

## 9. Public API surface (`ai_runtime/__init__.py`)

`AgentRuntime`, `ContextWindow`, `MemoryStore`, `InMemoryStore`,
`ConversationMemory`, `SemanticMemory`, `Document`, `VectorStore`,
`InMemoryVectorStore`, `Retriever`, `Skill`, `SkillRegistry`,
`ComposedSkills`, `Agent`, `AgentRunner`, `SubAgentSpec`, `SubAgentResult`,
`Tool`, `ToolResult`, `ToolRegistry`, `ToolExecutor`, `FunctionTool`,
`ReadFileTool`/`WriteFileTool`/`EditFileTool`/`GlobTool`/`GrepTool`/`BashTool`,
`register_builtin_tools`, `CheckpointManager`, `Checkpoint`,
`PermissionPolicy`/`PermissionRule`/`PermissionDecision`/`PermissionError`,
`GuardedToolExecutor`, `load_project_instructions`, `discover_instructions`,
`AgentServer`, `AgentRequest`, `AgentResponse`, `Plan`, `HookRegistry`,
`HookEvent`, `HookContext`, `HookResult`, `MCPClient`, `StdioTransport`,
`MCPTool`, `register_mcp_tools`, `BackgroundTaskRegistry`, `BackgroundTask`,
`Project`, `CommandRegistry`, `Command`, `default_commands`,
`WorkflowStep`, `WorkflowAgent`, `Route`, `RouterAgent`, `CriticResult`,
`CriticAgent`, `RetrievalSkill`, `GuardrailSkill`, `GuardrailOutcome`,
`WorkflowEvent`.

## 10. Quick reference: how a request flows

1. `AgentServer.handle()` / `AgentRunner.run()` receives a message.
2. `AgentRunner` loads memory, seeds `ExecutionContext` with system prompt +
   history.
3. `ExecutionEngine.chat()` adds the user message and runs the pipeline:
   `CompactionStage → RequestBuilderStage → SupervisorStage → LLMStage →
   ToolLoopStage → MemoryConsolidationStage`.
4. `ToolLoopStage` loops: if `finish_reason == "tool_calls"`, execute tools
   via `tool_executor`, append results, re-run LLM until done.
5. `EventProcessor` turns `StreamEvent`s into context state; events are also
   published on the `EventBus`.
6. `AgentRunner` persists the conversation back to memory.

## 11. Notes for future sessions

- When adding agentic-workflow features, follow the **mirror-the-tools**
  philosophy already established (plan mode, sub-agents, permissions, hooks,
  compaction, memory consolidation, MCP, background tasks, skill scoping,
  reasoning controls).
- **v0.8.0 workflow types** (in `agents/types.py`, `skills/types.py`,
  `commands/registry.py`, `streaming/workflow.py`) are higher-level primitives
  that *compose* existing `Agent`/`Skill`/`Command`/pipeline pieces rather than
  introducing new pipeline stages. `WorkflowAgent` runs a DAG via `AgentRunner`;
  `RouterAgent` dispatches to specialist agents; `CriticAgent` loops
  actor→critic; `RetrievalSkill`/`GuardrailSkill` extend `Skill`; new commands
  are categorized; `WorkflowEvent` surfaces progress.
- **v0.8.1 builtins + self-agentic** (in `agents/builtin.py`, `skills/builtin.py`,
  `commands/builtin.py`, `agents/self_agentic.py`): ready-to-use agent/skill/
  command presets, plus framework self-wiring — `AgentRunner(self_review=True)`
  applies a `CriticAgent` reflexion pass, and `CompactionStage` uses the
  framework's own `summarizer_agent` for LLM-backed compaction (via
  `ContextWindow.fit_async()` which awaits coroutine summarizers).
- **v0.8.2 web integration** (in `web/managers.py`, `web/app.py`,
  `web/static/{index.html,app.js,styles.css}`): the web UI exposes the
  built-in presets via REST endpoints — `GET /api/builtin/{agents,skills,
  commands}` catalogs, `POST /api/builtin/agents/run`,
  `POST /api/builtin/commands/run`, `POST /api/builtin/skills/apply`, and
  `POST /api/builtin/self-review`. `Session.metadata` carries `skills` and
  `self_review` flags.
- Tests for new types live in `tests/agents/test_agent_types.py`,
  `tests/skills/test_skill_types.py`, `tests/commands/test_command_types.py`,
  `tests/agents/test_builtin.py`, and `tests/web/test_web_builtin.py`.
- Keep `ai_runtime/__init__.py` `__all__` in sync with new public symbols.
- Keep `README.md` "Features" / "Agentic capabilities" sections updated when
  shipping new capabilities.
- Tests live under `tests/<subsystem>/` and should use fake providers, not
  real API calls.
