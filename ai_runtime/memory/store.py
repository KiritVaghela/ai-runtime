from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryStore(ABC):
    """Pluggable key/value memory backend.

    Implementations may be in-memory, Redis-backed, SQL, or a vector store.
    The interface is intentionally minimal so agents can persist arbitrary
    structured state across turns.
    """

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        ...

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def list_keys(self) -> list[str]:
        ...


class InMemoryStore(MemoryStore):
    """Default process-local memory store."""

    def __init__(self):
        self._data: dict[str, Any] = {}

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    async def get(self, key: str) -> Any | None:
        return self._data.get(key)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def list_keys(self) -> list[str]:
        return list(self._data.keys())
