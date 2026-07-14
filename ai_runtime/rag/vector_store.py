from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .document import Document


class VectorStore(ABC):
    """Interface for embedding-based document storage and similarity search.

    Implementations may use in-memory cosine similarity, a local FAISS index,
    or a managed vector database. The embedding function is injected so the
    store stays provider-agnostic.
    """

    @abstractmethod
    async def add(self, documents: list[Document]) -> None:
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 4,
    ) -> list[tuple[Document, float]]:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...


class InMemoryVectorStore(VectorStore):
    """Reference implementation using an injected embedder + cosine similarity."""

    def __init__(self, embedder: Any = None):
        self._embedder = embedder
        self._docs: list[Document] = []
        self._vectors: list[list[float]] = []

    async def add(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs.append(doc)
            self._vectors.append(self._embed(doc.content))

    async def search(
        self,
        query: str,
        top_k: int = 4,
    ) -> list[tuple[Document, float]]:
        if not self._docs:
            return []

        q = self._embed(query)
        scored = [
            (doc, self._cosine(q, vec))
            for doc, vec in zip(self._docs, self._vectors)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def clear(self) -> None:
        self._docs.clear()
        self._vectors.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> list[float]:
        if self._embedder is not None:
            result = self._embedder(text)
            if hasattr(result, "__await__"):
                import asyncio
                return asyncio.get_event_loop().run_until_complete(result)
            return list(result)
        # Deterministic hash-based pseudo-embedding for tests/offline use.
        vec = [0.0] * 8
        for i, ch in enumerate(text.encode("utf-8")):
            vec[i % 8] += ch
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5 or 1.0
        nb = sum(y * y for y in b) ** 0.5 or 1.0
        return dot / (na * nb)
