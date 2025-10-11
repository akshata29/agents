"""Minimal async agent registry for the Deep Research application."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import structlog

from .settings import Settings

logger = structlog.get_logger(__name__)


@dataclass
class AgentRecord:
    """Container that keeps both the agent instance and a bit of metadata."""

    name: str
    agent: Any
    tags: tuple[str, ...] = ()
    description: Optional[str] = None


class AgentRegistry:
    """Async-safe agent registry with the minimal surface the app requires."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings
        self._records: Dict[str, AgentRecord] = {}
        self._lock = asyncio.Lock()
        logger.info("Agent registry initialised")

    async def initialize(self) -> None:
        """Placeholder for compatibility with the original framework API."""
        logger.debug("Agent registry ready")

    async def shutdown(self) -> None:
        """Cleanup hook – currently just clears in-memory state."""
        async with self._lock:
            self._records.clear()
        logger.info("Agent registry shutdown complete")

    async def register_agent(self, name: str, agent: Any, *, tags: Iterable[str] | None = None, description: str | None = None) -> None:
        """Register a new agent by name.

        Mirrors the original framework behaviour by raising ``ValueError`` when a
        duplicate registration is attempted so existing error handling keeps
        working as-is.
        """

        async with self._lock:
            if name in self._records:
                raise ValueError(f"Agent already registered: {name}")
            record = AgentRecord(name=name, agent=agent, tags=tuple(tags or ()), description=description)
            self._records[name] = record
            logger.info("Registered agent", agent=name, tags=record.tags)

    async def unregister_agent(self, name: str) -> None:
        async with self._lock:
            self._records.pop(name, None)
            logger.info("Unregistered agent", agent=name)

    async def get_agent(self, name: str) -> Any:
        async with self._lock:
            record = self._records.get(name)
        if not record:
            raise KeyError(f"Agent not found: {name}")
        return record.agent

    async def list_agents(self) -> list[str]:
        async with self._lock:
            return sorted(self._records)

    async def has_agent(self, name: str) -> bool:
        async with self._lock:
            return name in self._records


__all__ = ["AgentRegistry"]
