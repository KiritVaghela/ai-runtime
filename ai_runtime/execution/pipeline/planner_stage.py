from __future__ import annotations

import json
import re
from typing import Any

from ai_runtime.conversation import ChatMessage
from ai_runtime.execution.plan import Plan, PlanStep
from ai_runtime.execution.pipeline.stage import ExecutionStage
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.mode import ExecutionMode
from ai_runtime.streaming import (
    StreamEvent,
    TextDeltaEvent,
    ThinkingEvent,
    CompletedEvent,
)
from collections.abc import AsyncIterator


_PLANNER_SYSTEM = (
    "You are a planning agent. Given the user's request, produce a concise, "
    "ordered execution plan in MARKDOWN (no code fences, no JSON). Use this "
    "structure:\n\n"
    "# Plan\\n<one-line goal>\\n\\n"
    "## Steps\\n- <step description>\\n- <step description>\\n\\n"
    "## Risks\\n- <risk>\\n\\n"
    "Do NOT execute anything. Research and structure only."
)


class PlannerStage(ExecutionStage):
    """Produces a reviewable `Plan` in PLAN mode (read-only, no tools run).

    The plan is stored on `context.plan` for the caller to inspect. This
    mirrors the plan-mode behavior of agentic coding tools: research and
    structuring happen before any mutating action.

    Planning streams exactly like chat: the markdown plan text (and any
    thinking) is emitted as live deltas, so effort / thinking / streaming
    controls all apply and the user watches the plan type out.
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

        request = (
            context.request.model_copy(update={"messages": messages})
            if hasattr(context.request, "model_copy")
            else context.request
        )

        # Stream the planning response live (markdown plan + thinking), exactly
        # like chat mode. The text deltas are surfaced to the caller so the
        # plan types out in the UI; we also accumulate it for parsing.
        raw_parts: list[str] = []
        thinking_parts: list[str] = []
        async for event in context.provider.stream(request):
            if isinstance(event, TextDeltaEvent):
                raw_parts.append(event.delta)
                # Surface the plan text live.
                context._plan_events = getattr(context, "_plan_events", []) + [event]
            elif isinstance(event, ThinkingEvent):
                thinking_parts.append(event.delta)
                # Surface thinking live (it's useful).
                context._plan_events = getattr(context, "_plan_events", []) + [event]
            else:
                context._plan_events = getattr(context, "_plan_events", []) + [event]

        raw = "".join(raw_parts)
        context.thinking_text = "".join(thinking_parts)
        context.assistant_text = raw
        context.plan = self._parse_plan(raw, context)
        return context

    @staticmethod
    def _parse_plan(content: str, context: ExecutionContext) -> Plan:
        text = content or ""

        # Goal: the first non-empty line (strip a leading "# Plan" heading).
        lines = [ln.strip() for ln in text.splitlines()]
        lines = [ln for ln in lines if ln]
        goal = ""
        for ln in lines:
            if ln.startswith("#"):
                continue
            goal = re.sub(r"^#+\s*", "", ln)
            break
        if not goal and context.request and context.request.messages:
            goal = context.request.messages[-1].content

        # Steps: bullet lines under "## Steps" (or any "- " bullets).
        steps: list[PlanStep] = []
        in_steps = False
        for ln in text.splitlines():
            s = ln.strip()
            if re.match(r"^#+\s*steps", s, re.IGNORECASE):
                in_steps = True
                continue
            if re.match(r"^#+\s", s):
                in_steps = False
                continue
            m = re.match(r"^[-*]\s+(.*)$", s)
            if m and in_steps:
                steps.append(PlanStep(description=m.group(1)))

        # Risks: bullet lines under "## Risks".
        risks: list[str] = []
        in_risks = False
        for ln in text.splitlines():
            s = ln.strip()
            if re.match(r"^#+\s*risks", s, re.IGNORECASE):
                in_risks = True
                continue
            if re.match(r"^#+\s", s):
                in_risks = False
                continue
            m = re.match(r"^[-*]\s+(.*)$", s)
            if m and in_risks:
                risks.append(m.group(1))

        return Plan(goal=goal, steps=steps, risks=risks, raw=text)
