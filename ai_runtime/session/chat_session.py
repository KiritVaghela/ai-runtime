from ai_runtime.conversation import Conversation
from ai_runtime.models import (
    ChatMessage,
    ChatRequest,
)


class ChatSession:

    def __init__(
        self,
        provider,
        conversation=None,
    ):
        self.provider = provider
        self.conversation = (
            conversation
            or Conversation()
        )

    async def chat(
        self,
        message: ChatMessage,
    ):

        self.conversation.add(message)

        response = await self.provider.chat(
            ChatRequest(
                messages=self.conversation.messages
            )
        )

        self.conversation.add(
            response.message
        )

        return response
    
    async def chat(
        self,
        request: ChatRequest,
    ):
        self.conversation.extend(
            request.messages
        )

        response = await self.provider.chat(request)

        self.conversation.add(
            response.message
        )

        return response

    def clear(self):
        self.conversation.clear()