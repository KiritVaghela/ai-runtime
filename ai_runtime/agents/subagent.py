from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent


@dataclass
class SubAgentSpec:
    """Declarative spec for a child agent spawned by a supervisor.

    Mirrors the sub-agent model of agentic coding tools: a child has its
    own tools, model, and isolation scope, and runs in a separate context
    so its transcript does not pollute the parent's context window.
    """

    name: str
    agent: Agent
    task_template: str = "{task}"  # receives `task` kwarg
    max_depth: int = 1  # how many levels of nesting allowed
    isolated: bool = True  # run in a fresh conversation context


@dataclass
class SubAgentResult:
    name: str
    output: str
    success: bool = True
    error: str | None = None
