"""
Entity & PII API Router

WebSocket and REST endpoints for entity extraction and PII detection/redaction.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
import structlog

from ..infra.settings import get_settings
from ..agents.entity_pii_agent import EntityPIIAgent

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/entity-pii", tags=["entity-pii"])


# In-memory storage (Phase 8 will use CosmosDB)
session_entities: Dict[str, Dict[str, Any]] = {}
active_connections: Dict[str, WebSocket] = {}


class EntityPIIWebSocketManager:
    """Manages WebSocket connections for entity/PII operations."""
    
    def __init__(self, agent: EntityPIIAgent):
        self.agent = agent
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("EntityPIIWebSocketManager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Entity/PII WebSocket connected", session_id=session_id)
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Entity/PII WebSocket disconnected", session_id=session_id)
    
    async def send_update(
        self,
        session_id: str,
        message: Dict[str, Any]
    ):
        """Send update to connected client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
                logger.debug(f"Entity/PII update sent", session_id=session_id)
            except Exception as e:
                logger.error(f"Failed to send update", error=str(e))
    
    async def process_extraction(
        self,
        session_id: str,
        text: str,
        redact_pii: bool = True
    ):
        """Process entity extraction and PII detection."""
        try:
            # Send started event
            await self.send_update(session_id, {
                "type": "extraction_started",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Extract entities and detect PII
            result = await self.agent.extract_all(text, redact_pii=redact_pii)
            
            # Store results
            session_entities[session_id] = result
            
            # Send completed event
            await self.send_update(session_id, {
                "type": "extraction_completed",
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(
                f"Extraction completed",
                session_id=session_id,
                entity_count=result["metadata"]["entity_count"],
                pii_count=result["metadata"]["pii_count"]
            )
            
        except Exception as e:
            logger.error(f"Error in extraction", error=str(e), exc_info=True)
            await self.send_update(session_id, {
                "type": "extraction_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })


# Initialize agent and manager
settings = get_settings()
entity_pii_agent = EntityPIIAgent(settings)
ws_manager = EntityPIIWebSocketManager(entity_pii_agent)


@router.websocket("/ws/{session_id}")
async def entity_pii_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time entity extraction and PII detection.
    
    Messages from client:
    - {"action": "extract_all", "text": "...", "redact_pii": true}
    - {"action": "extract_entities", "text": "..."}
    - {"action": "detect_pii", "text": "..."}
    - {"action": "redact_pii", "text": "..."}
    
    Messages to client:
    - {"type": "extraction_started", ...}
    - {"type": "extraction_completed", "result": {...}}
    - {"type": "extraction_error", "error": "..."}
    """
    await ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message
            message = await websocket.receive_json()
            action = message.get("action")
            text = message.get("text", "")
            
            if not text:
                await websocket.send_json({
                    "type": "error",
                    "error": "No text provided"
                })
                continue
            
            if action == "extract_all":
                redact_pii = message.get("redact_pii", True)
                asyncio.create_task(
                    ws_manager.process_extraction(
                        session_id=session_id,
                        text=text,
                        redact_pii=redact_pii
                    )
                )
            
            elif action == "extract_entities":
                try:
                    entities = await entity_pii_agent.extract_entities(text)
                    await websocket.send_json({
                        "type": "entities_extracted",
                        "session_id": session_id,
                        "entities": entities,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })
            
            elif action == "detect_pii":
                try:
                    pii_data = await entity_pii_agent.detect_pii(text)
                    await websocket.send_json({
                        "type": "pii_detected",
                        "session_id": session_id,
                        "pii": pii_data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })
            
            elif action == "redact_pii":
                try:
                    redaction_result = await entity_pii_agent.redact_pii(text)
                    await websocket.send_json({
                        "type": "pii_redacted",
                        "session_id": session_id,
                        "result": redaction_result,
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
        logger.info(f"Entity/PII WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error(f"Entity/PII WebSocket error", error=str(e), exc_info=True)
        ws_manager.disconnect(session_id)


@router.post("/extract-all/{session_id}")
async def extract_all_endpoint(
    session_id: str,
    request_body: Dict[str, Any] = Body(...)
):
    """
    Extract entities and detect PII via REST API.
    
    Request body:
    {
        "text": "Conversation text to analyze",
        "redact_pii": true
    }
    """
    try:
        text = request_body.get("text", "")
        redact_pii = request_body.get("redact_pii", True)
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        result = await entity_pii_agent.extract_all(text, redact_pii=redact_pii)
        
        # Store results
        session_entities[session_id] = result
        
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"Error in extract_all", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-entities")
async def extract_entities_endpoint(
    request_body: Dict[str, Any] = Body(...)
):
    """
    Extract entities only (no PII detection).
    
    Request body:
    {
        "text": "Text to analyze"
    }
    """
    try:
        text = request_body.get("text", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        entities = await entity_pii_agent.extract_entities(text)
        
        return JSONResponse(content={"entities": entities})
    
    except Exception as e:
        logger.error(f"Error extracting entities", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-pii")
async def detect_pii_endpoint(
    request_body: Dict[str, Any] = Body(...)
):
    """
    Detect PII only (no entity extraction).
    
    Request body:
    {
        "text": "Text to analyze"
    }
    """
    try:
        text = request_body.get("text", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        pii_data = await entity_pii_agent.detect_pii(text)
        
        return JSONResponse(content=pii_data)
    
    except Exception as e:
        logger.error(f"Error detecting PII", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redact-pii")
async def redact_pii_endpoint(
    request_body: Dict[str, Any] = Body(...)
):
    """
    Redact PII from text.
    
    Request body:
    {
        "text": "Text to redact",
        "replacement_patterns": {
            "ssn": "***-**-****",
            ...
        }
    }
    """
    try:
        text = request_body.get("text", "")
        replacement_patterns = request_body.get("replacement_patterns")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        result = await entity_pii_agent.redact_pii(text, replacement_patterns)
        
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"Error redacting PII", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-tickers")
async def extract_tickers_endpoint(
    request_body: Dict[str, Any] = Body(...)
):
    """
    Extract ticker symbols from text.
    
    Request body:
    {
        "text": "Text containing ticker symbols"
    }
    """
    try:
        text = request_body.get("text", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        tickers = await entity_pii_agent.extract_ticker_symbols(text)
        
        return JSONResponse(content={"tickers": tickers})
    
    except Exception as e:
        logger.error(f"Error extracting tickers", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_entities(session_id: str):
    """Get stored entities and PII data for a session."""
    if session_id not in session_entities:
        raise HTTPException(status_code=404, detail=f"No data found for session {session_id}")
    
    return JSONResponse(content=session_entities[session_id])


@router.get("/session/{session_id}/entities")
async def get_session_entities_only(session_id: str):
    """Get only extracted entities for a session."""
    if session_id not in session_entities:
        raise HTTPException(status_code=404, detail=f"No data found for session {session_id}")
    
    return JSONResponse(content={"entities": session_entities[session_id]["entities"]})


@router.get("/session/{session_id}/pii")
async def get_session_pii(session_id: str):
    """Get only PII data for a session."""
    if session_id not in session_entities:
        raise HTTPException(status_code=404, detail=f"No data found for session {session_id}")
    
    return JSONResponse(content={"pii": session_entities[session_id]["pii"]})


@router.get("/sessions")
async def list_sessions():
    """List all sessions with entity/PII data."""
    return JSONResponse(content={
        "sessions": list(session_entities.keys()),
        "count": len(session_entities)
    })


@router.delete("/session/{session_id}")
async def delete_session_data(session_id: str):
    """Delete entity/PII data for a session."""
    if session_id not in session_entities:
        raise HTTPException(status_code=404, detail=f"No data found for session {session_id}")
    
    del session_entities[session_id]
    
    return JSONResponse(content={"message": f"Data deleted for session {session_id}"})


@router.get("/capabilities")
async def get_capabilities():
    """Get entity/PII agent capabilities."""
    return JSONResponse(content=entity_pii_agent.get_capabilities())


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        "status": "healthy",
        "agent": entity_pii_agent.name,
        "active_connections": len(ws_manager.active_connections),
        "stored_sessions": len(session_entities),
        "timestamp": datetime.utcnow().isoformat()
    })
