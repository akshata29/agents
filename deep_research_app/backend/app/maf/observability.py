"""Lightweight observability hooks used by the Deep Research backend."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from .settings import Settings

logger = structlog.get_logger(__name__)


class ObservabilityService:
    """Thin async-friendly façade for telemetry calls.

    The original framework ships a rich integration with Application Insights
    and Azure Monitor.  For the Deep Research app we only need a handful of
    entry points so this class focuses on structured logging with the same
    method signatures to keep the rest of the code untouched.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings
        self._metadata: Dict[str, Any] = {}

    async def initialize(self) -> None:  # pragma: no cover - keep async signature
        logger.info("Observability service initialised")

    async def shutdown(self) -> None:  # pragma: no cover - keep async signature
        logger.info("Observability service shutdown")

    def set_execution_metadata(self, **metadata: Any) -> None:
        """Store execution-scoped metadata to enrich subsequent logs."""
        self._metadata.update(metadata)
        logger.debug("Observability metadata updated", metadata=self._metadata)

    def record_event(self, name: str, **properties: Any) -> None:
        logger.info(
            "Telemetry event",
            telemetry_event=name,
            **{**self._metadata, **properties},
        )

    def record_error(self, name: str, error: Exception, **properties: Any) -> None:
        logger.error(
            "Telemetry error",
            telemetry_event=name,
            error=str(error),
            **{**self._metadata, **properties},
        )

    def track_metric(self, name: str, value: float, **properties: Any) -> None:
        logger.info("Telemetry metric", metric=name, value=value, **{**self._metadata, **properties})


__all__ = ["ObservabilityService"]
