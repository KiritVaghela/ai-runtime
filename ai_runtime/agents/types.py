from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable



# ---------------------------------------------------------------------------
# WorkflowAgent — declarative DAG of agent steps (à la LangGraph / AutoGen)
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """A single node in a workflow DAG.

    Mirrors the step model of modern agentic orchestration frameworks
    (LangGraph nodes, DSPy modules, AutoGen groups): a step runs an agent
    (optionally composed with a skill or rendering a command), templated on
    upstream outputs, and publishes its result for downstream steps.
    """

    name: str
    agent: Any | None = None  # an `Agent` instance to run
    skill: str | None = None  # skill name composed into `agent` for this step
    command: str | None = None  # command name rendered as the step prompt
    prompt_template: str | None = None  # receives `task` + `steps` (outputs)
    depends_on: list[str] = field(default_factory=list)
    map_result: Callable[[str], Any] | None = None  # transform raw output
    max_retries: int = 0


class WorkflowAgent:
    """Declarative DAG of agent steps executed with dependency ordering.

    Steps whose dependencies are satisfied run concurrently (bounded by
    `max_concurrency`); each step's string output is exposed to downstream
    steps via the ``{steps.<name>}`` placeholder in ``prompt_template``.
    This mirrors the graph/orchestration layer that modern agentic workflows
    add on top of a single agent loop.
    """

    def __init__(
        self,
        name: str,
        steps: list[WorkflowStep],
        engine: Any | None = None,
        max_concurrency: int = 4,
    ):
        self.name = name
        self.steps: dict[str, WorkflowStep] = {s.name: s for s in steps}
        self.engine = engine
        self.max_concurrency = max_concurrency
        self.last_outputs: dict[str, Any] = {}

    # -- graph helpers ------------------------------------------------------

    def _layers(self) -> list[list[str]]:
        """Kahn layering: each layer is concurrently runnable."""
        remaining = dict(self.steps)
        resolved: set[str] = set()
        layers: list[list[str]] = []
        while remaining:
            layer = [
                n
                for n, s in remaining.items()
                if all(d in resolved for d in s.depends_on)
            ]
            if not layer:
                raise ValueError(
                    f"Cyclic or unsatisfiable dependency among steps: "
                    f"{sorted(remaining)}"
                )
            layers.append(layer)
            resolved.update(layer)
            for n in layer:
                del remaining[n]
        return layers

    def _render_prompt(self, step: WorkflowStep, task: str) -> str:
        if step.command:
            # Render a slash command as the step prompt (best-effort).
            from ai_runtime.commands import CommandRegistry

            reg = CommandRegistry()
            rendered = reg.render(step.command, task=task, steps=self.last_outputs)
            if rendered:
                return rendered
        if step.prompt_template:
            try:
                return step.prompt_template.format(
                    task=task, **self.last_outputs
                )
            except (KeyError, IndexError):
                return step.prompt_template
        return task

    async def _run_step(self, step: WorkflowStep, task: str) -> Any:
        prompt = self._render_prompt(step, task)
        agent = step.agent
        if agent is None:
            # Command-only / constant step: the rendered text is the output.
            return prompt

        if step.skill and agent.skill_registry is not None:
            agent.skills = agent.skill_registry.compose([step.skill])

        from .runner import AgentRunner

        runner = AgentRunner(agent, engine=self.engine)
        attempt = 0
        last_err: Exception | None = None
        while attempt <= step.max_retries:
            try:
                resp = await runner.run(prompt)
                output = resp.message.content or ""
                return step.map_result(output) if step.map_result else output
            except Exception as e:  # retry isolation per-step
                last_err = e
                attempt += 1
        raise last_err or RuntimeError(f"Step {step.name} failed")

    # -- execution ----------------------------------------------------------

    async def run(self, task: str) -> dict[str, Any]:
        """Execute the DAG and return a map of step-name -> output."""
        self.last_outputs = {}
        for layer in self._layers():
            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def _guarded(step: WorkflowStep):
                async with semaphore:
                    return step.name, await self._run_step(step, task)

            results = await asyncio.gather(*(_guarded(self.steps[n]) for n in layer))
            for name, out in results:
                self.last_outputs[name] = out
        return dict(self.last_outputs)


# ---------------------------------------------------------------------------
# RouterAgent — intent-based dispatcher (à la multi-agent orchestrators)
# ---------------------------------------------------------------------------


@dataclass
class Route:
    """A single routing rule: a specialist agent + how to match it."""

    name: str
    agent: Any  # an `Agent` instance
    description: str = ""
    keywords: list[str] = field(default_factory=list)  # case-insensitive match
    when: Callable[[str], bool] | None = None  # explicit rule-based predicate


