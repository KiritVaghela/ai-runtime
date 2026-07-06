from ai_runtime.providers.config import ProviderConfig
from ai_runtime.models.enums import ProviderType

def test_model_resolution():
    cfg=ProviderConfig(provider=ProviderType.OPENAI,model="gpt-4.1")
    assert cfg.litellm_model=="openai/gpt-4.1"

def test_prefixed_model_passthrough():
    cfg=ProviderConfig(provider=ProviderType.GROQ,model="groq/llama-3.3-70b-versatile")
    assert cfg.litellm_model=="groq/llama-3.3-70b-versatile"
