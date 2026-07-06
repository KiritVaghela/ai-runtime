from ai_runtime.conversation import Conversation
from ai_runtime.models import ChatMessage


def test_empty_conversation():

    conversation = Conversation()

    assert conversation.messages == []

def test_add_message():

    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    assert len(
        conversation.messages
    ) == 1


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

    other = conversation.copy()

    assert other.messages == conversation.messages

    assert other is not conversation


def test_append_multiple():

    conversation = Conversation()

    conversation.extend([
        ChatMessage.user("1"),
        ChatMessage.assistant("2"),
    ])

    assert len(
        conversation.messages
    ) == 2