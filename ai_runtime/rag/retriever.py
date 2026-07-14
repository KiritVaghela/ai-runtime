from __future__ import annotations

from typing import Any

from .document import Document
from .vector_store import VectorStore, InMemoryVectorStore


class Retriever:
    """High-level RAG retrieval: query a `VectorStore` and format context.

    The optional `formatter` controls how retrieved documents are rendered
    into a prompt context string (default: numbered text blocks).
    """

    def __init__(
        self,
        store: VectorStore | None = None,
        top_k: int = 4,
        formatter: Any = None,
    ):
        self._store = store or InMemoryVectorStore()
        self._top_k = top_k
        self._formatter = formatter or self._default_formatter

    async def add_documents(self, documents: list[Document]) -> None:
        await self._store.add(documents)

    async def retrieve(self, query: str) -> list[tuple[Document, float]]:
        return await self._store.search(query, top_k=self._top_k)

    async def context(self, query: str) -> str:
        results = await self.retrieve(query)
        return self._formatter([doc for doc, _ in results])

    @staticmethod
    def _default_formatter(documents: list[Document]) -> str:
        if not documents:
            return ""
        blocks = [f"[{i + 1}] {doc.content}" for i, doc in enumerate(documents)]
        return "\n\n".join(blocks)
