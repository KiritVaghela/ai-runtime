from __future__ import annotations


from ai_runtime.conversation import Conversation


class ConversationMemory:
    """Persists conversation history across sessions/turns.

    Backed by a `MemoryStore` keyed by a conversation id. The working
    `Conversation` is held in memory and flushed to the store on save.
    """

    def __init__(
        self,
        store,
        conversation_id: str = "default",
    ):
        self._store = store
        self._conversation_id = conversation_id
        self._conversation = Conversation()

    @property
    def conversation(self) -> Conversation:
        return self._conversation

    async def load(self) -> Conversation:
        raw = await self._store.get(self._key())
        if raw is not None:
            self._conversation = raw
        return self._conversation

    async def save(self) -> None:
        await self._store.set(self._key(), self._conversation)

    async def clear(self) -> None:
        self._conversation = Conversation()
        await self._store.delete(self._key())

    def _key(self) -> str:
        return f"conversation:{self._conversation_id}"
