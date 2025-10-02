"""
Telemetry and Observability Setup

Integrates with Azure Application Insights and OpenTelemetry.
"""

import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
import structlog

from .settings import Settings


logger = structlog.get_logger(__name__)


class TelemetryService:
    """Telemetry and observability service."""
    
    def __init__(self, settings: Settings):
        """Initialize telemetry service."""
        self.settings = settings
        self.tracer_provider: Optional[TracerProvider] = None
        self.instrumentor: Optional[FastAPIInstrumentor] = None
        
    def initialize(self, app=None):
        """Initialize telemetry with optional FastAPI app."""
        self._setup_logging()
        
        if self.settings.enable_agent_telemetry:
            self._setup_tracing()
            
            if app and self.instrumentor is None:
                # Instrument FastAPI
                self.instrumentor = FastAPIInstrumentor.instrument_app(app)
                logger.info("FastAPI telemetry instrumentation enabled")
    
    def _setup_logging(self):
        """Configure structured logging."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        logging.basicConfig(
            format="%(message)s",
            level=logging.INFO,
        )
        
        logger.info("Structured logging configured")
    
    def _setup_tracing(self):
        """Configure OpenTelemetry tracing."""
        # Set up tracer provider
        self.tracer_provider = TracerProvider()
        trace.set_tracer_provider(self.tracer_provider)
        
        # Add Azure Monitor exporter if configured
        if self.settings.applicationinsights_connection_string:
            exporter = AzureMonitorTraceExporter(
                connection_string=self.settings.applicationinsights_connection_string
            )
            span_processor = BatchSpanProcessor(exporter)
            self.tracer_provider.add_span_processor(span_processor)
            logger.info("Azure Monitor tracing enabled")
        else:
            logger.info("Tracing enabled without Azure Monitor export")
    
    def get_tracer(self, name: str):
        """Get a tracer for instrumentation."""
        return trace.get_tracer(name)
    
    def shutdown(self):
        """Shutdown telemetry service."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
        logger.info("Telemetry service shutdown complete")


# Global telemetry instance
_telemetry: Optional[TelemetryService] = None


def get_telemetry(settings: Optional[Settings] = None) -> TelemetryService:
    """Get or create telemetry singleton."""
    global _telemetry
    if _telemetry is None:
        from .settings import get_settings
        _telemetry = TelemetryService(settings or get_settings())
    return _telemetry
