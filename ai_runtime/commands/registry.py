from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Command:
    """A slash command / prompt file (à la Copilot's `/` menu).

    A command is a named, reusable prompt (or hook) the user can invoke.
    `render` produces the prompt text sent to the model; `run` optionally
    executes side effects (e.g. `/compact`, `/context`).
    """

    name: str
    description: str
    prompt_template: str | None = None
    run: Callable[[Any], Any] | None = None
    # Categorization (mirrors the grouped `/` menu of agentic tools):
    category: str = "general"  # general | review | explain | test | workflow
    args: list[str] = field(default_factory=list)  # named template args
    example: str | None = None  # example invocation shown in the UI

    def render(self, **kwargs: Any) -> str:
        if self.prompt_template:
            try:
                return self.prompt_template.format(**kwargs)
            except (KeyError, IndexError):
                return self.prompt_template
        return self.description

    def with_args(self, **kwargs: Any) -> "Command":
        """Return a copy of this command bound with the given args."""
        from dataclasses import replace

        return replace(self, prompt_template=self.render(**kwargs))


class CommandRegistry:
    """Registry of slash commands / prompt files."""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def list(self) -> list[Command]:
        return list(self._commands.values())

    def render(self, command_name: str, **kwargs: Any) -> str | None:
        cmd = self._commands.get(command_name)
        return cmd.render(**kwargs) if cmd else None


# Built-in commands mirroring Copilot/Claude/Cursor slash commands.
def default_commands() -> CommandRegistry:
    from .builtin import default_builtin_commands

    reg = CommandRegistry()
    for cmd in default_builtin_commands():
        reg.register(cmd)
    return reg
