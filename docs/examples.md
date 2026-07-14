# Examples

Quick reference for common `ai_runtime` usage.

## Create a runtime

```python
import os

from ai_runtime import AgentRuntime
from ai_runtime.providers.enums import ProviderType

runtime = AgentRuntime.from_provider(
    provider=ProviderType.GROQ,
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)

session = runtime.create_session()
```

## Chat

```python
from ai_runtime.conversation import ChatMessage

response = await session.chat(ChatMessage.user("Hello!"))
print(response.message.content)
```

## Stream

```python
from ai_runtime.conversation import ChatMessage
from ai_runtime.streaming import TextDeltaEvent

async for event in session.stream(ChatMessage.user("Write a haiku.")):
    if isinstance(event, TextDeltaEvent):
        print(event.delta, end="")
```

## Stream with timeout

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
        print("\nStream error:", event.message)
```

## Custom provider registry

```python
from ai_runtime import AgentRuntime
from ai_runtime.providers import ProviderRegistry
from ai_runtime.providers.enums import ProviderType

registry = ProviderRegistry()
registry.register(ProviderType.OPENAI, MyProvider)

runtime = AgentRuntime.from_provider(
    provider=ProviderType.OPENAI,
    model="gpt-4.1",
    api_key=os.getenv("OPENAI_API_KEY"),
    registry=registry,
)
```

## Provider capabilities

```python
info = session.context.provider.info
print(info.capabilities.tools)
print(info.capabilities.streaming)
```

## Conversation history

```python
# The session accumulates messages automatically.
print(len(session.context.conversation.messages))
```

## Running tests

```bash
pytest
```

Integration tests that hit live APIs are skipped unless the relevant API key
is present in the environment.
