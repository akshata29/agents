"""
Sessions API Router

Handles session history and retrieval endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel
import structlog

from ..persistence.cosmos_memory import CosmosMemoryStore
from ..models.task_models import Session, Plan, PlanWithSteps
from ..auth.auth_utils import get_authenticated_user_details
from .files import get_memory_store

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionWithDetails(BaseModel):
    """Session with enriched details for display."""
    id: str
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    timestamp: str
    # Enriched fields
    latest_objective: Optional[str] = None
    file_count: int = 0
    file_types: List[str] = []
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[SessionWithDetails])
async def list_sessions(
    request: Request,
    limit: int = 50,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """Get all sessions for the authenticated user with enriched details ordered by most recent."""
    # Extract authenticated user details
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    logger.info("Listing sessions with details", limit=limit, user_id=user_id)
    try:
        # Get sessions filtered by authenticated user_id
        sessions = await memory_store.get_all_sessions(limit=limit, user_id=user_id)
        
        # Enrich each session with latest plan objective and file info
        enriched_sessions = []
        for session in sessions:
            # Get latest plan for this session
            plans = await memory_store.get_plans_for_session(session.session_id)
            latest_objective = None
            if plans:
                latest_objective = plans[0].initial_goal  # Plans are sorted DESC by timestamp
            
            # Get file metadata for this session
            files = await memory_store.get_files_for_session(session.session_id)
            file_count = len(files)
            file_types = list(set([f.file_type.value for f in files])) if files else []
            
            enriched_session = SessionWithDetails(
                id=session.id,
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at.isoformat(),
                last_active=session.last_active.isoformat(),
                timestamp=session.timestamp.isoformat(),
                latest_objective=latest_objective,
                file_count=file_count,
                file_types=file_types
            )
            enriched_sessions.append(enriched_session)
        
        return enriched_sessions
    except Exception as e:
        logger.error("Failed to list sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """Get a specific session by ID."""
    logger.info("Getting session", session_id=session_id)
    try:
        session = await memory_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.get("/{session_id}/plans", response_model=List[Plan])
async def get_session_plans(
    session_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """Get all plans for a session."""
    logger.info("Getting session plans", session_id=session_id)
    try:
        plans = await memory_store.get_plans_for_session(session_id)
        return plans
    except Exception as e:
        logger.error("Failed to get session plans", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve plans")


@router.get("/{session_id}/plans/{plan_id}", response_model=PlanWithSteps)
async def get_session_plan_with_steps(
    session_id: str,
    plan_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """Get a specific plan with all its steps."""
    logger.info("Getting plan with steps", plan_id=plan_id, session_id=session_id)
    try:
        plan_with_steps = await memory_store.get_plan_with_steps(plan_id, session_id)
        if not plan_with_steps:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan_with_steps
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get plan with steps", error=str(e), plan_id=plan_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve plan")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """Delete a session and all related data (plans, steps, file metadata)."""
    logger.info("Deleting session", session_id=session_id)
    try:
        # Check if session exists first
        session = await memory_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete the session and all related items
        await memory_store.delete_session(session_id)
        return {"message": "Session deleted successfully", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete session", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail="Failed to delete session")
