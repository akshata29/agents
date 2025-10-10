"""Thin Magentic orchestrator wrapper built on Microsoft Agent Framework."""

from __future__ import annotations

import structlog

from .registry import AgentRegistry
from .settings import FrameworkSettings

logger = structlog.get_logger(__name__)


class MagenticOrchestrator:
    """Lightweight orchestrator exposing the subset used by the app."""

    def __init__(
        self,
        settings: FrameworkSettings | None = None,
        *,
        agent_registry: AgentRegistry | None = None,
    ) -> None:
        self.settings = settings or FrameworkSettings()
        self.agent_registry = agent_registry or AgentRegistry()
        logger.info("Advisor MAF orchestrator initialized")

    async def initialize(self) -> None:
        """Prepare internal services. Mirrors the upstream contract."""

        await self.agent_registry.initialize()
        logger.info("Advisor MAF orchestrator ready")