class RouterAgent:
    """Intent-based dispatcher: routes a message to a specialist agent.

    Mirrors the router/orchestrator pattern of multi-agent frameworks: a
    top-level agent classifies the request (rule-based keywords first, then
    an optional LLM classifier) and forwards it to the most appropriate
    specialist. Falls back to ``default_agent`` when nothing matches.
    """

    def __init__(
        self,
        name: str,
        routes: list[Route],
        default_agent: Any | None = None,
        classifier_prompt: str | None = None,
        engine: Any | None = None,
    ):
        self.name = name
        self.routes = routes
        self.default_agent = default_agent
        self.classifier_prompt = classifier_prompt or (
            "You are a routing classifier. Given the user request, reply with "
            "ONLY the name of the most appropriate route from this list: "
            f"{[r.name for r in routes]}. If none fit, reply with 'default'."
        )
        self.engine = engine

    async def route(self, message: str) -> Route | None:
        lowered = message.lower()
        # 1) Explicit predicates.
        for r in self.routes:
            if r.when is not None and r.when(message):
                return r
        # 2) Keyword matching.
        for r in self.routes:
            if any(k.lower() in lowered for k in r.keywords):
                return r
        # 3) LLM classifier (uses the default agent's provider if present).
        if self.default_agent is not None and hasattr(self.default_agent, "provider"):
            try:
                from .runner import AgentRunner

                classifier = Agent(
                    name=f"{self.name}-router",
                    provider=self.default_agent.provider,
                    system_prompt=self.classifier_prompt,
                )
                resp = await AgentRunner(classifier, engine=self.engine).run(message)
                label = (resp.message.content or "").strip().lower()
                for r in self.routes:
                    if r.name.lower() == label:
                        return r
            except Exception:
                pass
        return None

    async def run(self, message: str) -> Any:
        route = await self.route(message)
        agent = route.agent if route else self.default_agent
        if agent is None:
            raise RuntimeError(
                f"Router '{self.name}' matched no route and has no default agent."
            )
        from .runner import AgentRunner

        return await AgentRunner(agent, engine=self.engine).run(message)


# ---------------------------------------------------------------------------
# CriticAgent — reflexion-style self-improvement loop
# ---------------------------------------------------------------------------


@dataclass
class CriticResult:
    """Outcome of a `CriticAgent` run."""

    output: str
    iterations: int
    approved: bool
    critiques: list[str]


class CriticAgent:
    """Reflexion-style actor/critic loop.

    Runs an ``actor`` agent to produce a candidate, then evaluates it with a
    ``critic`` (an `Agent`, or a ``validator`` callable). If the candidate is
    rejected, the critique is fed back to the actor and the loop repeats up
    to ``max_iterations``. Mirrors the self-reflection / critic-actor pattern
    of modern agentic workflows (Reflexion, Constitutional AI, CriticGPT).
    """

    def __init__(
        self,
        name: str,
        actor: Any,  # `Agent`
        critic: Any | None = None,  # `Agent` used when no `validator`
        validator: Callable[[str, str], tuple[bool, str]] | None = None,
        max_iterations: int = 3,
        engine: Any | None = None,
    ):
        self.name = name
        self.actor = actor
        self.critic = critic
        self.validator = validator
        self.max_iterations = max_iterations
        self.engine = engine

    @staticmethod
    def _parse_approval(text: str) -> tuple[bool, str]:
        t = text.lower()
        if "approved" in t and "rejected" not in t:
            return True, text.strip()
        if "rejected" in t:
            # Capture the rationale after the verdict.
            idx = t.find("rejected")
            return False, text[idx:].strip()
        return True, text.strip()

    async def _evaluate(self, task: str, candidate: str) -> tuple[bool, str]:
        if self.validator is not None:
            return self.validator(task, candidate)
        if self.critic is None:
            return True, "no critic configured"
        from .runner import AgentRunner

        prompt = (
            f"Task:\n{task}\n\nCandidate answer:\n{candidate}\n\n"
            "Evaluate the candidate. Reply with either 'APPROVED' or "
            "'REJECTED: <reason>'."
        )
        resp = await AgentRunner(self.critic, engine=self.engine).run(prompt)
        return self._parse_approval(resp.message.content or "")

    async def run(self, task: str) -> CriticResult:
        candidate = ""
        critiques: list[str] = []
        for i in range(1, self.max_iterations + 1):
            if i == 1:
                prompt = task
            else:
                prompt = (
                    f"{task}\n\nYour previous attempt was rejected.\n"
                    f"Critique:\n{critiques[-1]}\n\nRevise and improve your answer."
                )
            from .runner import AgentRunner

            resp = await AgentRunner(self.actor, engine=self.engine).run(prompt)
            candidate = resp.message.content or ""
            approved, reason = await self._evaluate(task, candidate)
            if approved:
                return CriticResult(candidate, i, True, critiques)
            critiques.append(reason)
        return CriticResult(candidate, self.max_iterations, False, critiques)


# Late import kept at bottom to avoid a hard cycle with `.agent`.
from .agent import Agent  # noqa: E402
