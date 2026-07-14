# Adapter Tutorial

This tutorial shows how to implement a custom provider adapter for
`ai_runtime`. Adapters translate between the runtime's provider-agnostic
models and a specific backend SDK.

## 1. Implement the provider contract

Inherit from `BaseProvider` and implement `info`, `chat`, and `stream`.

```python
from typing import AsyncIterator

from ai_runtime.conversation import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Usage,
)
from ai_runtime.providers import (
    BaseProvider,
    ProviderConfig,
    ProviderInfo,
    ProviderCapabilities,
    SDKInfo,
)
from ai_runtime.streaming import (
    CompletedEvent,
    StreamEvent,
    TextDeltaEvent,
)


class MyProvider(BaseProvider):

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider=self.config.provider,
            model=self.config.model,
            sdkInfo=SDKInfo(sdk="MySDK", version="1.0"),
            capabilities=ProviderCapabilities(
                chat=True,
                streaming=True,
            ),
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.validate_request(request)

        # Call your backend SDK here and map the response.
        text = "Hello"

        return ChatResponse(
            message=ChatMessage.assistant(text),
            usage=Usage(
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
            ),
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        self.validate_request(request)

        yield TextDeltaEvent(delta="Hel")
        yield TextDeltaEvent(delta="lo")
        yield CompletedEvent(finish_reason="stop")
```

## 2. Map requests and responses

For non-trivial backends, keep mapping logic in a dedicated mapper so the
provider stays thin. The LiteLLM adapter uses `LiteLLMMapper` and
`LiteLLMResponseAdapter` for this.

```python
class MyMapper:

    @staticmethod
    def to_request(config: ProviderConfig, request: ChatRequest) -> dict:
        return {
            "model": config.model,
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
```

## 3. Map exceptions

Convert backend errors into runtime exceptions so callers get a consistent
interface.

```python
from ai_runtime.providers.exceptions import ProviderError

try:
    ...
except Exception as ex:
    raise self.map_exception(ex)
```

## 4. Register the provider

```python
from ai_runtime import AgentRuntime
from ai_runtime.providers import ProviderRegistry
from ai_runtime.providers.enums import ProviderType

registry = ProviderRegistry()
registry.register(ProviderType.OPENAI, MyProvider)

runtime = AgentRuntime.from_provider(
    provider=ProviderType.OPENAI,
    model="my-model",
    registry=registry,
)
```

## 5. Test with a double

Use a fake provider in tests to avoid network calls:

```python
class FakeProvider(MyProvider):
    async def chat(self, request):
        return ChatResponse(message=ChatMessage.assistant("Hello"))
```

See `tests/integration/test_provider_doubles.py` for full examples.
