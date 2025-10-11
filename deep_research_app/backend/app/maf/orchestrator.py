"""Orchestration helpers built on Microsoft Agent Framework primitives."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

import structlog

from agent_framework import (
    ChatMessage,
    Role,
    SequentialBuilder,
    ConcurrentBuilder,
    WorkflowOutputEvent,
    TextContent,
    AgentRunResponse,
)
from .registry import AgentRegistry
from .observability import ObservabilityService
from .settings import Settings

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class ExecutionContext:
    """Result metadata for an orchestration run."""

    id: str
    pattern_name: str
    agents: List[str]
    result: Dict[str, Any]
    started_at: datetime
    ended_at: datetime
    metadata: Dict[str, Any]


class MagenticOrchestrator:
    """Lean orchestrator compatible with the original framework surface."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        *,
        agent_registry: Optional[AgentRegistry] = None,
        observability: Optional[ObservabilityService] = None,
    ) -> None:
        self._settings = settings or Settings()
        self._registry = agent_registry or AgentRegistry(self._settings)
        self._observability = observability or ObservabilityService(self._settings)
        logger.info("Magentic orchestrator initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def execute(
        self,
        *,
        task: str | ChatMessage | Sequence[ChatMessage],
        pattern: str,
        agents: Sequence[str],
        tools: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionContext:
        """Execute a Microsoft Agent Framework workflow pattern."""

        pattern_name = pattern.lower()
        pattern_agents = list(agents)
        logger.info(
            "Starting orchestration run",
            pattern=pattern_name,
            agents=pattern_agents,
        )
        start = datetime.utcnow()

        if pattern_name == "sequential":
            result = await self.execute_sequential(task, pattern_agents, tools=tools)
        elif pattern_name == "concurrent":
            result = await self.execute_concurrent(task, pattern_agents, tools=tools)
        else:
            raise ValueError(f"Unsupported pattern '{pattern}'. Expected 'sequential' or 'concurrent'.")

        context = ExecutionContext(
            id=str(uuid.uuid4()),
            pattern_name=pattern_name,
            agents=pattern_agents,
            result=result,
            started_at=start,
            ended_at=datetime.utcnow(),
            metadata=metadata or {},
        )

        self._observability.record_event(
            "maf.orchestrator.execute",
            pattern=pattern_name,
            duration=(context.ended_at - start).total_seconds(),
            agents=pattern_agents,
        )
        return context

    async def execute_sequential(
        self,
        task: str | ChatMessage | Sequence[ChatMessage],
        agent_ids: Sequence[str],
        *,
        tools: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Execute agents sequentially using Microsoft Agent Framework."""

        agents = list(agent_ids)
        agent_instances = []
        agent_display_names = []
        for name in agents:
            agent = await self._registry.get_agent(name)
            agent_instances.append(agent)
            agent_display_names.append(getattr(agent, "name", name))

        if tools:
            logger.debug("Tools parameter acknowledged", tools=list(tools))

        builder = SequentialBuilder()
        if agent_instances:
            builder = builder.participants(agent_instances)
        workflow = builder.build()
        messages = self._normalise_messages(task)

        workflow_events = await workflow.run(messages)
        results: List[Dict[str, Any]] = []
        final_conversation: Optional[List[ChatMessage]] = None

        for event in workflow_events:
            if isinstance(event, WorkflowOutputEvent):
                if event.source_executor_id == "end" and event.data:
                    final_conversation = list(event.data)

        if final_conversation:
            mapping = {display: agent for display, agent in zip(agent_display_names, agents)}
            for message in final_conversation:
                role = getattr(message, "role", None)
                text = getattr(message, "text", None)
                author = getattr(message, "author_name", None)

                if not text:
                    continue
                if role and role == Role.USER:
                    continue

                if author and author in mapping:
                    agent_name = mapping[author]
                else:
                    agent_index = len(results)
                    agent_name = agents[agent_index] if agent_index < len(agents) else author or "assistant"

                results.append(
                    {
                        "agent": agent_name,
                        "content": text,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        summary = results[-1]["content"] if results else None
        logger.info("Sequential pattern completed", agent_results=len(results))
        return {
            "pattern": "sequential",
            "task": self._summarise_task(task),
            "agents": agents,
            "results": results,
            "summary": summary,
        }

    async def execute_concurrent(
        self,
        task: str | ChatMessage | Sequence[ChatMessage],
        agent_ids: Sequence[str],
        *,
        tools: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Execute agents concurrently using Microsoft Agent Framework."""

        agents = list(agent_ids)
        agent_instances = []
        for name in agents:
            agent_instances.append(await self._registry.get_agent(name))

        if len(agent_instances) < 2:
            raise ValueError("Concurrent execution requires at least two agents")

        if tools:
            logger.debug("Tools parameter acknowledged", tools=list(tools))

        builder = ConcurrentBuilder().participants(agent_instances)
        workflow = builder.build()
        messages = self._normalise_messages(task)
        events = await workflow.run(messages)

        aggregated: Dict[str, str] = {}
        for event in events:
            if isinstance(event, WorkflowOutputEvent) and event.data:
                text_blocks = []
                for msg in event.data:
                    text_blocks.append(getattr(msg, "text", ""))
                aggregated[event.source_executor_id] = "\n".join(filter(None, text_blocks))

        results = [
            {
                "agent": agent,
                "content": aggregated.get(agent, ""),
                "timestamp": datetime.utcnow().isoformat(),
            }
            for agent in agents
        ]
        summary_parts = [entry["content"] for entry in results if entry["content"]]
        summary = "\n".join(summary_parts) if summary_parts else None

        logger.info("Concurrent pattern completed", agent_results=len(results))
        return {
            "pattern": "concurrent",
            "task": self._summarise_task(task),
            "agents": agents,
            "results": results,
            "summary": summary,
        }

    async def execute_agent(
        self,
        *,
        agent_name: str,
        input_message: str | ChatMessage | Sequence[ChatMessage],
        context: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a single agent and return its textual output."""

        agent = await self._registry.get_agent(agent_name)
        response: AgentRunResponse = await agent.run(messages=input_message, context=context or {})
        output = ""
        if response and response.messages:
            last_message = response.messages[-1]
            output = getattr(last_message, "text", str(last_message))

        logger.info("Agent executed", agent=agent_name, execution_id=execution_id)
        return {
            "agent": agent_name,
            "output": output,
            "execution_id": execution_id,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_messages(task: str | ChatMessage | Sequence[ChatMessage]) -> List[ChatMessage]:
        if isinstance(task, list):
            return list(task)
        if isinstance(task, ChatMessage):
            return [task]
        return [ChatMessage(role=Role.USER, contents=[TextContent(text=str(task))])]

    @staticmethod
    def _summarise_task(task: str | ChatMessage | Sequence[ChatMessage]) -> str:
        if isinstance(task, str):
            return task[:120]
        if isinstance(task, ChatMessage):
            return getattr(task, "text", "")[:120]
        if isinstance(task, Sequence) and task:
            return MagenticOrchestrator._summarise_task(task[0])
        return ""


__all__ = ["MagenticOrchestrator", "ExecutionContext"]
