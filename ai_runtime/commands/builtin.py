from __future__ import annotations


from .registry import Command


# ---------------------------------------------------------------------------
# Built-in command presets
#
# Reusable `Command` instances that ship with the framework. `default_commands()`
# registers these so the CLI / server / web UIs all expose the same `/` menu.
# ---------------------------------------------------------------------------


def compact_command() -> Command:
    return Command(
        "compact",
        "Summarize the conversation to free context",
        "Please summarize the conversation so far concisely.",
        category="general",
        example="/compact",
    )


def context_command() -> Command:
    return Command(
        "context",
        "Show a token/context breakdown",
        "List the current context window usage.",
        category="general",
        example="/context",
    )


def clear_command() -> Command:
    return Command(
        "clear",
        "Clear the conversation history",
        "Clear all messages from the current session.",
        category="general",
        example="/clear",
    )


def review_command() -> Command:
    return Command(
        "review",
        "Critique the proposed change for correctness and risks",
        "You are a senior reviewer. Review the following change for "
        "correctness, edge cases, and risks. Be specific and actionable:\n\n{diff}",
        category="review",
        args=["diff"],
        example='/review def add(a, b):\n    return a + b',
    )


def explain_command() -> Command:
    return Command(
        "explain",
        "Explain a piece of code or concept clearly",
        "Explain the following {target} in clear, concise terms suitable "
        "for a competent engineer who is new to this codebase:\n\n{code}",
        category="explain",
        args=["target", "code"],
        example="/explain the quicksort implementation in sort.py",
    )


def test_command() -> Command:
    return Command(
        "test",
        "Generate tests for the given code",
        "Write a focused set of unit tests for the following code. Cover "
        "happy paths, edge cases, and failure modes:\n\n{code}",
        category="test",
        args=["code"],
        example="/test def divide(a, b):\n    return a / b",
    )


def workflow_command() -> Command:
    return Command(
        "workflow",
        "Run a named multi-step workflow against the task",
        "Execute the '{name}' workflow to accomplish the task step by "
        "step, validating each step before proceeding:\n\n{task}",
        category="workflow",
        args=["name", "task"],
        example="/workflow refactor Extract the parser into its own module",
    )


def default_builtin_commands() -> list[Command]:
    """The canonical set of built-in slash commands."""
    return [
        compact_command(),
        context_command(),
        clear_command(),
        review_command(),
        explain_command(),
        test_command(),
        workflow_command(),
    ]
