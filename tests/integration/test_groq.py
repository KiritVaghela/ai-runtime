import os,pytest
from ai_runtime import AgentRuntime
from ai_runtime.conversation import ChatMessage
from ai_runtime.providers.enums import ProviderType

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"),reason="GROQ_API_KEY missing")
async def test_groq_chat():
    runtime = AgentRuntime.from_provider(
        provider=ProviderType.GROQ,
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    session = runtime.create_session()

    response = await session.chat(
        ChatMessage.user("Say Hello")
    )

    assert response.message.content
