"""
Sentiment Analysis Router

Provides REST and WebSocket endpoints for real-time sentiment analysis.
Integrates with transcription stream to provide live sentiment insights.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
import structlog

from ..agents.sentiment_agent import InvestmentSentimentAgent
from ..models.task_models import (
    SentimentAnalysis,
    SentimentType,
    Session
)
from ..infra.settings import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/sentiment", tags=["sentiment"])

# Initialize settings
settings = get_settings()

# Initialize sentiment agent
sentiment_agent = InvestmentSentimentAgent(settings)


class SentimentWebSocketManager:
    """Manages WebSocket connections for real-time sentiment analysis."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "sentiment_history": [],
            "last_analysis": None
        }
        logger.info(
            "Sentiment WebSocket connected",
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
            "Sentiment WebSocket disconnected",
            session_id=session_id,
            remaining_connections=len(self.active_connections)
        )
    
    async def send_sentiment_update(
        self,
        session_id: str,
        sentiment_data: Dict[str, Any]
    ):
        """Send sentiment analysis update to client."""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_json({
                    "type": "sentiment_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": sentiment_data
                })
                
                # Store in history
                if session_id in self.session_data:
                    self.session_data[session_id]["sentiment_history"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "sentiment": sentiment_data
                    })
                    self.session_data[session_id]["last_analysis"] = sentiment_data
                
            except Exception as e:
                logger.error(
                    "Failed to send sentiment update",
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
sentiment_ws_manager = SentimentWebSocketManager()


@router.websocket("/ws/{session_id}")
async def sentiment_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time sentiment analysis.
    
    Listens for transcript segments and provides live sentiment updates.
    
    Client sends:
    {
        "type": "analyze",
        "text": "transcript segment",
        "speaker": "advisor|client",
        "context": {...}
    }
    
    Server sends:
    {
        "type": "sentiment_update",
        "timestamp": "ISO timestamp",
        "data": {sentiment analysis results}
    }
    """
    await sentiment_ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "analyze":
                # Extract content
                text = data.get("text", "")
                speaker = data.get("speaker")
                context = data.get("context", {})
                
                if not text:
                    await sentiment_ws_manager.send_error(
                        session_id,
                        "No text provided for sentiment analysis"
                    )
                    continue
                
                # Perform sentiment analysis
                try:
                    result = await sentiment_agent.analyze_investment_sentiment(
                        content=text,
                        session_id=session_id,
                        speaker=speaker,
                        context=context
                    )
                    
                    # Send result to client
                    await sentiment_ws_manager.send_sentiment_update(
                        session_id,
                        result
                    )
                    
                except Exception as e:
                    logger.error(
                        "Sentiment analysis failed",
                        session_id=session_id,
                        error=str(e),
                        exc_info=True
                    )
                    await sentiment_ws_manager.send_error(
                        session_id,
                        f"Sentiment analysis failed: {str(e)}"
                    )
            
            elif message_type == "get_history":
                # Send sentiment history
                session_data = sentiment_ws_manager.get_session_data(session_id)
                if session_data:
                    await websocket.send_json({
                        "type": "history",
                        "data": session_data["sentiment_history"]
                    })
            
            elif message_type == "ping":
                # Heartbeat
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await sentiment_ws_manager.send_error(
                    session_id,
                    f"Unknown message type: {message_type}"
                )
    
    except WebSocketDisconnect:
        logger.info("Client disconnected", session_id=session_id)
        sentiment_ws_manager.disconnect(session_id)
    
    except Exception as e:
        logger.error(
            "WebSocket error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        sentiment_ws_manager.disconnect(session_id)


@router.post("/analyze")
async def analyze_text_sentiment(
    text: str,
    speaker: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    REST endpoint for one-time sentiment analysis.
    
    Use for analyzing historical transcripts or batch processing.
    For real-time analysis, use the WebSocket endpoint.
    """
    try:
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="No text provided")
        
        result = await sentiment_agent.analyze_investment_sentiment(
            content=text,
            session_id=session_id,
            speaker=speaker
        )
        
        return {
            "status": "success",
            "sentiment": result
        }
    
    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sentiment analysis failed: {str(e)}"
        )


