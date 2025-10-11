"""Simplified MCP client used by the Deep Research backend."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from .settings import Settings

logger = structlog.get_logger(__name__)


class MCPClient:
    """Minimal placeholder that satisfies the Foundation Workflow contracts."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings
        self._tools: Dict[str, Any] = {}

    async def initialize(self) -> None:  # pragma: no cover - async compatibility
        logger.info("MCP client initialised")

    async def shutdown(self) -> None:  # pragma: no cover - async compatibility
        logger.info("MCP client shutdown")
        self._tools.clear()

    def register_tool(self, name: str, tool: Any) -> None:
        self._tools[name] = tool
        logger.debug("Registered MCP tool", tool=name)

    def get_tool(self, name: str) -> Any:
        return self._tools.get(name)

    async def invoke_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        tool = self.get_tool(name)
        if not tool:
            raise KeyError(f"MCP tool not found: {name}")
        if callable(tool):
            result = tool(*args, **kwargs)
            if hasattr(result, "__await__"):
                return await result  # type: ignore[func-returns-value]
            return result
        raise TypeError(f"Registered MCP tool '{name}' is not callable")


__all__ = ["MCPClient"]
