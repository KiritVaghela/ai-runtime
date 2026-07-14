Provider contract for ai_runtime
===============================

Overview
--------
The `LLMProvider` contract defines a minimal async interface that provider
implementations must follow so the runtime can interact with any LLM backend
in a uniform way.

Core expectations
- `chat(request: ChatRequest) -> ChatResponse` (async): perform a single
  completion for the given request. Providers should honor `request.metadata`
  for provider-specific options and `request.tool_calls` if tool-use is
  supported.
- `stream(request: ChatRequest) -> AsyncIterator[StreamEvent]` (async): yield
  `StreamEvent` objects representing partial output, usage updates, and a
  final completion event. Provider streams should allow the consumer to cancel
  iteration (e.g., by closing the iterator or by the runtime cancelling the
  task). If a provider cannot support streaming, it should raise a clearly
  documented exception.
- `list_models() -> list[str]` (async): return available model identifiers.
- `info` property: return `ProviderInfo` with `ProviderCapabilities` indicating
  supported features (tools, streaming, vision, etc.).

Cancellation & Timeouts
-----------------------
Providers should respect `ProviderConfig.timeout` and the runtime's cancellation
signals. Long-running blocking calls should be executed in an executor or via
async client libraries to allow cooperative cancellation.

Tooling
-------
If `ProviderInfo.capabilities.tools` is true, the provider should provide a
mechanism to accept `request.tool_calls` or similar directives and should
emit `ToolResultEvent` or `ToolErrorEvent` via the runtime's `EventBus`.

Backward compatibility
----------------------
The runtime will first pass `ChatRequest` objects. New optional fields in the
request (`metadata`, `tool_calls`) are non-breaking — providers that ignore
them will continue to work.
