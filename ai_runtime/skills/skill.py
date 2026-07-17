from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Skill:
    """A reusable, composable unit of agent behavior.

    A skill bundles a system-prompt fragment, an optional set of tools, and
    an optional `run` hook that can transform the request/context before the
    LLM is called. Skills let users ship named capabilities (e.g. "summarize",
    "translate", "sql-analyst") without writing a full agent.
    """

    name: str
    description: str
    system_prompt: str | None = None
    tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    run: Callable[..., Any] | None = None
    # Scoping (mirrors Claude Code / Cursor skill path-scoping):
    paths: list[str] = field(default_factory=list)  # path prefixes where active
    globs: list[str] = field(default_factory=list)  # file-glob triggers
    disable_model_invocation: bool = False  # if True, skill is manual-only

    # RetrievalSkill config (RAG-backed skill): when set, the skill injects
    # retrieved context into the system prompt before the LLM is called.
    retriever: Any | None = None  # an `ai_runtime.rag.Retriever` instance
    retrieval_top_k: int = 4
    retrieval_query_template: str | None = None  # receives `task`

    # GuardrailSkill config (validation hook): when set, the skill validates
    # the model output and may rewrite/reject it before it is returned.
    guardrail: Callable[[str], tuple[bool, str]] | None = None
    # signature: (output: str) -> (passed: bool, message: str)
    guardrail_on_fail: str = "reject"  # "reject" | "warn" | "rewrite"
