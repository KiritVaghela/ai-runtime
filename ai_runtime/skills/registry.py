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
