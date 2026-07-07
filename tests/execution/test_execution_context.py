from ai_runtime.execution import ExecutionContext
from ai_runtime.conversation import Conversation


class DummyProvider:
    pass


def test_context_creation():

    context = ExecutionContext(
        provider=DummyProvider(),
        conversation=Conversation(),
    )

    assert context.provider is not None
    assert context.conversation is not None


def test_context_metadata():

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    context.metadata["user"] = "kirit"

    assert context.metadata["user"] == "kirit"

def test_context_variables():

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    context.variables["cwd"] = "/tmp"

    assert context.variables["cwd"] == "/tmp"