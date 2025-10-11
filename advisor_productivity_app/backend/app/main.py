"""
Advisor Productivity App - FastAPI Backend

Main application entry point with API routes and middleware.
"""

import os
import structlog
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.infra.settings import get_settings
from app.routers import transcription, sentiment, recommendations
from app.api import summary, entity_pii, orchestration, history

# Configure structured logging
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
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def _resolve_frontend_dist_path() -> Optional[Path]:
    """Locate the built frontend assets directory for SPA hosting."""
    candidates = []

    env_path = os.getenv("FRONTEND_DIST_PATH")
    if env_path:
        candidates.append(Path(env_path))

    current_path = Path(__file__).resolve()
    lineage = [current_path.parent, *current_path.parents]
    for parent in lineage:
        candidates.append(parent / "frontend" / "dist")
        candidates.append(parent / "static")

    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if resolved.exists():
            return resolved

    return None


FRONTEND_DIST_DIR = _resolve_frontend_dist_path()
if FRONTEND_DIST_DIR:
    logger.info("Serving built frontend", path=str(FRONTEND_DIST_DIR))
else:
    logger.warning("Frontend dist directory not found; defaulting to API-only responses")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting Advisor Productivity App backend")
    settings = get_settings()
    logger.info(
        "Configuration loaded",
        backend_port=settings.backend_port,
        data_dir=settings.data_directory
    )
    
    # Initialize OrchestrationService with MAF
    from app.services.orchestration_service import OrchestrationService
    from app.routers import transcription
    from app.api import orchestration as orchestration_api
    
    logger.info("Initializing OrchestrationService with MAF framework")
    orchestration_service = OrchestrationService(settings)
    await orchestration_service.initialize()
    logger.info("✓ OrchestrationService initialized with MAF Concurrent Pattern")
    
    # Inject orchestration service into routers
    transcription.set_orchestration_service(orchestration_service)
    logger.info("✓ OrchestrationService injected into transcription router")
    
    orchestration_api.set_orchestration_service(orchestration_service)
    logger.info("✓ OrchestrationService injected into orchestration API router")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Advisor Productivity App backend")


# Create FastAPI app
app = FastAPI(
    title="Advisor Productivity API",
    description="AI-powered investment advisor productivity platform with real-time transcription, sentiment analysis, and intelligent recommendations",
    version="0.1.0",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

SERVICE_STATUS_PAYLOAD = {
    "name": "Advisor Productivity API",
    "version": "0.1.0",
    "status": "running"
}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Serve the SPA shell or fall back to service status."""
    if FRONTEND_DIST_DIR:
        index_file = FRONTEND_DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return SERVICE_STATUS_PAYLOAD


@app.get("/api/status")
async def api_status():
    """Public API status endpoint providing service metadata."""
    return SERVICE_STATUS_PAYLOAD


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "advisor_productivity_app",
        "version": "0.1.0"
    }


@app.get("/api/config")
async def get_config():
    """Get public configuration."""
    return {
        "features": {
            "real_time_transcription": settings.enable_real_time_transcription,
            "speaker_diarization": settings.enable_speaker_diarization,
            "sentiment_analysis": settings.sentiment_analysis_enabled,
            "recommendations": settings.recommendation_enabled,
            "pii_detection": settings.pii_detection_enabled,
            "auto_summarization": settings.enable_auto_summarization,
            "compliance_mode": settings.compliance_mode_enabled
        },
        "settings": {
            "max_session_duration_hours": settings.max_session_duration_hours,
            "sentiment_window_seconds": settings.sentiment_window_seconds,
            "max_recommendations": settings.max_recommendations_per_session
        }
    }


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(transcription.router)
app.include_router(sentiment.router)
app.include_router(recommendations.router)
app.include_router(summary.router)
app.include_router(entity_pii.router)
app.include_router(orchestration.router)
app.include_router(history.router)


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc)
        }
    )


if FRONTEND_DIST_DIR:
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_single_page_app(full_path: str):
        """Serve static assets or fall back to the SPA index for client routes."""
        target_path = FRONTEND_DIST_DIR / full_path
        if target_path.is_file():
            return FileResponse(target_path)

        index_file = FRONTEND_DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        return JSONResponse(SERVICE_STATUS_PAYLOAD)


# ============================================================================
# Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
