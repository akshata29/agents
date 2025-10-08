"""
Recommendation Router

Provides REST and WebSocket endpoints for investment recommendations.
Integrates with sentiment analysis for context-aware suggestions.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
import structlog

from ..agents.recommendation_agent import InvestmentRecommendationAgent
from ..models.task_models import (
    InvestmentRecommendation,
    RecommendationType
)
from ..infra.settings import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Initialize settings
settings = get_settings()

# Initialize recommendation agent
recommendation_agent = InvestmentRecommendationAgent(settings)


class RecommendationWebSocketManager:
    """Manages WebSocket connections for real-time recommendations."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "recommendations": [],
            "last_update": None
        }
        logger.info(
            "Recommendation WebSocket connected",
            session_id=session_id,
            total_connections=len(self.active_connections)
        )
    
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        logger.info(
            "Recommendation WebSocket disconnected",
            session_id=session_id,
            remaining_connections=len(self.active_connections)
        )
    
    async def send_recommendations(
        self,
        session_id: str,
        recommendations: Dict[str, Any]
    ):
        """Send recommendations to client."""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_json({
                    "type": "recommendations_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": recommendations
                })
                
                # Store in history
                if session_id in self.session_data:
                    self.session_data[session_id]["recommendations"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "recommendations": recommendations
                    })
                    self.session_data[session_id]["last_update"] = recommendations
                
            except Exception as e:
                logger.error(
                    "Failed to send recommendations",
                    session_id=session_id,
                    error=str(e)
                )
    
    async def send_error(self, session_id: str, error_message: str):
        """Send error message to client."""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_json({
                    "type": "error",
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": error_message
                })
            except Exception as e:
                logger.error(
                    "Failed to send error message",
                    session_id=session_id,
                    error=str(e)
                )
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.session_data.get(session_id)


# Global manager instance
recommendation_ws_manager = RecommendationWebSocketManager()


