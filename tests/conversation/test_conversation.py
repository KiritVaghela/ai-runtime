from ai_runtime.conversation import Conversation
from ai_runtime.models import ChatMessage


def test_new_conversation_is_empty():
    conversation = Conversation()

    assert conversation.messages == []


def test_add_message():
    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    assert len(conversation.messages) == 1
    assert conversation.messages[0].content == "Hello"


def test_extend_messages():
    conversation = Conversation()

    conversation.extend([
        ChatMessage.user("Hi"),
        ChatMessage.assistant("Hello"),
    ])

    assert len(conversation.messages) == 2


def test_clear():
    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    conversation.clear()

    assert conversation.messages == []


def test_copy():
    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    copy = conversation.copy()

    assert copy.messages == conversation.messages
    assert copy is not conversation