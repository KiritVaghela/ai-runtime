from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .skill import Skill


# ---------------------------------------------------------------------------
# RetrievalSkill — RAG-backed skill that injects retrieved context
# ---------------------------------------------------------------------------


class RetrievalSkill(Skill):
    """A skill that augments the system prompt with retrieved context.

    Mirrors the retrieval-augmented skill pattern of modern agentic
    workflows: before the LLM is called, the skill queries its `Retriever`
    (a `ai_runtime.rag.Retriever`) for the most relevant documents and folds
    them into the prompt as grounded context. The retrieval query can be
    templated on the incoming task.
    """

    def __init__(
        self,
        name: str,
        description: str,
        retriever: Any,
        system_prompt: str | None = None,
        retrieval_top_k: int = 4,
        retrieval_query_template: str | None = None,
        tools: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        paths: list[str] | None = None,
        globs: list[str] | None = None,
    ):
        super().__init__(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools or [],
            metadata=metadata or {},
            paths=paths or [],
            globs=globs or [],
            retriever=retriever,
            retrieval_top_k=retrieval_top_k,
            retrieval_query_template=retrieval_query_template,
        )

    async def retrieve_context(self, task: str) -> str:
        """Query the retriever and return formatted context for the prompt."""
        query = self.retrieval_query_template or "{task}"
        try:
            query = query.format(task=task)
        except (KeyError, IndexError):
            pass
        return await self.retriever.context(query)


# ---------------------------------------------------------------------------
# GuardrailSkill — validation hook that gates model output
# ---------------------------------------------------------------------------


@dataclass
class GuardrailOutcome:
    """Result of running a guardrail over model output."""

    passed: bool
    message: str
    action: str  # reject | warn | rewrite
    rewritten: str | None = None


class GuardrailSkill(Skill):
    """A skill that validates model output via a `guardrail` callable.

    Mirrors the output-validation / policy layer of agentic frameworks
    (content filters, schema checks, safety gates). The `guardrail` callable
    receives the raw output and returns ``(passed, message)``. On failure the
    skill either rejects the output, warns and passes it through, or rewrites
    it (when the callable returns a rewritten string as ``message`` and
    ``guardrail_on_fail == "rewrite"``).
    """

    def __init__(
        self,
        name: str,
        description: str,
        guardrail: Callable[[str], tuple[bool, str]],
        on_fail: str = "reject",
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools or [],
            metadata=metadata or {},
            guardrail=guardrail,
            guardrail_on_fail=on_fail,
        )

    def evaluate(self, output: str) -> GuardrailOutcome:
        passed, message = self.guardrail(output)
        if passed:
            return GuardrailOutcome(True, message, self.guardrail_on_fail)
        action = self.guardrail_on_fail
        rewritten = message if action == "rewrite" else None
        return GuardrailOutcome(False, message, action, rewritten=rewritten)
