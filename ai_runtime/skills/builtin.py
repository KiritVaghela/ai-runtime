from __future__ import annotations

from typing import Any

from .skill import Skill
from .types import RetrievalSkill, GuardrailSkill


# ---------------------------------------------------------------------------
# Built-in skill presets
#
# Ready-to-use `Skill` (and `RetrievalSkill` / `GuardrailSkill`) instances that
# ship with the framework. They let any agent gain named capabilities without
# writing a full agent, and several are wired into the framework itself to make
# it more agentic (e.g. self-review, output guardrails).
# ---------------------------------------------------------------------------


def self_review_skill() -> Skill:
    """A skill that instructs the agent to self-review before answering.

    Composes into an agent's system prompt; pairs naturally with a
    `CriticAgent` for a reflexion loop.
    """
    return Skill(
        name="self_review",
        description="Critically review your own draft before finalizing.",
        system_prompt=(
            "Before finalizing, critically review your own draft for "
            "correctness, completeness, and risks. Fix issues you find, then "
            "output the improved version."
        ),
    )


def explain_code_skill() -> Skill:
    """A skill that biases the agent toward clear, example-driven explanations."""
    return Skill(
        name="explain_code",
        description="Explain code and concepts clearly with examples.",
        system_prompt=(
            "Explain using concrete examples and analogies where helpful. "
            "Structure the answer: what it does, why, and a short example."
        ),
    )


def generate_tests_skill() -> Skill:
    """A skill that biases the agent toward writing focused, runnable tests."""
    return Skill(
        name="generate_tests",
        description="Generate focused, runnable unit tests.",
        system_prompt=(
            "Generate tests that are runnable and follow the project's "
            "conventions. Cover happy paths, edge cases, and failure modes. "
            "Prefer table-driven or parameterized tests where appropriate."
        ),
    )


def summarize_skill() -> Skill:
    """A skill that biases the agent toward dense, decision-preserving summaries."""
    return Skill(
        name="summarize",
        description="Produce dense summaries preserving decisions and learnings.",
        system_prompt=(
            "Summarize densely. Preserve decisions, facts, open questions, and "
            "any `LEARNING:` lines. Output only the summary."
        ),
    )


def no_secrets_guardrail() -> GuardrailSkill:
    """A guardrail that blocks outputs containing obvious secret patterns."""

    def _check(output: str) -> tuple[bool, str]:
        lowered = output.lower()
        for token in ("api_key=", "apikey:", "secret=", "password=", "bearer "):
            if token in lowered:
                return False, f"output contains a likely secret ({token})"
        return True, "no secrets detected"

    return GuardrailSkill(
        name="no_secrets",
        description="Block outputs that leak secrets/tokens.",
        guardrail=_check,
        on_fail="reject",
    )


def retrieval_skill(retriever: Any, name: str = "kb", description: str = "Knowledge-base retrieval") -> RetrievalSkill:
    """A RAG-backed skill built on the given `ai_runtime.rag.Retriever`."""
    return RetrievalSkill(
        name=name,
        description=description,
        retriever=retriever,
        system_prompt=(
            "Use the retrieved context to ground your answer. Cite the source "
            "material where relevant and do not contradict it."
        ),
    )


def default_builtin_skills() -> list[Skill]:
    """The set of built-in skills registered by `default_skill_registry()`."""
    return [
        self_review_skill(),
        explain_code_skill(),
        generate_tests_skill(),
        summarize_skill(),
        no_secrets_guardrail(),
    ]
