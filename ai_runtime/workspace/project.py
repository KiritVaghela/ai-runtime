from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_runtime.agents.config_files import load_project_instructions
from ai_runtime.memory import InMemoryStore, MemoryStore
from ai_runtime.tools import PermissionPolicy, ToolRegistry
from ai_runtime.tools.builtin import register_builtin_tools
from ai_runtime.tools.checkpoints import CheckpointManager


@dataclass
class Project:
    """Scopes agent resources to a project root.

    Mirrors the project-scoped context of agentic tools: a project owns its
    instruction files, memory store, tool registry (sandboxed to the root),
    permission policy, and checkpoints. This is the unit you mount into a
    web/desktop/VS Code/CLI client.
    """

    root: str
    name: str | None = None
    memory_store: MemoryStore = field(default_factory=InMemoryStore)
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    permission_policy: PermissionPolicy = field(default_factory=lambda: PermissionPolicy())
    checkpoint_manager: CheckpointManager | None = None
    instructions: str | None = None

    def __post_init__(self):
        self.root = str(Path(self.root).resolve())
        if self.name is None:
            self.name = Path(self.root).name
        if self.checkpoint_manager is None:
            self.checkpoint_manager = CheckpointManager(f"{self.root}/.ai-runtime/checkpoints")
        if self.instructions is None:
            self.instructions = load_project_instructions(self.root)

    def install_builtin_tools(self) -> None:
        """Register the standard file/shell tools scoped to this project root."""
        register_builtin_tools(self.tool_registry, base_dir=self.root)

    def as_system_prompt(self, base_prompt: str | None = None) -> str | None:
        parts: list[str] = []
        if base_prompt:
            parts.append(base_prompt)
        if self.instructions:
            parts.append(self.instructions)
        return "\n\n---\n\n".join(parts) if parts else None
