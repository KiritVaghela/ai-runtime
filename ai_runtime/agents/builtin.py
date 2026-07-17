from __future__ import annotations

from typing import Any

from .agent import Agent
from .types import RouterAgent, Route, CriticAgent


# ---------------------------------------------------------------------------
# Built-in agent presets
#
# These are ready-to-use `Agent` (and higher-level) instances that ship with
# the framework and exercise its own capabilities — turning the runtime into
# a more agentic system that can review, explain, test, and route work using
# the same primitives it exposes to users.
# ---------------------------------------------------------------------------


def reviewer_agent(provider: Any, name: str = "reviewer") -> Agent:
    """A senior-code-reviewer agent (used by `/review` and `CriticAgent`)."""
    return Agent(
        name=name,
        provider=provider,
        system_prompt=(
            "You are a meticulous senior engineer performing code review. "
            "Focus on correctness, edge cases, security, and maintainability. "
            "Be specific and actionable; cite the exact lines or symbols."
        ),
    )


def explainer_agent(provider: Any, name: str = "explainer") -> Agent:
    """An agent that explains code/concepts clearly (used by `/explain`)."""
    return Agent(
        name=name,
        provider=provider,
        system_prompt=(
            "You are a patient staff engineer who explains code and systems "
            "to competent developers new to a codebase. Use concrete examples "
            "and avoid unnecessary jargon."
        ),
    )


def tester_agent(provider: Any, name: str = "tester") -> Agent:
    """An agent that writes focused tests (used by `/test`)."""
    return Agent(
        name=name,
        provider=provider,
        system_prompt=(
            "You are a test engineer. Write focused, runnable unit tests that "
            "cover happy paths, edge cases, and failure modes. Prefer the "
            "project's existing test framework and conventions."
        ),
    )


def summarizer_agent(provider: Any, name: str = "summarizer") -> Agent:
    """An agent that condenses conversations (used by agentic compaction)."""
    return Agent(
        name=name,
        provider=provider,
        system_prompt=(
            "You are a concise summarizer. Given a conversation transcript, "
            "produce a dense summary that preserves decisions, facts, open "
            "questions, and any `LEARNING:` lines. Output only the summary."
        ),
    )


def critic_agent(
    provider: Any,
    actor: Agent | None = None,
    critic: Agent | None = None,
    max_iterations: int = 3,
    name: str = "critic",
) -> CriticAgent:
    """A Reflexion loop that self-critiques an actor's output.

    Defaults to a `tester` actor and a `reviewer` critic so the runtime can
    improve generated artifacts (e.g. tests) before returning them.
    """
    actor = actor or tester_agent(provider, name=f"{name}-actor")
    critic = critic or reviewer_agent(provider, name=f"{name}-critic")
    return CriticAgent(
        name=name,
        actor=actor,
        critic=critic,
        max_iterations=max_iterations,
    )


def router_agent(
    provider: Any,
    routes: list[Route] | None = None,
    default_agent: Agent | None = None,
    name: str = "router",
) -> RouterAgent:
    """A general-purpose intent router over common specialist agents.

    If no routes are supplied, a sensible default set is built from the
    built-in reviewer / explainer / tester agents.
    """
    if routes is None:
        routes = [
            Route("review", reviewer_agent(provider, "reviewer"), keywords=["review", "critique", "bug"]),
            Route("explain", explainer_agent(provider, "explainer"), keywords=["explain", "what does", "how does"]),
            Route("test", tester_agent(provider, "tester"), keywords=["test", "unit test", "coverage"]),
        ]
    default_agent = default_agent or explainer_agent(provider, "general")
    return RouterAgent(name=name, routes=routes, default_agent=default_agent)
