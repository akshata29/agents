"""
Session History API

Endpoints for managing and retrieving advisor session history.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import structlog

from ..persistence.cosmos_memory import CosmosMemoryStore
from ..models.persistence_models import AdvisorSession, SessionSearchResult
from ..infra.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/history", tags=["history"])

# Initialize Cosmos DB store
cosmos_store: Optional[CosmosMemoryStore] = None


async def get_cosmos_store() -> CosmosMemoryStore:
    """Get or initialize Cosmos DB store."""
    global cosmos_store
    
    if cosmos_store is None:
        settings = get_settings()
        cosmos_store = CosmosMemoryStore(
            endpoint=settings.COSMOSDB_ENDPOINT,
            database_name=settings.COSMOSDB_DATABASE,
            container_name=settings.COSMOSDB_CONTAINER,
            user_id="default_advisor",
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret
        )
        await cosmos_store.initialize()
    
    return cosmos_store


@router.get("/sessions")
async def get_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, completed, archived)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return")
) -> List[SessionSearchResult]:
    """
    Get list of all sessions with optional filters.
    Returns lightweight session summaries.
    """
    try:
        store = await get_cosmos_store()
        sessions = await store.get_all_sessions(
            user_id=user_id,
            limit=limit,
            status=status
        )
        
        logger.info(
            "Retrieved sessions",
            count=len(sessions),
            user_id=user_id,
            status=status
        )
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error retrieving sessions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> AdvisorSession:
    """
    Get complete session data by ID.
    Returns full session with transcript, analytics, and summaries.
    """
    try:
        store = await get_cosmos_store()
        session = await store.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        logger.info("Retrieved session", session_id=session_id)
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error retrieving session",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> JSONResponse:
    """Delete a session by ID."""
    try:
        store = await get_cosmos_store()
        await store.delete_session(session_id)
        
        logger.info("Session deleted", session_id=session_id)
        return JSONResponse(
            content={"message": f"Session {session_id} deleted successfully"}
        )
        
    except Exception as e:
        logger.error(
            "Error deleting session",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/archive")
async def archive_session(session_id: str) -> JSONResponse:
    """Archive a session (change status to 'archived')."""
    try:
        store = await get_cosmos_store()
        await store.archive_session(session_id)
        
        logger.info("Session archived", session_id=session_id)
        return JSONResponse(
            content={"message": f"Session {session_id} archived successfully"}
        )
        
    except Exception as e:
        logger.error(
            "Error archiving session",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(status_code=500, detail=str(e))
