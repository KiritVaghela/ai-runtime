from __future__ import annotations


from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A single step in an execution plan."""

    description: str
    action: str | None = None  # e.g. "tool:write_file", "llm:answer"
    target: str | None = None  # resource the action operates on


class Plan(BaseModel):
    """A reviewable execution plan produced in PLAN mode.

    The plan is intentionally separate from execution: the caller inspects
    it and may approve, edit, or reject before any tool runs.
    """

    goal: str
    steps: list[PlanStep] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    raw: str | None = None

    def __str__(self) -> str:
        lines = [f"Goal: {self.goal}", ""]
        for i, step in enumerate(self.steps, 1):
            line = f"{i}. {step.description}"
            if step.action:
                line += f"  [{step.action}]"
            lines.append(line)
        if self.risks:
            lines.append("")
            lines.append("Risks:")
            lines.extend(f"  - {r}" for r in self.risks)
        return "\n".join(lines)
