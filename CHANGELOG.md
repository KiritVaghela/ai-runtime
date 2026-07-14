# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
