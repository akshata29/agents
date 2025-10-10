"""Thin orchestration layer using native Microsoft Agent Framework workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import structlog

from agent_framework import (
    ChatMessage,
    Role,
    SequentialBuilder,
    ConcurrentBuilder,
    WorkflowOutputEvent,
    TextContent,
)

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class WorkflowResult:
    """Represents the condensed outcome of a workflow execution."""

    messages: List[ChatMessage]

    def last_text(self) -> str:
        """Return the text content of the final message, if available."""
        if not self.messages:
            return ""
        last = self.messages[-1]
        return last.text if hasattr(last, "text") else ""


class MAFOrchestrator:
    """Coordinates registered agents using Sequential or Concurrent workflows."""

    def __init__(self) -> None:
        self._agents: Dict[str, object] = {}
        logger.info("MAF orchestrator initialised")

    def register_agent(self, name: str, agent: object) -> None:
        """Register a MAF-compatible agent for workflow execution."""
        self._agents[name] = agent
        logger.debug("Registered agent with orchestrator", agent=name)

    def unregister_agent(self, name: str) -> None:
        """Remove an agent from the orchestrator registry."""
        self._agents.pop(name, None)
        logger.debug("Unregistered agent", agent=name)

    def get_agent(self, name: str) -> object:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self._agents[name]

    def list_agents(self) -> List[str]:
        return sorted(self._agents)

    def _build_messages(self, prompt: str | ChatMessage | Sequence[ChatMessage]) -> List[ChatMessage]:
        if isinstance(prompt, list):
            return list(prompt)
        if isinstance(prompt, ChatMessage):
            return [prompt]
        return [ChatMessage(role=Role.USER, contents=[TextContent(text=str(prompt))])]

    async def run_sequential(
        self,
        agent_names: Sequence[str],
        prompt: str | ChatMessage | Sequence[ChatMessage],
    ) -> WorkflowResult:
        """Execute agents sequentially and return their aggregated output."""
        agents = [self.get_agent(name) for name in agent_names]
        if not agents:
            raise ValueError("At least one agent must be provided for sequential workflows")

        builder = SequentialBuilder().participants(agents)
        workflow = builder.build()
        events = await workflow.run(self._build_messages(prompt))
        messages = self._extract_output_messages(events)
        return WorkflowResult(messages=messages)

    async def run_concurrent(
        self,
        agent_names: Sequence[str],
        prompt: str | ChatMessage | Sequence[ChatMessage],
    ) -> WorkflowResult:
        """Execute agents concurrently (fan-out) and gather outputs."""
        agents = [self.get_agent(name) for name in agent_names]
        if len(agents) < 2:
            raise ValueError("Concurrent workflows require at least two agents")

        builder = ConcurrentBuilder().participants(agents)
        workflow = builder.build()
        events = await workflow.run(self._build_messages(prompt))
        messages = self._extract_output_messages(events)
        return WorkflowResult(messages=messages)

    @staticmethod
    def _extract_output_messages(events: Iterable[object]) -> List[ChatMessage]:
        collected: List[ChatMessage] = []
        for event in events:
            if isinstance(event, WorkflowOutputEvent):
                collected.extend(event.data or [])
        return collected