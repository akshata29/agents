"""
Multimodal Insights Backend API

FastAPI application for multi-agent multimodal content processing and analysis.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import structlog

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import orchestration, files, export_router, sessions
from .services.task_orchestrator import TaskOrchestrator
from .services.file_handler import FileHandler
from .services.export_service import ExportService
from .infra.settings import Settings
from .infra.telemetry import get_telemetry
from .persistence.cosmos_memory import CosmosMemoryStore

logger = structlog.get_logger(__name__)

# Global state
task_orchestrator: Optional[TaskOrchestrator] = None
file_handler: Optional[FileHandler] = None
export_service: Optional[ExportService] = None
memory_store: Optional[CosmosMemoryStore] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global task_orchestrator, file_handler, export_service, memory_store
    
    # Startup
    logger.info("Starting Multimodal Insights Application")
    settings = Settings()
    telemetry = get_telemetry(settings)
    telemetry.initialize(app)
    
    # Initialize memory store
    memory_store = CosmosMemoryStore(settings)
    await memory_store.initialize()
    
    # Initialize file handler
    file_handler = FileHandler(settings)
    await file_handler.initialize()
    
    # Initialize export service
    export_service = ExportService(settings)
    await export_service.initialize()
    
    # Initialize task orchestrator with framework patterns
    task_orchestrator = TaskOrchestrator(settings, file_handler)
    await task_orchestrator.initialize()
    await task_orchestrator.initialize_agents()  # Register MAF-compatible agents
    
    # Wire up router dependencies
    orchestration.set_orchestrator(task_orchestrator)
    files.set_file_handler(file_handler, memory_store)
    export_router.set_export_service(export_service)
    
    # Store in app state for access in routes
    app.state.task_orchestrator = task_orchestrator
    app.state.file_handler = file_handler
    app.state.export_service = export_service
    app.state.memory_store = memory_store
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    if task_orchestrator:
        await task_orchestrator.shutdown()
    if export_service:
        await export_service.shutdown()
    if file_handler:
        await file_handler.shutdown()
    if memory_store:
        await memory_store.close()
    telemetry.shutdown()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Multimodal Insights API",
    description="Multi-agent system for processing and analyzing multimodal content (audio, video, PDF)",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orchestration.router)
app.include_router(files.router)
app.include_router(sessions.router)
app.include_router(export_router.router)

# Mount uploads and data directories (for file serving)
# app.add_mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ============= Health & Status =============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "multimodal-insights-api",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multimodal Insights API",
        "version": "1.0.0",
        "description": "Multi-agent system for multimodal content analysis",
        "features": [
            "Multimodal file processing (audio, video, PDF)",
            "Azure AI service integration (Speech, Document Intelligence)",
            "Sentiment analysis",
            "Flexible summarization with persona support",
            "Dynamic analytics",
            "Real-time execution tracking",
            "Export to multiple formats"
        ],
        "agents": [
            "Planner Agent (ReAct pattern)",
            "Multimodal Processor Agent",
            "Sentiment Analysis Agent",
            "Summarizer Agent",
            "Analytics Agent"
        ],
        "patterns": [
            "ReAct Pattern (Planning)",
            "Handoff Pattern (Execution)",
            "GroupChat Pattern (Collaboration)"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
