from __future__ import annotations

from typing import Callable

from ai_runtime.conversation import Conversation


class SemanticMemory:
    """Compresses older conversation turns into a running summary.

    Used by `ContextWindow` as a `summarizer` hook so long conversations
    stay within the token budget without losing context. The summarizer is
    any callable that takes a `Conversation` and returns a summary string
    (e.g. an LLM call or a heuristic extractor).
    """

    def __init__(
        self,
        summarizer: Callable[[Conversation], str],
        preserve_recent: int = 4,
    ):
        self._summarizer = summarizer
        self._preserve_recent = preserve_recent
        self._summary: str = ""

    @property
    def summary(self) -> str:
        return self._summary

    def summarize(self, conversation: Conversation) -> str:
        # recent = conversation.messages[-self._preserve_recent:]
        prior = conversation.messages[:-self._preserve_recent] if len(
            conversation.messages
        ) > self._preserve_recent else []

        if not prior:
            return self._summary

        prior_conv = Conversation()
        prior_conv.extend(prior)

        new_summary = self._summarizer(prior_conv)
        # Accumulate so earlier context is not lost on each compaction.
        self._summary = f"{self._summary}\n{new_summary}".strip()
        return self._summary

    def compact(self, conversation: Conversation) -> Conversation:
        summary = self.summarize(conversation)
        from ai_runtime.conversation import ChatMessage

        result = Conversation()
        if summary:
            result.add(ChatMessage.system(f"Summary of earlier context:\n{summary}"))
        result.extend(conversation.messages[-self._preserve_recent:])
        return result
