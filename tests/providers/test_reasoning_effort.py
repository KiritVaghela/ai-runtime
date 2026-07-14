from __future__ import annotations

import pytest

from ai_runtime.providers.config import ProviderConfig
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers.capabilities import ProviderCapabilities
from ai_runtime.providers.litellm_mapper import LiteLLMMapper
from ai_runtime.conversation import ChatRequest, ChatMessage


def test_reasoning_effort_forwarded_when_capable():
    cfg = ProviderConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4o",
        reasoning_effort="high",
        thinking_enabled=True,
        thinking_budget_tokens=1000,
    )
    caps = ProviderCapabilities(reasoning=True)
    req = ChatRequest(messages=[ChatMessage.user("think hard")])
    payload = LiteLLMMapper.to_request(cfg, req, caps)

    assert payload["reasoning_effort"] == "high"
    assert payload["thinking"] == {"type": "enabled", "budget_tokens": 1000}


def test_reasoning_not_forwarded_when_uncapable():
    cfg = ProviderConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4o",
        reasoning_effort="high",
    )
    caps = ProviderCapabilities(reasoning=False)
    req = ChatRequest(messages=[ChatMessage.user("hi")])
    payload = LiteLLMMapper.to_request(cfg, req, caps)

    assert "reasoning_effort" not in payload
    assert "thinking" not in payload
