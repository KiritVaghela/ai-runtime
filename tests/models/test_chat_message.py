from ai_runtime.conversation import ChatMessage
from ai_runtime.conversation.enums import MessageRole

def test_helper_constructors():
    assert ChatMessage.user("Hi").role == MessageRole.USER
    assert ChatMessage.system("S").role == MessageRole.SYSTEM
    assert ChatMessage.assistant("A").role == MessageRole.ASSISTANT
