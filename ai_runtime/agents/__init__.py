"""Agent subsystem: declarative agents and orchestration runner."""

from .agent import Agent
from .runner import AgentRunner
from .subagent import SubAgentSpec, SubAgentResult
from .modes import AgentMode, AGENT_MODES
from .types import (
    WorkflowStep,
    WorkflowAgent,
    Route,
    RouterAgent,
    CriticResult,
    CriticAgent,
)
from .builtin import (
    reviewer_agent,
    explainer_agent,
    tester_agent,
    summarizer_agent,
    critic_agent,
    router_agent,
)
from .self_agentic import (
    agentic_summarize,
    make_agentic_compaction_summarizer,
    make_self_reviewer,
)

__all__ = [
    "Agent",
    "AgentRunner",
    "SubAgentSpec",
    "SubAgentResult",
    "AgentMode",
    "AGENT_MODES",
    "WorkflowStep",
    "WorkflowAgent",
    "Route",
    "RouterAgent",
    "CriticResult",
    "CriticAgent",
    "reviewer_agent",
    "explainer_agent",
    "tester_agent",
    "summarizer_agent",
    "critic_agent",
    "router_agent",
    "agentic_summarize",
    "make_agentic_compaction_summarizer",
    "make_self_reviewer",
]
