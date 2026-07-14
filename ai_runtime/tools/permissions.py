from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    """A single allow/deny rule matched against `Tool(name=..., action=...)`.

    Patterns use glob syntax (e.g. `Bash(git push *)`, `Agent(model:opus)`,
    `Write(*)`). A rule matches when both the tool name and the parameter
    pattern match.
    """

    tool: str  # glob, e.g. "Bash", "Write", "*"
    params: str = "*"  # glob over the rendered param string
    decision: PermissionDecision = PermissionDecision.ALLOW

    def matches(self, tool_name: str, param_str: str) -> bool:
        if not fnmatch.fnmatch(tool_name, self.tool):
            return False
        if fnmatch.fnmatch(param_str, self.params):
            return True
        # Allow a wildcard pattern to match as a substring, e.g.
        # "git push *" matches "cmd=git push origin".
        if "*" in self.params:
            core = self.params.strip("*")
            if core and core in param_str:
                return True
        return False


@dataclass
class PermissionPolicy:
    """Aggregates rules into a decision for a tool invocation.

    Rules are evaluated in order; the first matching rule wins. If no rule
    matches, the `default` decision is used (defaults to ASK, mirroring the
    safe-by-default posture of agentic coding tools).
    """

    rules: list[PermissionRule] = field(default_factory=list)
    default: PermissionDecision = PermissionDecision.ASK

    def decide(self, tool_name: str, param_str: str = "") -> PermissionDecision:
        for rule in self.rules:
            if rule.matches(tool_name, param_str):
                return rule.decision
        return self.default

    @classmethod
    def permissive(cls) -> "PermissionPolicy":
        return cls(rules=[PermissionRule("*", "*", PermissionDecision.ALLOW)])

    @classmethod
    def restrictive(cls) -> "PermissionPolicy":
        return cls(rules=[PermissionRule("*", "*", PermissionDecision.DENY)])


class PermissionError(Exception):
    """Raised when a tool invocation is denied by policy."""


def render_params(input: Any) -> str:
    """Render a tool input into a string for rule matching."""
    if isinstance(input, dict):
        return " ".join(f"{k}={v}" for k, v in input.items())
    return str(input)
