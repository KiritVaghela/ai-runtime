import os,pytest
from ai_runtime import AgentRuntime
from ai_runtime.models import ChatRequest,ChatMessage
from ai_runtime.models.enums import ProviderType

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"),reason="GROQ_API_KEY missing")
async def test_groq_chat():
    rt=AgentRuntime.from_provider(provider=ProviderType.GROQ,model="llama-3.3-70b-versatile",api_key=os.getenv("GROQ_API_KEY"))
    res=await rt.chat(ChatRequest(messages=[ChatMessage.user("Say Hello")]))
    assert res.message.content
