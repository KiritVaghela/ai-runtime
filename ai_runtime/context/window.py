from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from ai_runtime.conversation import Conversation


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for budgeting.

    This is provider-agnostic and intentionally cheap. Providers that expose
    accurate tokenizers can supply a custom estimator to `ContextWindow`.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


class TruncationStrategy(ABC):
    """Decides how to shrink a conversation that exceeds the token budget."""

    @abstractmethod
    def truncate(self, conversation: Conversation) -> Conversation:
        ...


class DropOldestStrategy(TruncationStrategy):
    """Drops the oldest non-system messages until under budget.

    System messages are always preserved so the model keeps its instructions.
    """

    def __init__(self, max_tokens: int, estimator: Callable[[str], int] = estimate_tokens):
        self.max_tokens = max_tokens
        self.estimator = estimator

    def truncate(self, conversation: Conversation) -> Conversation:
        system = [m for m in conversation.messages if m.role.value == "system"]
        rest = [m for m in conversation.messages if m.role.value != "system"]

        # Keep system messages plus as many of the most recent turns as fit.
        kept = list(system)
        total = sum(self.estimator(str(m.content)) for m in kept)

        # Add recent messages from the end until the budget is exceeded.
        for m in reversed(rest):
            cost = self.estimator(str(m.content))
            if total + cost > self.max_tokens and len(kept) > len(system):
                break
            kept.append(m)
            total += cost

        # Restore chronological order.
        kept = system + kept[len(system):][::-1]

        result = Conversation()
        result.extend(kept)
        return result


class ContextWindow:
    """Manages a conversation within a token budget.

    Wraps a `Conversation` and applies a `TruncationStrategy` when the
    estimated token count exceeds `max_tokens`. An optional `summarizer`
    hook can compress older turns instead of dropping them.
    """

    def __init__(
        self,
        conversation: Conversation | None = None,
        max_tokens: int = 8000,
        strategy: TruncationStrategy | None = None,
        estimator: Callable[[str], int] = estimate_tokens,
        summarizer: Callable[[Conversation], str] | None = None,
    ):
        self.conversation = conversation or Conversation()
        self.max_tokens = max_tokens
        self.strategy = strategy or DropOldestStrategy(max_tokens, estimator)
        self.estimator = estimator
        self.summarizer = summarizer

    def token_count(self) -> int:
        return sum(
            self.estimator(str(m.content)) for m in self.conversation.messages
        )

    def is_over_budget(self) -> bool:
        return self.token_count() > self.max_tokens

    def fit(self) -> Conversation:
        """Return a budget-compliant copy of the conversation."""
        if not self.is_over_budget():
            return self.conversation.copy()

        if self.summarizer is not None:
            summary = self.summarizer(self.conversation)
            compacted = Conversation()
            compacted.add(
                self.conversation.messages[0]
                if self.conversation.messages
                and self.conversation.messages[0].role.value == "system"
                else __import__(
                    "ai_runtime.conversation", fromlist=["ChatMessage"]
                ).ChatMessage.system(summary)
            )
            return compacted

        return self.strategy.truncate(self.conversation)
