# AI Runtime

AI Runtime is a provider-agnostic Python runtime for building AI
applications and agent workflows.

## Features

-   Provider abstraction (LiteLLM-based)
-   OpenAI, Groq and other LiteLLM providers
-   Conversation management
-   Chat sessions
-   Streaming responses
-   Execution engine & execution pipeline
-   Event bus for execution events
-   Provider registry and metadata
-   Fully tested (57+ tests)

## Installation

### From PyPI

``` bash
pip install ai-runtime
```

### From source

``` bash
git clone https://github.com/KiritVaghela/ai-runtime.git
cd ai-runtime
pip install -e .
```

## Quick Start

``` python
import os

from ai_runtime import AgentRuntime
from ai_runtime.conversation import ChatMessage
from ai_runtime.models.enums import ProviderType

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

``` python
from ai_runtime.streaming import TextDeltaEvent

async for event in session.stream(
    ChatMessage.user("Write a haiku.")
):
    if isinstance(event, TextDeltaEvent):
        print(event.delta, end="")
```

## Architecture

    AgentRuntime
        └── Session
              └── ExecutionEngine
                    └── ExecutionPipeline
                          ├── RequestBuilderStage
                          ├── LLMStage
                          └── EventProcessor

## Testing

``` bash
pytest
```

Current status:

-   57 passing tests
-   Provider integrations
-   Streaming support
-   Session-based execution

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

``` bash
python -m build
```

3.  Check:

``` bash
twine check dist/*
```

4.  Upload to TestPyPI:

``` bash
twine upload --repository testpypi dist/*
```

5.  Upload to PyPI:

``` bash
twine upload dist/*
```

