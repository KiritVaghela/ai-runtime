# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
