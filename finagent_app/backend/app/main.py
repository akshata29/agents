"""
Financial Research Backend API

FastAPI application for multi-agent financial research.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import structlog

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncAzureOpenAI

from .models.dto import (
    SequentialResearchRequest, ConcurrentResearchRequest,
    OrchestrationResponse, SystemStatusResponse, AgentHealthResponse,
    OrchestrationPattern
)
from .services.orchestrator import FinancialOrchestrationService
from .infra.settings import get_settings
from .infra.telemetry import get_telemetry

logger = structlog.get_logger(__name__)

# Global state
orchestration_service: Optional[FinancialOrchestrationService] = None
websocket_connections: List[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestration_service
    
    # Startup
    logger.info("Starting Financial Research Application")
    settings = get_settings()
    telemetry = get_telemetry(settings)
    telemetry.initialize(app)
    
    # Initialize Azure OpenAI client
    azure_client = AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint
    )
    
    # Initialize orchestration service
    orchestration_service = FinancialOrchestrationService(
        settings=settings,
        azure_client=azure_client
    )
    
    # Register agents with framework registry
    await orchestration_service.initialize()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    telemetry.shutdown()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Financial Research API",
    description="Multi-agent financial research system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Health & Status =============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "financial-research-api"}


@app.get("/status", response_model=SystemStatusResponse)
async def system_status():
    """Get detailed system status."""
    agents_health = []
    
    if orchestration_service:
        for agent_id, agent in orchestration_service.agents.items():
            health = AgentHealthResponse(
                agent_id=agent_id,
                agent_name=agent.name,
                status="healthy",
                tools_available=agent.capabilities if hasattr(agent, 'capabilities') else [],
                error_rate=0.0
            )
            agents_health.append(health)
    
    active_runs = len(orchestration_service.list_active_runs()) if orchestration_service else 0
    
    return SystemStatusResponse(
        status="operational",
        agents=agents_health,
        active_executions=active_runs,
        mcp_connected=True,
        storage_connected=True,
        timestamp=datetime.utcnow()
    )


# ============= Orchestration Endpoints =============

@app.post("/orchestration/sequential", response_model=OrchestrationResponse)
async def run_sequential(request: SequentialResearchRequest):
    """
    Execute sequential research workflow.
    
    Agents run in order: Company → SEC → Earnings → Fundamentals → Technicals → Report
    This endpoint returns immediately with a run_id and processes in the background.
    """
    if not orchestration_service:
        raise HTTPException(status_code=503, detail="Orchestration service not available")
    
    try:
        logger.info(
            "=== Sequential research request received ===",
            ticker=request.ticker,
            scope=request.scope,
            depth=request.depth,
            include_pdf=request.include_pdf,
            year=request.year
        )
        
        # Generate run_id immediately
        import uuid
        run_id = f"seq-{request.ticker}-{uuid.uuid4().hex[:8]}"
        
        # Create initial response with "running" status
        initial_response = OrchestrationResponse(
            run_id=run_id,
            status="running",
            pattern=OrchestrationPattern.SEQUENTIAL,
            started_at=datetime.utcnow(),
            steps=[],
            final_report="",
            execution_time=0.0,
            ticker=request.ticker,
            timestamp=datetime.utcnow()
        )
        
        # Start background task for actual execution
        asyncio.create_task(execute_sequential_background(
            run_id=run_id,
            ticker=request.ticker,
            scope=[m.value for m in request.scope],
            depth=request.depth.value,
            include_pdf=request.include_pdf,
            year=request.year
        ))
        
        # Broadcast initial status
        await broadcast_execution_update(run_id, "started", initial_response.model_dump())
        
        return initial_response
        
    except Exception as e:
        logger.error("Sequential execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def execute_sequential_background(
    run_id: str,
    ticker: str,
    scope: List[str],
    depth: str,
    include_pdf: bool,
    year: Optional[int]
):
    """Execute sequential research in background and broadcast updates."""
    import time
    start_time = time.time()
    
    try:
        result = await orchestration_service.execute_sequential(
            ticker=ticker,
            scope=scope,
            depth=depth,
            include_pdf=include_pdf,
            year=year,
            run_id=run_id,  # Pass the run_id
            progress_callback=broadcast_execution_update  # Pass broadcast callback for real-time updates
        )
        
        duration = time.time() - start_time
        result.execution_time = duration
        
        logger.info(
            f"=== Sequential research completed ===",
            ticker=ticker,
            run_id=run_id,
            status=result.status,
            duration_seconds=round(duration, 2),
            steps_count=len(result.steps)
        )
        
        # Broadcast final completion
        await broadcast_execution_update(run_id, "completed", result.model_dump())
        
    except Exception as e:
        logger.error("Background sequential execution failed", error=str(e), run_id=run_id)
        # Broadcast error
        await broadcast_execution_update(run_id, "error", {"error": str(e)})


@app.post("/orchestration/concurrent", response_model=OrchestrationResponse)
async def run_concurrent(request: ConcurrentResearchRequest):
    """
    Execute concurrent research workflow.
    
    Agents run in parallel with result aggregation.
    This endpoint returns immediately with a run_id and processes in the background.
    """
    if not orchestration_service:
        raise HTTPException(status_code=503, detail="Orchestration service not available")
    
    try:
        logger.info("Concurrent research requested",
                    ticker=request.ticker, modules=request.modules)
        
        # Generate run_id immediately
        import uuid
        run_id = f"con-{request.ticker}-{uuid.uuid4().hex[:8]}"
        
        # Create initial response
        initial_response = OrchestrationResponse(
            run_id=run_id,
            status="running",
            pattern=OrchestrationPattern.CONCURRENT,
            started_at=datetime.utcnow(),
            steps=[],
            final_report="",
            execution_time=0.0,
            ticker=request.ticker,
            timestamp=datetime.utcnow()
        )
        
        # Start background task
        asyncio.create_task(execute_concurrent_background(
            run_id=run_id,
            ticker=request.ticker,
            modules=[m.value for m in request.modules],
            aggregation_strategy=request.aggregation_strategy,
            include_pdf=request.include_pdf,
            year=request.year
        ))
        
        await broadcast_execution_update(run_id, "started", initial_response.model_dump())
        
        return initial_response
        
    except Exception as e:
        logger.error("Concurrent execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def execute_concurrent_background(
    run_id: str,
    ticker: str,
    modules: List[str],
    aggregation_strategy: str,
    include_pdf: bool,
    year: Optional[int]
):
    """Execute concurrent research in background and broadcast updates."""
    import time
    start_time = time.time()
    
    try:
        result = await orchestration_service.execute_concurrent(
            ticker=ticker,
            modules=modules,
            aggregation_strategy=aggregation_strategy,
            include_pdf=include_pdf,
            year=year,
            run_id=run_id,
            progress_callback=broadcast_execution_update  # Real-time updates
        )
        
        duration = time.time() - start_time
        result.execution_time = duration
        
        logger.info(
            "=== Concurrent research completed ===",
            ticker=ticker,
            run_id=run_id,
            duration_seconds=round(duration, 2)
        )
        
        await broadcast_execution_update(run_id, "completed", result.model_dump())
        
    except Exception as e:
        logger.error("Background concurrent execution failed", error=str(e), run_id=run_id)
        await broadcast_execution_update(run_id, "error", {"error": str(e)})
        
        return result
        
    except Exception as e:
        logger.error("Concurrent execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestration/runs/{run_id}", response_model=OrchestrationResponse)
async def get_run_status(run_id: str):
    """Get status of a specific run."""
    if not orchestration_service:
        raise HTTPException(status_code=503, detail="Orchestration service not available")
    
    result = orchestration_service.get_run_status(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return result


@app.get("/orchestration/runs", response_model=List[OrchestrationResponse])
async def list_runs():
    """List all active runs."""
    if not orchestration_service:
        raise HTTPException(status_code=503, detail="Orchestration service not available")
    
    return orchestration_service.list_active_runs()


# ============= Agents Endpoints =============

@app.get("/agents")
async def list_agents():
    """List all available agents."""
    if not orchestration_service:
        raise HTTPException(status_code=503, detail="Orchestration service not available")
    
    agents_info = []
    for agent_id, agent in orchestration_service.agents.items():
        info = {
            "id": agent_id,
            "name": agent.name,
            "description": agent.description,
            "capabilities": agent.capabilities if hasattr(agent, 'capabilities') else []
        }
        agents_info.append(info)
    
    return {"agents": agents_info}


@app.get("/agents/{agent_id}/health", response_model=AgentHealthResponse)
async def get_agent_health(agent_id: str):
    """Get health status of a specific agent."""
    if not orchestration_service:
        raise HTTPException(status_code=503, detail="Orchestration service not available")
    
    agent = orchestration_service.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentHealthResponse(
        agent_id=agent_id,
        agent_name=agent.name,
        status="healthy",
        tools_available=agent.capabilities if hasattr(agent, 'capabilities') else [],
        error_rate=0.0
    )


# ============= WebSocket for Real-Time Updates =============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time execution updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "pong", "data": data})
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info("WebSocket client disconnected")


async def broadcast_execution_update(run_id: str, event_type: str, data: dict):
    """Broadcast execution update to all WebSocket clients."""
    message = {
        "type": event_type,
        "run_id": run_id,
        "data": data
    }
    
    disconnected = []
    for ws in websocket_connections:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.warning("Failed to send WebSocket message", error=str(e))
            disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)


# ============= Error Handlers =============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
