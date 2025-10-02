"""
Observability Wrapper - Microsoft Agent Framework Observability Integration

Provides a thin wrapper around MAF's OpenTelemetry-based observability
for centralized configuration and custom metrics/spans.
"""

import os
from typing import Optional, Dict, Any
import structlog

from agent_framework.observability import (
    setup_observability as maf_setup_observability,
    get_tracer,
    get_meter
)

from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class ObservabilityService:
    """
    Observability service wrapping Microsoft Agent Framework's OpenTelemetry integration.
    
    Provides simplified configuration and access to MAF's built-in observability features:
    - Automatic agent invocation tracing
    - Chat operation spans
    - Tool execution tracking
    - Token usage metrics
    - Performance metrics
    """

    def __init__(self, settings: Settings):
        """Initialize observability service."""
        self.settings = settings
        self._initialized = False
        self._tracer = None
        self._meter = None
        
        logger.info("ObservabilityService created (not yet initialized)")

    async def initialize(self) -> None:
        """
        Initialize Microsoft Agent Framework observability.
        
        This sets up OpenTelemetry with the configured exporters and enables
        automatic instrumentation for all agent operations.
        """
        if self._initialized:
            logger.warning("ObservabilityService already initialized")
            return
        
        # Check if observability is enabled
        if hasattr(self.settings, 'observability') and hasattr(self.settings.observability, 'enabled'):
            if not self.settings.observability.enabled:
                logger.info("Observability is disabled in configuration, skipping initialization")
                self._initialized = True  # Mark as initialized to prevent re-attempts
                return
            
        try:
            logger.info("Initializing MAF observability...")
            
            # Build configuration from settings
            config = self._build_observability_config()
            
            # Setup MAF observability with configuration
            if config:
                maf_setup_observability(**config)
                logger.info("MAF observability configured", config=config)
            else:
                # Setup with defaults (will use environment variables)
                maf_setup_observability()
                logger.info("MAF observability initialized with default configuration")
            
            # Get tracer and meter for custom instrumentation
            self._tracer = get_tracer()
            self._meter = get_meter()
            
            self._initialized = True
            logger.info("ObservabilityService initialization complete")
            
        except Exception as e:
            logger.error("Failed to initialize observability", error=str(e))
            raise

    def _build_observability_config(self) -> Dict[str, Any]:
        """Build observability configuration from settings."""
        config = {}
        
        # Check settings for observability configuration
        if hasattr(self.settings, 'observability'):
            obs_settings = self.settings.observability
            
            # Enable sensitive data logging (prompts, responses)
            if hasattr(obs_settings, 'enable_sensitive_data'):
                config['enable_sensitive_data'] = obs_settings.enable_sensitive_data
            
            # OTLP endpoint (Jaeger, Zipkin, etc.)
            if hasattr(obs_settings, 'otlp_endpoint'):
                config['otlp_endpoint'] = obs_settings.otlp_endpoint
            
            # Azure Application Insights connection string
            if hasattr(obs_settings, 'applicationinsights_connection_string'):
                config['applicationinsights_connection_string'] = obs_settings.applicationinsights_connection_string
            
            # VS Code extension port
            if hasattr(obs_settings, 'vs_code_extension_port'):
                config['vs_code_extension_port'] = obs_settings.vs_code_extension_port
        
        # Also check environment variables (MAF uses these by default)
        # ENABLE_OTEL, ENABLE_SENSITIVE_DATA, OTLP_ENDPOINT, 
        # APPLICATIONINSIGHTS_CONNECTION_STRING, VS_CODE_EXTENSION_PORT
        
        return config

    async def shutdown(self) -> None:
        """Shutdown observability service."""
        if not self._initialized:
            return
            
        try:
            logger.info("Shutting down ObservabilityService")
            # MAF handles cleanup automatically
            self._initialized = False
            logger.info("ObservabilityService shutdown complete")
            
        except Exception as e:
            logger.error("Error during observability shutdown", error=str(e))

    def start_span(self, name: str, **attributes):
        """
        Create a custom span for tracing.
        
        Args:
            name: Span name
            **attributes: Additional span attributes
            
        Returns:
            Context manager for the span
        """
        if not self._initialized or not self._tracer:
            logger.warning("Observability not initialized, span will not be recorded")
            # Return a no-op context manager
            from contextlib import nullcontext
            return nullcontext()
        
        span = self._tracer.start_as_current_span(name)
        if attributes:
            # Set attributes on the span
            span_obj = span.__enter__()
            for key, value in attributes.items():
                span_obj.set_attribute(key, value)
        return span

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels/attributes for the metric
        """
        if not self._initialized or not self._meter:
            logger.warning("Observability not initialized, metric will not be recorded")
            return
        
        try:
            # Create or get counter
            counter = self._meter.create_counter(name)
            counter.add(value, labels or {})
        except Exception as e:
            logger.error("Failed to record metric", metric=name, error=str(e))

    def get_tracer(self):
        """Get the OpenTelemetry tracer for custom spans."""
        if not self._initialized:
            logger.warning("Observability not initialized")
            return None
        return self._tracer

    def get_meter(self):
        """Get the OpenTelemetry meter for custom metrics."""
        if not self._initialized:
            logger.warning("Observability not initialized")
            return None
        return self._meter


# Convenience function for backward compatibility
async def setup_observability(settings: Settings) -> ObservabilityService:
    """
    Setup and initialize observability service.
    
    Args:
        settings: Application settings
        
    Returns:
        Initialized ObservabilityService
    """
    service = ObservabilityService(settings)
    await service.initialize()
    return service