@router.websocket("/ws/{session_id}")
async def recommendation_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time recommendations.
    
    Client sends:
    {
        "type": "generate",
        "conversation_context": "recent conversation text",
        "sentiment_data": {...},
        "client_profile": {...}
    }
    
    Server sends:
    {
        "type": "recommendations_update",
        "timestamp": "ISO timestamp",
        "data": {recommendation results}
    }
    """
    await recommendation_ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "generate":
                # Extract context
                conversation_context = data.get("conversation_context", "")
                sentiment_data = data.get("sentiment_data", {})
                client_profile = data.get("client_profile", {})
                
                if not conversation_context:
                    await recommendation_ws_manager.send_error(
                        session_id,
                        "No conversation context provided"
                    )
                    continue
                
                # Generate recommendations
                try:
                    result = await recommendation_agent.generate_recommendations(
                        conversation_context=conversation_context,
                        sentiment_data=sentiment_data,
                        session_id=session_id,
                        client_profile=client_profile,
                        context=data
                    )
                    
                    # Send result to client
                    await recommendation_ws_manager.send_recommendations(
                        session_id,
                        result
                    )
                    
                except Exception as e:
                    logger.error(
                        "Recommendation generation failed",
                        session_id=session_id,
                        error=str(e),
                        exc_info=True
                    )
                    await recommendation_ws_manager.send_error(
                        session_id,
                        f"Recommendation generation failed: {str(e)}"
                    )
            
            elif message_type == "get_history":
                # Send recommendation history
                session_data = recommendation_ws_manager.get_session_data(session_id)
                if session_data:
                    await websocket.send_json({
                        "type": "history",
                        "data": session_data["recommendations"]
                    })
            
            elif message_type == "ping":
                # Heartbeat
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await recommendation_ws_manager.send_error(
                    session_id,
                    f"Unknown message type: {message_type}"
                )
    
    except WebSocketDisconnect:
        logger.info("Client disconnected", session_id=session_id)
        recommendation_ws_manager.disconnect(session_id)
    
    except Exception as e:
        logger.error(
            "WebSocket error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        recommendation_ws_manager.disconnect(session_id)


@router.post("/generate")
async def generate_recommendations(
    conversation_context: str,
    sentiment_data: Optional[Dict[str, Any]] = None,
    client_profile: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
):
    """
    REST endpoint for generating recommendations.
    
    Use for batch generation or historical analysis.
    For real-time recommendations, use the WebSocket endpoint.
    """
    try:
        if not conversation_context or len(conversation_context.strip()) == 0:
            raise HTTPException(status_code=400, detail="No conversation context provided")
        
        result = await recommendation_agent.generate_recommendations(
            conversation_context=conversation_context,
            sentiment_data=sentiment_data,
            session_id=session_id,
            client_profile=client_profile
        )
        
        return {
            "status": "success",
            "recommendations": result
        }
    
    except Exception as e:
        logger.error("Recommendation generation failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation generation failed: {str(e)}"
        )


@router.post("/filter")
async def filter_recommendations(
    recommendations: List[Dict[str, Any]],
    risk_tolerance: str,
    investment_readiness: Optional[float] = None
):
    """
    Filter existing recommendations by risk tolerance and readiness.
    
    Request body:
    {
        "recommendations": [...],
        "risk_tolerance": "conservative|moderate|aggressive|very_aggressive",
        "investment_readiness": 0.0-1.0 (optional)
    }
    """
    try:
        if not recommendations:
            raise HTTPException(status_code=400, detail="No recommendations provided")
        
        # Filter by risk tolerance
        filtered = await recommendation_agent.filter_recommendations_by_risk(
            recommendations=recommendations,
            risk_tolerance=risk_tolerance
        )
        
        # Filter by readiness if provided
        if investment_readiness is not None:
            filtered = [
                rec for rec in filtered
                if rec.get("suitable_for", {}).get("investment_readiness", 0) <= investment_readiness
            ]
        
        return {
            "status": "success",
            "original_count": len(recommendations),
            "filtered_count": len(filtered),
            "recommendations": filtered
        }
    
    except Exception as e:
        logger.error("Recommendation filtering failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation filtering failed: {str(e)}"
        )


@router.post("/prioritize")
async def prioritize_recommendations(
    recommendations: List[Dict[str, Any]],
    max_count: int = 5
):
    """
    Prioritize recommendations by confidence and priority.
    
    Returns top N recommendations sorted by priority (high→low) and confidence.
    """
    try:
        if not recommendations:
            raise HTTPException(status_code=400, detail="No recommendations provided")
        
        prioritized = await recommendation_agent.prioritize_recommendations(
            recommendations=recommendations,
            max_count=max_count
        )
        
        return {
            "status": "success",
            "original_count": len(recommendations),
            "prioritized_count": len(prioritized),
            "recommendations": prioritized
        }
    
    except Exception as e:
        logger.error("Recommendation prioritization failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation prioritization failed: {str(e)}"
        )


@router.get("/session/{session_id}/history")
async def get_recommendation_history(session_id: str):
    """Get recommendation history for a session."""
    session_data = recommendation_ws_manager.get_session_data(session_id)
    
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendation data found for session {session_id}"
        )
    
    return {
        "status": "success",
        "session_id": session_id,
        "connected_at": session_data.get("connected_at"),
        "history": session_data.get("recommendations", []),
        "last_update": session_data.get("last_update")
    }


@router.get("/session/{session_id}/summary")
async def get_recommendation_summary(session_id: str):
    """Get aggregated recommendation summary for a session."""
    session_data = recommendation_ws_manager.get_session_data(session_id)
    
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendation data found for session {session_id}"
        )
    
    history = session_data.get("recommendations", [])
    
    if not history:
        return {
            "status": "success",
            "session_id": session_id,
            "message": "No recommendation history available"
        }
    
    # Aggregate metrics
    total_recommendations = 0
    product_recs = 0
    education_recs = 0
    high_priority = 0
    avg_confidence = 0.0
    confidence_scores = []
    
    for item in history:
        recs_data = item.get("recommendations", {})
        
        investment_recs = recs_data.get("investment_recommendations", [])
        education_recs_list = recs_data.get("education_recommendations", [])
        
        total_recommendations += len(investment_recs) + len(education_recs_list)
        product_recs += len(investment_recs)
        education_recs += len(education_recs_list)
        
        for rec in investment_recs:
            if rec.get("priority") == "high":
                high_priority += 1
            if "confidence" in rec:
                confidence_scores.append(rec["confidence"])
    
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
    
    return {
        "status": "success",
        "session_id": session_id,
        "summary": {
            "total_recommendation_sets": len(history),
            "total_recommendations": total_recommendations,
            "product_recommendations": product_recs,
            "education_recommendations": education_recs,
            "high_priority_count": high_priority,
            "average_confidence": round(avg_confidence, 3),
            "last_update": session_data.get("last_update")
        }
    }


@router.get("/capabilities")
async def get_capabilities():
    """Get recommendation agent capabilities."""
    return recommendation_agent.get_capabilities()
