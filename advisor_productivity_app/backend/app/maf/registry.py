"""Simplified agent registry used by the advisor productivity app."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentCapability(BaseModel):
    """Description of what an agent can do."""

    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_tools: list[str] = Field(default_factory=list)


class AgentMetadata(BaseModel):
    """Minimal metadata tracked for each registered agent."""

    id: str
    name: str
    description: str
    capabilities: list[AgentCapability] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


@dataclass
class _AgentRegistration:
    metadata: AgentMetadata
    agent: Any


class AgentRegistry:
    """Hold references to application agents and their metadata."""

    def __init__(self) -> None:
        self._agents: Dict[str, _AgentRegistration] = {}
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:  # pragma: no cover - simple noop
        """Initialize the registry (placeholder for parity with framework)."""

    async def register_agent(
        self,
        *,
        name: str,
        agent: Any,
        metadata: AgentMetadata,
    ) -> str:
        """Register a new agent; returns the metadata identifier."""

        async with self._lock:
            self._agents[name] = _AgentRegistration(metadata=metadata, agent=agent)
            return metadata.id

    async def get_agent(self, name: str) -> Optional[Any]:
        """Return a registered agent instance."""

        async with self._lock:
            registration = self._agents.get(name)
            if registration:
                registration.metadata.last_used = datetime.utcnow()
                return registration.agent
            return None

    async def get_metadata(self, name: str) -> Optional[AgentMetadata]:
        """Return the metadata for a registered agent, if present."""

        async with self._lock:
            registration = self._agents.get(name)
            return registration.metadata if registration else None
