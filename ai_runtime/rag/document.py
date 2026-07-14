from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """A retrievable unit of text with optional metadata."""

    content: str
    id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
