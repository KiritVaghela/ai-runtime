from __future__ import annotations

import json
from typing import Any

from ai_runtime.conversation import ChatMessage
from ai_runtime.execution.plan import Plan, PlanStep
from ai_runtime.execution.pipeline.stage import ExecutionStage
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.mode import ExecutionMode


_PLANNER_SYSTEM = (
    "You are a planning agent. Given the user's request, produce a concise, "
    "ordered execution plan as JSON with keys: "
    '"goal" (string), "steps" (array of {"description", "action", "target"}), '
    '"risks" (array of strings). Do NOT execute anything. Respond ONLY with '
    "the JSON object."
)


class PlannerStage(ExecutionStage):
    """Produces a reviewable `Plan` in PLAN mode (read-only, no tools run).

    The plan is stored on `context.plan` for the caller to inspect. This
    mirrors the plan-mode behavior of agentic coding tools: research and
    structuring happen before any mutating action.
    """

    def __init__(self, system_prompt: str | None = None):
        self._system_prompt = system_prompt or _PLANNER_SYSTEM

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if context.mode != ExecutionMode.PLAN:
            return context

        if context.request is None:
            raise RuntimeError("RequestBuilderStage must execute first.")

        messages = [ChatMessage.system(self._system_prompt)]
        messages.extend(context.request.messages)

        # Use the provider directly (no tool loop) to keep planning read-only.
        response = await context.provider.chat(
            context.request.model_copy(update={"messages": messages})
            if hasattr(context.request, "model_copy")
            else context.request
        )

        context.plan = self._parse_plan(response.message.content, context)
        return context

    @staticmethod
    def _parse_plan(content: str, context: ExecutionContext) -> Plan:
        text = content or ""
        # Extract the first JSON object from the response.
        start = text.find("{")
        end = text.rfind("}") + 1
        try:
            data = json.loads(text[start:end]) if start != -1 else {}
        except json.JSONDecodeError:
            data = {}

        goal = data.get("goal", context.request.messages[-1].content
                        if context.request and context.request.messages else "")
        steps = [
            PlanStep(
                description=s.get("description", ""),
                action=s.get("action"),
                target=s.get("target"),
            )
            for s in data.get("steps", [])
        ]
        risks = data.get("risks", [])

        return Plan(goal=goal, steps=steps, risks=risks, raw=text)
