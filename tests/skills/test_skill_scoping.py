from __future__ import annotations

import pytest

from ai_runtime.skills import Skill, SkillRegistry, ComposedSkills


def test_skill_scoping_fields():
    s = Skill(
        name="sql",
        description="SQL analyst",
        globs=["*.sql"],
        paths=["/db"],
        disable_model_invocation=True,
    )
    assert s.globs == ["*.sql"]
    assert s.paths == ["/db"]
    assert s.disable_model_invocation is True


def test_compose_respects_scoping():
    registry = SkillRegistry()
    registry.register(
        Skill(name="general", description="g", system_prompt="GENERAL")
    )
    registry.register(
        Skill(name="scoped", description="s", system_prompt="SCOPED", globs=["*.py"])
    )
    composed = registry.compose(["general", "scoped"])
    assert isinstance(composed, ComposedSkills)
    assert "general" in composed.tool_names or composed.system_prompt
