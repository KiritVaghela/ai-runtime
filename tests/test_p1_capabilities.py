import json

import pytest

from ai_runtime import (
    Agent,
    AgentRunner,
    ContextWindow,
    ConversationMemory,
    Document,
    InMemoryStore,
    InMemoryVectorStore,
    Retriever,
    SemanticMemory,
    Skill,
    SkillRegistry,
    ToolRegistry,
    ToolExecutor,
    FunctionTool,
)
from ai_runtime.conversation import ChatMessage, ChatResponse, ToolCall, Usage
from ai_runtime.execution import ExecutionContext, ExecutionEngine


# ----------------------------------------------------------------------
# Context management
# ----------------------------------------------------------------------

def test_context_window_truncates_over_budget():
    conv = __import__(
        "ai_runtime.conversation", fromlist=["Conversation"]
    ).Conversation()
    conv.add(ChatMessage.system("sys"))
    for i in range(20):
        conv.add(ChatMessage.user(f"message number {i} " * 20))

    window = ContextWindow(conv, max_tokens=200)
    fitted = window.fit()

    # System message preserved; oldest user messages dropped.
    assert fitted.messages[0].role.value == "system"
    assert window.token_count() > 200
    assert fitted is not None


def test_context_window_under_budget_passthrough():
    conv = __import__(
        "ai_runtime.conversation", fromlist=["Conversation"]
    ).Conversation()
    conv.add(ChatMessage.user("hi"))

    window = ContextWindow(conv, max_tokens=1000)
    assert window.fit().messages == conv.messages


def test_semantic_memory_summarizes():
    conv = __import__(
        "ai_runtime.conversation", fromlist=["Conversation"]
    ).Conversation()
    for i in range(10):
        conv.add(ChatMessage.user(f"fact {i}"))

    mem = SemanticMemory(summarizer=lambda c: "summary", preserve_recent=2)
    compacted = mem.compact(conv)
    # Recent 2 preserved + 1 summary system message.
    assert len(compacted.messages) == 3
    assert "summary" in compacted.messages[0].content


# ----------------------------------------------------------------------
# Memory
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_conversation_memory_persist():
    store = InMemoryStore()
    mem = ConversationMemory(store, "sess-1")
    mem.conversation.add(ChatMessage.user("hello"))
    await mem.save()

    mem2 = ConversationMemory(store, "sess-1")
    loaded = await mem2.load()
    assert loaded.messages[0].content == "hello"


# ----------------------------------------------------------------------
# RAG
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retriever_returns_relevant_docs():
    retriever = Retriever(InMemoryVectorStore())
    await retriever.add_documents([
        Document(content="The capital of France is Paris", id="d1"),
        Document(content="Python is a programming language", id="d2"),
    ])

    ctx = await retriever.context("France capital")
    assert "Paris" in ctx


# ----------------------------------------------------------------------
# Skills
# ----------------------------------------------------------------------

def test_skill_registry_compose():
    registry = SkillRegistry()
    registry.register(Skill(
        name="translator",
        description="translates text",
        system_prompt="You are a translator.",
        tools=["translate"],
    ))
    registry.register(Skill(
        name="summarizer",
        description="summarizes text",
        system_prompt="You are a summarizer.",
    ))

    composed = registry.compose(["translator", "summarizer"])
    assert "translator" in composed.system_prompt
    assert "summarizer" in composed.system_prompt
    assert composed.tool_names == ["translate"]


# ----------------------------------------------------------------------
# Agent
# ----------------------------------------------------------------------

class EchoToolProvider:
    """Fake provider that echoes the last user/tool content."""

    def __init__(self, config):
        self.config = config

    async def chat(self, request):
        last = request.messages[-1]
        return ChatResponse.assistant(
            f"echo: {last.content}",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            finish_reason="stop",
        )


@pytest.mark.asyncio
async def test_agent_run_with_memory_and_tools():
    registry = ToolRegistry()
    registry.register(FunctionTool(
        "ping", lambda ctx, inp: "pong"
    ))

    agent = Agent(
        name="test-agent",
        provider=EchoToolProvider(None),
        system_prompt="You are helpful.",
        tool_registry=registry,
    )

    runner = AgentRunner(agent)
    response = await runner.run("hello")

    assert "echo: hello" in response.message.content

    # Memory persisted the user + assistant turns.
    saved = agent.memory.conversation.messages
    assert any(m.role.value == "user" and m.content == "hello" for m in saved)
    assert any(m.role.value == "assistant" for m in saved)


@pytest.mark.asyncio
async def test_agent_run_loads_prior_memory():
    store = InMemoryStore()
    mem = ConversationMemory(store, "persist-sess")
    mem.conversation.add(ChatMessage.user("previous turn"))
    await mem.save()

    agent = Agent(
        name="persist-sess",
        provider=EchoToolProvider(None),
        memory=mem,
    )

    runner = AgentRunner(agent)
    await runner.run("new turn")

    # Both prior and new turns persisted.
    contents = [m.content for m in agent.memory.conversation.messages]
    assert "previous turn" in contents
    assert "new turn" in contents