@router.post("/conversation/analyze")
async def analyze_conversation_flow(
    segments: List[Dict[str, Any]]
):
    """
    Analyze sentiment progression across multiple conversation segments.
    
    Request body:
    {
        "segments": [
            {
                "text": "transcript segment",
                "speaker": "advisor|client",
                "timestamp": "ISO timestamp",
                "sentiment": {...}  // Optional, will be analyzed if not provided
            }
        ]
    }
    """
    try:
        if not segments or len(segments) == 0:
            raise HTTPException(status_code=400, detail="No segments provided")
        
        # Analyze each segment if sentiment not provided
        for segment in segments:
            if "sentiment" not in segment and "text" in segment:
                sentiment = await sentiment_agent.analyze_investment_sentiment(
                    content=segment["text"],
                    speaker=segment.get("speaker")
                )
                segment["sentiment"] = sentiment
        
        # Analyze conversation flow
        flow_analysis = await sentiment_agent.analyze_conversation_flow(segments)
        
        return {
            "status": "success",
            "flow_analysis": flow_analysis,
            "segments_analyzed": len(segments)
        }
    
    except Exception as e:
        logger.error("Conversation flow analysis failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Conversation flow analysis failed: {str(e)}"
        )


@router.post("/compliance/check")
async def check_compliance(
    text: str,
    session_id: Optional[str] = None
):
    """
    Check conversation text for compliance concerns.
    
    Returns list of potential compliance issues with severity ratings.
    """
    try:
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="No text provided")
        
        concerns = await sentiment_agent.detect_compliance_concerns(
            content=text,
            context={"session_id": session_id}
        )
        
        return {
            "status": "success",
            "concerns": concerns,
            "requires_review": any(
                c.get("severity") in ["critical", "high"] 
                for c in concerns
            )
        }
    
    except Exception as e:
        logger.error("Compliance check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Compliance check failed: {str(e)}"
        )


@router.get("/session/{session_id}/history")
async def get_sentiment_history(session_id: str):
    """Get sentiment analysis history for a session."""
    session_data = sentiment_ws_manager.get_session_data(session_id)
    
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail=f"No sentiment data found for session {session_id}"
        )
    
    return {
        "status": "success",
        "session_id": session_id,
        "connected_at": session_data.get("connected_at"),
        "history": session_data.get("sentiment_history", []),
        "last_analysis": session_data.get("last_analysis")
    }


@router.get("/session/{session_id}/summary")
async def get_sentiment_summary(session_id: str):
    """Get aggregated sentiment summary for a session."""
    session_data = sentiment_ws_manager.get_session_data(session_id)
    
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail=f"No sentiment data found for session {session_id}"
        )
    
    history = session_data.get("sentiment_history", [])
    
    if not history:
        return {
            "status": "success",
            "session_id": session_id,
            "message": "No sentiment history available"
        }
    
    # Aggregate sentiment metrics
    sentiment_scores = []
    investment_readiness_scores = []
    emotions = []
    compliance_flags = []
    
    for item in history:
        sentiment = item.get("sentiment", {})
        
        if "sentiment_score" in sentiment:
            sentiment_scores.append(sentiment["sentiment_score"])
        
        if "investment_readiness" in sentiment:
            readiness = sentiment["investment_readiness"]
            if isinstance(readiness, dict) and "score" in readiness:
                investment_readiness_scores.append(readiness["score"])
        
        if "investment_emotions" in sentiment:
            emotions.extend(sentiment["investment_emotions"])
        
        if "compliance_flags" in sentiment:
            compliance_flags.extend(sentiment["compliance_flags"])
    
    # Calculate averages
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
    avg_readiness = sum(investment_readiness_scores) / len(investment_readiness_scores) if investment_readiness_scores else 0.0
    
    # Determine overall sentiment trend
    if len(sentiment_scores) >= 2:
        first_half = sentiment_scores[:len(sentiment_scores)//2]
        second_half = sentiment_scores[len(sentiment_scores)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_second > avg_first + 0.1:
            trend = "improving"
        elif avg_second < avg_first - 0.1:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    return {
        "status": "success",
        "session_id": session_id,
        "summary": {
            "total_analyses": len(history),
            "average_sentiment_score": round(avg_sentiment, 3),
            "average_investment_readiness": round(avg_readiness, 3),
            "sentiment_trend": trend,
            "total_emotions_detected": len(emotions),
            "compliance_flags_count": len(compliance_flags),
            "high_severity_flags": sum(
                1 for f in compliance_flags 
                if f.get("severity") in ["critical", "high"]
            ),
            "last_analysis": session_data.get("last_analysis")
        }
    }


@router.get("/capabilities")
async def get_capabilities():
    """Get sentiment agent capabilities."""
    return sentiment_agent.get_capabilities()
