from __future__ import annotations

import os

import pytest

from ai_runtime.providers.config import ProviderConfig


@pytest.mark.asyncio
async def test_from_env_builds_byo_config(monkeypatch):
    monkeypatch.setenv("COPILOT_PROVIDER_TYPE", "openai")
    monkeypatch.setenv("COPILOT_PROVIDER_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("COPILOT_PROVIDER_API_KEY", "x")
    monkeypatch.setenv("COPILOT_MODEL", "llama3")

    cfg = ProviderConfig.from_env()
    assert cfg.base_url == "http://localhost:11434"
    assert cfg.litellm_model == "openai/llama3"


@pytest.mark.asyncio
async def test_from_env_default_when_unset(monkeypatch):
    for v in (
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "COPILOT_MODEL",
    ):
        monkeypatch.delenv(v, raising=False)
    cfg = ProviderConfig.from_env()
    assert cfg.provider.value == "openai"
    assert cfg.litellm_model == "openai/local-model"
