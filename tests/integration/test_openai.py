import os,pytest
from ai_runtime import AgentRuntime
from ai_runtime.conversation import ChatMessage
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers.exceptions import RateLimitError

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"),reason="OPENAI_API_KEY missing")
async def test_openai_chat():
    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    session = runtime.create_session()

    try:

        response = await session.chat(
            ChatMessage.user("Say Hello")
        )
        
        assert response.message.content

    except RateLimitError:
        pytest.skip("OpenAI rate limit exceeded")


    
