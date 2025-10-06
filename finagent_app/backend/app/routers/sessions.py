"""
Sessions API Router for Financial Research

Handles session history and research run retrieval endpoints.
All endpoints require authentication and filter by authenticated user.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import structlog

from ..models.persistence_models import ResearchSession, ResearchRun
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..auth.auth_utils import get_authenticated_user_details
from ..infra.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Global cosmos store instance
_cosmos_store: Optional[CosmosMemoryStore] = None


async def get_cosmos_store() -> CosmosMemoryStore:
    """Dependency to get or create Cosmos DB store."""
    global _cosmos_store
    
    if _cosmos_store is None:
        settings = get_settings()
        if not settings.cosmos_db_endpoint:
            raise HTTPException(
                status_code=503,
                detail="Cosmos DB not configured"
            )
        
        _cosmos_store = CosmosMemoryStore(
            endpoint=settings.cosmos_db_endpoint,
            database_name=settings.cosmos_db_database,
            container_name=settings.cosmos_db_container
        )
        await _cosmos_store.initialize()
    
    return _cosmos_store


class SessionWithDetails(BaseModel):
    """Session with enriched research run details for display."""
    id: str
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    # Enriched fields from research runs
    ticker: Optional[str] = None
    pattern: Optional[str] = None
    run_count: int = 0
    latest_status: Optional[str] = None
    total_execution_time: float = 0.0
    
    class Config:
        from_attributes = True


class RunSummary(BaseModel):
    """Summary of a research run."""
    run_id: str
    ticker: str
    pattern: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    execution_time: Optional[float] = None
    steps_count: int = 0
    has_pdf: bool = False
    summary: Optional[str] = None


@router.get("", response_model=List[SessionWithDetails])
async def list_sessions(
    request: Request,
    limit: int = Query(50, description="Maximum number of sessions to return"),
    cosmos: CosmosMemoryStore = Depends(get_cosmos_store)
):
    """
    Get all research sessions for the authenticated user with enriched details.
    
    Returns sessions ordered by most recent first, with summary information
    about research runs in each session.
    """
    # Extract authenticated user details
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Listing sessions", limit=limit, user_id=user_id)
    
    try:
        # Get sessions filtered by authenticated user
        sessions = await cosmos.get_all_sessions(user_id=user_id, limit=limit)
        
        # Enrich each session with research run details
        enriched_sessions = []
        for session in sessions:
            # Get runs for this session
            runs = await cosmos.get_runs_by_session(session.session_id)
            
            # Calculate aggregates
            ticker = None
            pattern = None
            latest_status = None
            total_execution_time = 0.0
            
            if runs:
                # Get latest run details
                latest_run = runs[0]  # Already sorted DESC by started_at
                ticker = latest_run.ticker
                pattern = latest_run.pattern
                latest_status = latest_run.status
                
                # Sum execution times
                total_execution_time = sum(
                    r.execution_time for r in runs if r.execution_time
                )
            
            enriched_session = SessionWithDetails(
                id=session.id,
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at.isoformat(),
                last_active=session.last_active.isoformat(),
                ticker=ticker,
                pattern=pattern,
                run_count=len(runs),
                latest_status=latest_status,
                total_execution_time=round(total_execution_time, 2)
            )
            enriched_sessions.append(enriched_session)
        
        logger.info("Sessions listed", count=len(enriched_sessions), user_id=user_id)
        return enriched_sessions
        
    except Exception as e:
        logger.error("Failed to list sessions", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/{session_id}", response_model=ResearchSession)
async def get_session(
    request: Request,
    session_id: str,
    cosmos: CosmosMemoryStore = Depends(get_cosmos_store)
):
    """
    Get a specific session by ID.
    
    Only returns the session if it belongs to the authenticated user.
    """
    # Extract authenticated user
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Getting session", session_id=session_id, user_id=user_id)
    
    try:
        session = await cosmos.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Security check: verify session belongs to authenticated user
        if session.user_id != user_id:
            logger.warning(
                "Unauthorized session access attempt",
                session_id=session_id,
                session_user=session.user_id,
                requesting_user=user_id
            )
            raise HTTPException(status_code=403, detail="Access denied")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.get("/{session_id}/runs", response_model=List[RunSummary])
async def get_session_runs(
    request: Request,
    session_id: str,
    cosmos: CosmosMemoryStore = Depends(get_cosmos_store)
):
    """
    Get all research runs for a specific session.
    
    Only returns runs if the session belongs to the authenticated user.
    """
    # Extract authenticated user
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Getting session runs", session_id=session_id, user_id=user_id)
    
    try:
        # First verify session belongs to user
        session = await cosmos.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get runs for this session
        runs = await cosmos.get_runs_by_session(session_id)
        
        # Convert to summaries
        run_summaries = [
            RunSummary(
                run_id=run.run_id,
                ticker=run.ticker,
                pattern=run.pattern,
                status=run.status,
                started_at=run.started_at.isoformat(),
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                execution_time=run.execution_time,
                steps_count=run.steps_count,
                has_pdf=bool(run.pdf_url),
                summary=run.summary
            )
            for run in runs
        ]
        
        return run_summaries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session runs", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve runs")


@router.get("/{session_id}/runs/{run_id}", response_model=ResearchRun)
async def get_run_details(
    request: Request,
    session_id: str,
    run_id: str,
    cosmos: CosmosMemoryStore = Depends(get_cosmos_store)
):
    """
    Get complete details of a specific research run.
    
    Includes full execution details, steps, messages, and artifacts.
    Only accessible if the run belongs to the authenticated user's session.
    """
    # Extract authenticated user
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Getting run details", run_id=run_id, session_id=session_id, user_id=user_id)
    
    try:
        # Verify session belongs to user
        session = await cosmos.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get the run
        run = await cosmos.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Verify run belongs to this session
        if run.session_id != session_id:
            raise HTTPException(status_code=404, detail="Run not found in this session")
        
        return run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get run details", error=str(e), run_id=run_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve run")


@router.get("/ticker/{ticker}", response_model=List[RunSummary])
async def get_runs_by_ticker(
    request: Request,
    ticker: str,
    limit: int = Query(20, description="Maximum number of runs to return"),
    cosmos: CosmosMemoryStore = Depends(get_cosmos_store)
):
    """
    Get all research runs for a specific ticker for the authenticated user.
    
    Useful for viewing research history on a particular stock.
    """
    # Extract authenticated user
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Getting runs by ticker", ticker=ticker, user_id=user_id, limit=limit)
    
    try:
        # Get runs for this ticker filtered by user
        runs = await cosmos.get_runs_by_ticker(ticker, user_id=user_id, limit=limit)
        
        # Convert to summaries
        run_summaries = [
            RunSummary(
                run_id=run.run_id,
                ticker=run.ticker,
                pattern=run.pattern,
                status=run.status,
                started_at=run.started_at.isoformat(),
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                execution_time=run.execution_time,
                steps_count=run.steps_count,
                has_pdf=bool(run.pdf_url),
                summary=run.summary
            )
            for run in runs
        ]
        
        logger.info("Runs by ticker retrieved", ticker=ticker, count=len(run_summaries))
        return run_summaries
        
    except Exception as e:
        logger.error("Failed to get runs by ticker", error=str(e), ticker=ticker)
        raise HTTPException(status_code=500, detail="Failed to retrieve runs")


@router.get("/user/history", response_model=List[RunSummary])
async def get_user_history(
    request: Request,
    limit: int = Query(50, description="Maximum number of runs to return"),
    cosmos: CosmosMemoryStore = Depends(get_cosmos_store)
):
    """
    Get complete research history for the authenticated user.
    
    Returns all research runs ordered by most recent first.
    """
    # Extract authenticated user
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Getting user history", user_id=user_id, limit=limit)
    
    try:
        # Get all runs for this user
        runs = await cosmos.get_runs_by_user(user_id, limit=limit)
        
        # Convert to summaries
        run_summaries = [
            RunSummary(
                run_id=run.run_id,
                ticker=run.ticker,
                pattern=run.pattern,
                status=run.status,
                started_at=run.started_at.isoformat(),
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                execution_time=run.execution_time,
                steps_count=run.steps_count,
                has_pdf=bool(run.pdf_url),
                summary=run.summary
            )
            for run in runs
        ]
        
        logger.info("User history retrieved", user_id=user_id, count=len(run_summaries))
        return run_summaries
        
    except Exception as e:
        logger.error("Failed to get user history", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve history")
