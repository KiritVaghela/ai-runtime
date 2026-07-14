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
-   Rich streaming events: text, usage, tool call, tool result, thinking, permission
-   Execution engine and pipeline stages
-   Provider metadata, capabilities, and request mapping
-   Fully tested runtime and provider integration coverage

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

Current status:

-   Provider registry with custom provider registration
-   Streaming response support with timeouts and completion events
-   Session-based execution and conversation accumulation
-   Provider integration coverage with test doubles

## Roadmap

### v0.3.x

-   Tool registry
-   Tool execution
-   Permission manager
-   Filesystem tools
-   Bash tools

### Future

-   MCP support
-   Multi-agent workflows
-   Desktop and terminal integrations
-   AI Factory integration

## Publishing to PyPI

1.  Update version in `pyproject.toml`.
2.  Build:

```bash
python -m build
```

3.  Check:

```bash
twine check dist/*
```

4.  Upload to TestPyPI:

```bash
twine upload --repository testpypi dist/*
```

5.  Upload to PyPI:

```bash
twine upload dist/*
```

