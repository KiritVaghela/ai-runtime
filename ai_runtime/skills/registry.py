from __future__ import annotations

from typing import Iterable

from .skill import Skill


class SkillRegistry:
    """In-memory registry of named `Skill` definitions."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if skill.name in self._skills:
            raise KeyError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        return self._skills[name]

    def list(self) -> Iterable[Skill]:
        return list(self._skills.values())

    def compose(self, names: list[str]) -> "ComposedSkills":
        selected = [self.get(n) for n in names]
        return ComposedSkills(selected)


class ComposedSkills:
    """Aggregates multiple skills into a single system prompt + tool set."""

    def __init__(self, skills: list[Skill]):
        self.skills = skills

    @property
    def system_prompt(self) -> str:
        parts = [
            s.system_prompt for s in self.skills if s.system_prompt
        ]
        return "\n\n".join(parts)

    @property
    def tool_names(self) -> list[str]:
        names: list[str] = []
        for s in self.skills:
            names.extend(s.tools)
        return names

    @property
    def retrieval_skills(self) -> list["Skill"]:
        """Skills that inject retrieved RAG context into the prompt."""
        return [s for s in self.skills if getattr(s, "retriever", None) is not None]

    @property
    def guardrail_skills(self) -> list["Skill"]:
        """Skills that validate/reject model output."""
        return [s for s in self.skills if getattr(s, "guardrail", None) is not None]

    async def retrieval_context(self, task: str) -> str:
        """Aggregate retrieved context from all retrieval skills."""
        blocks: list[str] = []
        for s in self.retrieval_skills:
            try:
                ctx = await s.retrieve_context(task)
            except Exception:
                ctx = ""
            if ctx:
                blocks.append(f"[Retrieved context: {s.name}]\n{ctx}")
        return "\n\n".join(blocks)

    def apply_guardrails(self, output: str) -> "tuple[str, list]":
        """Run all guardrail skills over output.

        Returns ``(final_output, failures)`` where ``failures`` is a list of
        ``GuardrailOutcome`` for any guardrail that did not pass.
        """
        from .types import GuardrailOutcome

        failures: list[GuardrailOutcome] = []
        final = output
        for s in self.guardrail_skills:
            outcome = s.evaluate(final)
            if not outcome.passed:
                failures.append(outcome)
                if outcome.action == "reject":
                    final = f"[blocked by guardrail '{s.name}']: {outcome.message}"
                elif outcome.action == "rewrite" and outcome.rewritten is not None:
                    final = outcome.rewritten
                # "warn" passes output through unchanged.
        return final, failures
