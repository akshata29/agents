"""
Orchestration API Router

Unified API for managing sessions and coordinating all agents.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
import structlog

from ..services.orchestration_service import OrchestrationService
from ..infra.settings import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

# Global orchestration service instance (will be injected from main.py)
orchestration_service: Optional[OrchestrationService] = None


def set_orchestration_service(service: OrchestrationService):
    """Set the orchestration service instance (called from main.py)."""
    global orchestration_service
    orchestration_service = service


def get_orchestration_service() -> OrchestrationService:
    """Get the orchestration service instance."""
    if orchestration_service is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestration service not initialized"
        )
    return orchestration_service


@router.post("/sessions")
async def create_session(
    request_body: Dict[str, Any] = Body(...)
):
    """
    Create a new session.
    
    Request body:
    {
        "session_id": "session_xxx",
        "workflow_type": "standard_advisor_session",
        "config": {}
    }
    """
    try:
        service = get_orchestration_service()
        session_id = request_body.get("session_id")
        workflow_type = request_body.get("workflow_type", "standard_advisor_session")
        config = request_body.get("config")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        result = await service.create_session(
            session_id=session_id,
            workflow_type=workflow_type,
            config=config
        )
        
        return JSONResponse(content=result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating session", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start a session."""
    try:
        service = get_orchestration_service()
        result = await service.start_session(session_id)
        return JSONResponse(content=result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error starting session", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/transcript")
async def process_transcript(
    session_id: str,
    request_body: Dict[str, Any] = Body(...)
):
    """
    Process a transcript chunk.
    
    Request body:
    {
        "text": "Transcript text",
        "speaker": "Advisor",
        "is_final": true
    }
    """
    try:
        service = get_orchestration_service()
        text = request_body.get("text")
        speaker = request_body.get("speaker")
        is_final = request_body.get("is_final", False)
        
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        
        result = await service.process_transcript_chunk(
            session_id=session_id,
            text=text,
            speaker=speaker,
            is_final=is_final
        )
        
        return JSONResponse(content=result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error processing transcript", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/recommendations")
async def generate_recommendations(session_id: str):
    """Generate recommendations for a session."""
    try:
        service = get_orchestration_service()
        result = await service.generate_recommendations(session_id)
        return JSONResponse(content=result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error generating recommendations", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/summary")
async def generate_summary(
    session_id: str,
    request_body: Dict[str, Any] = Body(default={})
):
    """
    Generate summary for a session.
    
    Request body:
    {
        "personas": ["advisor", "compliance", "client"]
    }
    """
    try:
        service = get_orchestration_service()
        personas = request_body.get("personas")
        result = await service.generate_summary(
            session_id=session_id,
            personas=personas
        )
        return JSONResponse(content=result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error generating summary", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    request_body: Dict[str, Any] = Body(default={})
):
    """
    End a session.
    
    Request body:
    {
        "auto_summary": true
    }
    """
    try:
        service = get_orchestration_service()
        auto_summary = request_body.get("auto_summary", True)
        result = await service.end_session(
            session_id=session_id,
            auto_summary=auto_summary
        )
        return JSONResponse(content=result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error ending session", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session data."""
    service = get_orchestration_service()
    session = service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return JSONResponse(content=session)


@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status."""
    try:
        service = get_orchestration_service()
        status = await service.get_session_status(session_id)
        return JSONResponse(content=status)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error getting session status", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    """List all sessions."""
    service = get_orchestration_service()
    sessions = service.get_all_sessions()
    return JSONResponse(content={
        "sessions": sessions,
        "count": len(sessions)
    })


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "service": "orchestration_service",
        "agents": [
            "speech_transcription_agent",
            "sentiment_analysis_agent",
            "recommendation_engine_agent",
            "summarization_agent",
            "entity_pii_agent",
            "planner_agent"
        ]
    })
