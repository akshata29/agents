"""
Summary API Router

WebSocket and REST endpoints for investment session summarization.
Integrates with transcription, sentiment, and recommendation data.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
import structlog

from ..infra.settings import get_settings
from ..agents.summarization_agent import InvestmentSummarizationAgent
from ..models.task_models import SessionSummary
from ..models.persistence_models import AdvisorSession
from ..persistence.cosmos_memory import CosmosMemoryStore

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/summary", tags=["summary"])


# In-memory storage (fallback for non-persisted data)
session_summaries: Dict[str, Dict[str, Any]] = {}
active_connections: Dict[str, WebSocket] = {}

# Cosmos DB store
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

class SummaryWebSocketManager:
    """Manages WebSocket connections for summarization."""
    
    def __init__(self, agent: InvestmentSummarizationAgent):
        self.agent = agent
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("SummaryWebSocketManager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Summary WebSocket connected", session_id=session_id)
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Summary WebSocket disconnected", session_id=session_id)
    
    async def send_summary_update(
        self,
        session_id: str,
        message: Dict[str, Any]
    ):
        """Send summary update to connected client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
                logger.debug(f"Summary update sent", session_id=session_id)
            except Exception as e:
                logger.error(f"Failed to send summary update", error=str(e))
    
    async def generate_and_stream_summary(
        self,
        session_id: str,
        transcript_segments: List[Dict[str, Any]],
        sentiment_data: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None,
        summary_type: str = "detailed",
        persona: str = "advisor"
    ):
        """Generate summary and stream progress."""
        try:
            # Send started event
            await self.send_summary_update(session_id, {
                "type": "summary_started",
                "session_id": session_id,
                "summary_type": summary_type,
                "persona": persona,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Generate summary
            result = await self.agent.generate_session_summary(
                transcript_segments=transcript_segments,
                sentiment_data=sentiment_data,
                recommendations=recommendations,
                session_id=session_id,
                summary_type=summary_type,
                persona=persona
            )
            
            # Store summary
            if session_id not in session_summaries:
                session_summaries[session_id] = {}
            
            session_summaries[session_id][persona] = result
            
            # Send completed event
            await self.send_summary_update(session_id, {
                "type": "summary_completed",
                "session_id": session_id,
                "persona": persona,
                "summary": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(
                f"Summary generated and sent",
                session_id=session_id,
                persona=persona
            )
            
        except Exception as e:
            logger.error(f"Error generating summary", error=str(e), exc_info=True)
            await self.send_summary_update(session_id, {
                "type": "summary_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })


# Initialize agent and manager
settings = get_settings()
summarization_agent = InvestmentSummarizationAgent(settings)
ws_manager = SummaryWebSocketManager(summarization_agent)


@router.websocket("/ws/{session_id}")
async def summary_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time summary generation.
    
    Messages from client:
    - {"action": "generate_summary", "transcript_segments": [...], "sentiment_data": {...}, "recommendations": {...}, "summary_type": "detailed", "persona": "advisor"}
    - {"action": "generate_all_personas", "transcript_segments": [...], "sentiment_data": {...}, "recommendations": {...}}
    - {"action": "extract_actions", "transcript_segments": [...]}
    
    Messages to client:
    - {"type": "summary_started", ...}
    - {"type": "summary_completed", "summary": {...}}
    - {"type": "summary_error", "error": "..."}
    """
    await ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message
            message = await websocket.receive_json()
            action = message.get("action")
            
            if action == "generate_summary":
                # Generate single persona summary
                transcript_segments = message.get("transcript_segments", [])
                sentiment_data = message.get("sentiment_data")
                recommendations = message.get("recommendations")
                summary_type = message.get("summary_type", "detailed")
                persona = message.get("persona", "advisor")
                
                if not transcript_segments:
                    await websocket.send_json({
                        "type": "error",
                        "error": "No transcript segments provided"
                    })
                    continue
                
                # Generate in background
                asyncio.create_task(
                    ws_manager.generate_and_stream_summary(
                        session_id=session_id,
                        transcript_segments=transcript_segments,
                        sentiment_data=sentiment_data,
                        recommendations=recommendations,
                        summary_type=summary_type,
                        persona=persona
                    )
                )
            
            elif action == "generate_all_personas":
                # Generate summaries for all personas
                transcript_segments = message.get("transcript_segments", [])
                sentiment_data = message.get("sentiment_data")
                recommendations = message.get("recommendations")
                
                if not transcript_segments:
                    await websocket.send_json({
                        "type": "error",
                        "error": "No transcript segments provided"
                    })
                    continue
                
                # Generate all personas in background
                for persona in ["advisor", "compliance", "client", "general"]:
                    asyncio.create_task(
                        ws_manager.generate_and_stream_summary(
                            session_id=session_id,
                            transcript_segments=transcript_segments,
                            sentiment_data=sentiment_data,
                            recommendations=recommendations,
                            summary_type="detailed",
                            persona=persona
                        )
                    )
            
            elif action == "extract_actions":
                # Extract action items
                transcript_segments = message.get("transcript_segments", [])
                
                if not transcript_segments:
                    await websocket.send_json({
                        "type": "error",
                        "error": "No transcript segments provided"
                    })
                    continue
                
                try:
                    action_items = await summarization_agent.extract_action_items(
                        transcript_segments=transcript_segments
                    )
                    
                    await websocket.send_json({
                        "type": "action_items_extracted",
                        "session_id": session_id,
                        "action_items": action_items,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Unknown action: {action}"
                })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        logger.info(f"Summary WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error(f"Summary WebSocket error", error=str(e), exc_info=True)
        ws_manager.disconnect(session_id)


@router.post("/generate/{session_id}")
async def generate_summary(
    session_id: str,
    request_body: Dict[str, Any] = Body(...)
):
    """
    Generate session summary via REST API.
    
    Request body:
    {
        "transcript_segments": [...],
        "sentiment_data": {...},
        "recommendations": {...},
        "summary_type": "detailed",
        "persona": "advisor"
    }
    """
    try:
        transcript_segments = request_body.get("transcript_segments", [])
        sentiment_data = request_body.get("sentiment_data")
        recommendations = request_body.get("recommendations")
        summary_type = request_body.get("summary_type", "detailed")
        persona = request_body.get("persona", "advisor")
        
        if not transcript_segments:
            raise HTTPException(status_code=400, detail="No transcript segments provided")
        
        # Generate summary
        result = await summarization_agent.generate_session_summary(
            transcript_segments=transcript_segments,
            sentiment_data=sentiment_data,
            recommendations=recommendations,
            session_id=session_id,
            summary_type=summary_type,
            persona=persona
        )
        
        # Store summary
        if session_id not in session_summaries:
            session_summaries[session_id] = {}
        
        session_summaries[session_id][persona] = result
        
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"Error generating summary", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-all-personas/{session_id}")
async def generate_all_persona_summaries(
    session_id: str,
    request_body: Dict[str, Any] = Body(...)
):
    """
    Generate summaries for all personas in parallel and save session to Cosmos DB.
    
    Request body:
    {
        "transcript_segments": [...],
        "sentiment_data": {...},
        "recommendations": {...}
    }
    """
    try:
        transcript_segments = request_body.get("transcript_segments", [])
        sentiment_data = request_body.get("sentiment_data")
        recommendations = request_body.get("recommendations")
        
        if not transcript_segments:
            raise HTTPException(status_code=400, detail="No transcript segments provided")
        
        # Generate all persona summaries
        results = await summarization_agent.generate_persona_summaries(
            transcript_segments=transcript_segments,
            sentiment_data=sentiment_data,
            recommendations=recommendations,
            session_id=session_id
        )
        
        # Store all summaries in memory
        session_summaries[session_id] = results
        
        # Save session to Cosmos DB
        try:
            store = await get_cosmos_store()
            
            # Calculate session metrics
            total_words = sum(len(seg.get("text", "").split()) for seg in transcript_segments)
            exchange_count = len(transcript_segments)
            
            # Extract client/advisor names if available
            client_name = None
            advisor_name = None
            for seg in transcript_segments:
                speaker = seg.get("speaker", "").lower()
                if "client" in speaker or "unknown" in speaker:
                    # Try to extract name from early transcript
                    pass
                elif "advisor" in speaker:
                    pass
            
            # Extract investment readiness from sentiment
            investment_readiness_score = None
            risk_tolerance = None
            key_phrases = []
            if sentiment_data:
                if isinstance(sentiment_data.get("investment_readiness"), dict):
                    investment_readiness_score = sentiment_data["investment_readiness"].get("score")
                if isinstance(sentiment_data.get("risk_tolerance"), dict):
                    risk_tolerance = sentiment_data["risk_tolerance"].get("level")
                key_phrases = sentiment_data.get("key_phrases", [])
            
            # Count decisions and actions from summaries
            decisions_count = 0
            action_items_count = 0
            for persona_data in results.values():
                if isinstance(persona_data, dict):
                    decisions_count = max(decisions_count, len(persona_data.get("decisions_made", [])))
                    action_items_count = max(action_items_count, len(persona_data.get("action_items", [])))
            
            # Create AdvisorSession model
            session = AdvisorSession(
                session_id=session_id,
                user_id="default_advisor",
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow(),
                status="completed",
                transcript=transcript_segments,
                total_words=total_words,
                exchange_count=exchange_count,
                sentiment_data=sentiment_data,
                recommendations=recommendations,
                summaries=results,
                client_name=client_name,
                advisor_name=advisor_name,
                investment_readiness_score=investment_readiness_score,
                risk_tolerance=risk_tolerance,
                key_phrases=key_phrases[:10] if key_phrases else [],
                decisions_count=decisions_count,
                action_items_count=action_items_count
            )
            
            await store.save_session(session)
            logger.info(
                "Session saved to Cosmos DB",
                session_id=session_id,
                exchange_count=exchange_count,
                total_words=total_words
            )
            
        except Exception as db_error:
            # Log but don't fail the request if DB save fails
            logger.error(
                "Failed to save session to Cosmos DB",
                error=str(db_error),
                session_id=session_id
            )
        
        return JSONResponse(content=results)
    
    except Exception as e:
        logger.error(f"Error generating multi-persona summaries", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-actions/{session_id}")
async def extract_action_items_endpoint(
    session_id: str,
    request_body: Dict[str, Any] = Body(...)
):
    """
    Extract action items from transcript.
    
    Request body:
    {
        "transcript_segments": [...]
    }
    """
    try:
        transcript_segments = request_body.get("transcript_segments", [])
        
        if not transcript_segments:
            raise HTTPException(status_code=400, detail="No transcript segments provided")
        
        action_items = await summarization_agent.extract_action_items(
            transcript_segments=transcript_segments
        )
        
        return JSONResponse(content={"action_items": action_items})
    
    except Exception as e:
        logger.error(f"Error extracting action items", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_summaries(
    session_id: str,
    persona: Optional[str] = Query(None, description="Filter by persona")
):
    """
    Get stored summaries for a session.
    
    Query params:
    - persona: Optional filter for specific persona (advisor, compliance, client, general)
    """
    if session_id not in session_summaries:
        raise HTTPException(status_code=404, detail=f"No summaries found for session {session_id}")
    
    summaries = session_summaries[session_id]
    
    if persona:
        if persona not in summaries:
            raise HTTPException(status_code=404, detail=f"No {persona} summary found for session {session_id}")
        return JSONResponse(content=summaries[persona])
    
    return JSONResponse(content=summaries)


@router.get("/session/{session_id}/personas/{persona}")
async def get_persona_summary(
    session_id: str,
    persona: str
):
    """Get summary for specific persona."""
    if session_id not in session_summaries:
        raise HTTPException(status_code=404, detail=f"No summaries found for session {session_id}")
    
    if persona not in session_summaries[session_id]:
        raise HTTPException(status_code=404, detail=f"No {persona} summary found for session {session_id}")
    
    return JSONResponse(content=session_summaries[session_id][persona])


@router.get("/sessions")
async def list_sessions():
    """List all sessions with summaries."""
    return JSONResponse(content={
        "sessions": list(session_summaries.keys()),
        "count": len(session_summaries)
    })


@router.delete("/session/{session_id}")
async def delete_session_summaries(session_id: str):
    """Delete all summaries for a session."""
    if session_id not in session_summaries:
        raise HTTPException(status_code=404, detail=f"No summaries found for session {session_id}")
    
    del session_summaries[session_id]
    
    return JSONResponse(content={"message": f"Summaries deleted for session {session_id}"})


@router.get("/capabilities")
async def get_capabilities():
    """Get summarization agent capabilities."""
    return JSONResponse(content=summarization_agent.get_capabilities())


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "agent": summarization_agent.name,
        "active_connections": len(ws_manager.active_connections),
        "stored_sessions": len(session_summaries),
        "timestamp": datetime.utcnow().isoformat()
    })
