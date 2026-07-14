from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebConfig:
    """Web app configuration, sourced from environment variables.

    Mirrors the BYO-provider pattern: point at any OpenAI-compatible endpoint
    via AI_RUNTIME_PROVIDER / AI_RUNTIME_BASE_URL / AI_RUNTIME_API_KEY.
    """

    provider: str = field(default_factory=lambda: os.getenv("AI_RUNTIME_PROVIDER", "openai"))
    model: str = field(default_factory=lambda: os.getenv("AI_RUNTIME_MODEL", "gpt-4o"))
    api_key: str = field(
        default_factory=lambda: os.getenv("AI_RUNTIME_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    )
    base_url: str | None = field(default_factory=lambda: os.getenv("AI_RUNTIME_BASE_URL"))
    host: str = field(default_factory=lambda: os.getenv("AI_RUNTIME_WEB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("AI_RUNTIME_WEB_PORT", "8787")))
    default_project_root: str = field(
        default_factory=lambda: os.getenv("AI_RUNTIME_PROJECT_ROOT", os.getcwd())
    )
    reasoning_effort: str | None = field(
        default_factory=lambda: os.getenv("AI_RUNTIME_REASONING_EFFORT")
    )


def load_config() -> WebConfig:
    return WebConfig()
