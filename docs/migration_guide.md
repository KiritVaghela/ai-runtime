# Migration Guide

This guide covers migrating to the current provider-agnostic runtime
(`ai_runtime` >= 0.1.0).

## Key concepts

- `AgentRuntime` — entrypoint that builds sessions from a `ProviderRegistry`.
- `Session` — wraps an `ExecutionContext` and `ExecutionEngine`.
- `ProviderRegistry` — maps `ProviderType` to provider classes. It can be
  frozen and supports plugin discovery.
- `LLMProvider` / `BaseProvider` — the unified provider contract.
- `ChatRequest` / `ChatResponse` — provider-agnostic conversation models.
- `StreamEvent` — streaming events (`TextDeltaEvent`, `UsageEvent`,
  `CompletedEvent`, `ErrorEvent`).

## Migrating from a single-provider client

### Before (hypothetical direct client)

```python
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
resp = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
print(resp.choices[0].message.content)
```

### After (ai_runtime)

```python
import os

from ai_runtime import AgentRuntime
from ai_runtime.conversation import ChatMessage
from ai_runtime.providers.enums import ProviderType

runtime = AgentRuntime.from_provider(
    provider=ProviderType.OPENAI,
    model="gpt-4.1-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

session = runtime.create_session()

response = await session.chat(ChatMessage.user("Hello"))
print(response.message.content)
```

## Migrating to the unified provider contract

If you previously implemented a provider with ad-hoc methods, switch to the
`LLMProvider` contract:

| Old pattern | New contract |
| --- | --- |
| `complete(request)` | `async def chat(self, request) -> ChatResponse` |
| `stream(request)` returning raw chunks | `async def stream(self, request) -> AsyncIterator[StreamEvent]` |
| `models()` | `async def list_models(self) -> list[str]` (optional) |
| manual cleanup | `async def close(self) -> None` (optional) |

`BaseProvider` provides `validate_request(request)` and `map_exception(ex)`
helpers. Inherit from it instead of `LLMProvider` directly when possible.

## Streaming timeout changes

`ChatRequest` now supports a `timeout` field. The `ExecutionEngine.stream`
loop enforces per-event timeouts and emits an `ErrorEvent` on stall or
exception. If you previously relied on unbounded streams, set an explicit
`timeout` or rely on `ProviderConfig.timeout` (default `60.0s`).

```python
from ai_runtime.conversation import ChatMessage, ChatRequest

request = ChatRequest(
    messages=[ChatMessage.user("Write a poem.")],
    timeout=10.0,
)

async for event in session.stream(request):
    ...
```

## Registry changes

- `ProviderRegistry.register(...)` raises `RuntimeError` after `freeze()`.
- Use `list_providers()` to inspect registered providers.
- Use `discover(entry_point_group)` to load plugin providers from installed
  packages.

## Exception mapping

Provider-specific errors should be mapped to `ai_runtime.providers.exceptions`
types (e.g. `RateLimitError`, `TimeoutError`, `ProviderError`). The LiteLLM
adapter demonstrates this via `LiteLLMExceptionMapper`.
