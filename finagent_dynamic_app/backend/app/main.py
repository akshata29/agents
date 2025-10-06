"""
Financial Research Backend API - Dynamic Planning

FastAPI application for multi-agent financial research with dynamic planning and approval workflow.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import orchestration
from .services.task_orchestrator import TaskOrchestrator
from .infra.settings import Settings
from .infra.telemetry import get_telemetry

logger = structlog.get_logger(__name__)

# Global state
task_orchestrator: Optional[TaskOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global task_orchestrator
    
    # Startup
    logger.info("Starting Financial Research Application (Dynamic)")
    settings = Settings()
    telemetry = get_telemetry(settings)
    telemetry.initialize(app)
    
    # Initialize task orchestrator with framework patterns
    task_orchestrator = TaskOrchestrator(settings)
    await task_orchestrator.initialize()
    
    # Store in app state for access in routes
    app.state.task_orchestrator = task_orchestrator
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    if task_orchestrator:
        await task_orchestrator.shutdown()
    telemetry.shutdown()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Financial Research API - Dynamic Planning",
    description="Multi-agent financial research with dynamic planning and approval workflow",
    version="2.0.0",
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


# ============= Health & Status =============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "financial-research-api-dynamic",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Financial Research API - Dynamic Planning",
        "version": "2.0.0",
        "description": "Multi-agent financial research with framework-based orchestration",
        "features": [
            "Dynamic plan generation using ReAct pattern",
            "Human-in-the-loop approval workflow",
            "Group chat pattern for multi-agent execution",
            "CosmosDB persistence for plans and conversations",
            "Microsoft Agent Framework integration"
        ],
        "endpoints": {
            "health": "/health",
            "create_plan": "POST /api/input_task",
            "get_plan": "GET /api/plans/{session_id}/{plan_id}",
            "list_plans": "GET /api/plans/{session_id}",
            "approve_step": "POST /api/approve_step",
            "approve_steps": "POST /api/approve_steps",
            "get_steps": "GET /api/steps/{session_id}/{plan_id}",
            "get_messages": "GET /api/messages/{session_id}",
            "docs": "/docs"
        }
    }


# ============= Error Handlers =============

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    logger.warning("ValueError occurred", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Mount static files (frontend build) if they exist
# This allows serving the frontend from the same container
# __file__ is /app/app/main.py, so parent.parent gives us /app
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists() and static_dir.is_dir():
    # Serve static files
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    
    # Serve index.html for all other routes (SPA support)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes."""
        # Don't interfere with API routes
        if full_path.startswith("api/") or full_path in ["health", "docs", "redoc", "openapi.json"]:
            raise HTTPException(status_code=404)
        
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
