"""
Transcription API endpoints for real-time audio processing and WebSocket streaming
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import logging
import structlog
from datetime import datetime

from ..agents.speech_transcription_agent import SpeechTranscriptionAgent
from ..infra.settings import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/transcription", tags=["transcription"])

# Global settings
settings = get_settings()

# Agent instance
transcription_agent = SpeechTranscriptionAgent(settings=settings)

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Store session data
sessions: Dict[str, dict] = {}


class TranscriptionWebSocketManager:
    """Manages WebSocket connections for transcription streaming"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("transcription_websocket_connected", session_id=session_id)
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("transcription_websocket_disconnected", session_id=session_id)
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to specific WebSocket"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSockets"""
        for connection in self.active_connections.values():
            await connection.send_json(message)


ws_manager = TranscriptionWebSocketManager()


@router.websocket("/ws/{session_id}")
async def transcription_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time transcription streaming
    
    Accepts audio data and streams back transcription results
    """
    await ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_json()
            
            action = data.get("action")
            
            if action == "start":
                # Initialize session
                if session_id not in sessions:
                    sessions[session_id] = {
                        "transcript": [],
                        "started_at": datetime.now().isoformat(),
                        "status": "active"
                    }
                
                await ws_manager.send_message(session_id, {
                    "type": "session_started",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                
            elif action == "stop":
                # Stop session
                if session_id in sessions:
                    sessions[session_id]["status"] = "stopped"
                    sessions[session_id]["ended_at"] = datetime.now().isoformat()
                
                await ws_manager.send_message(session_id, {
                    "type": "session_stopped",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                
            elif action == "get_transcript":
                # Return current transcript
                transcript = sessions.get(session_id, {}).get("transcript", [])
                await ws_manager.send_message(session_id, {
                    "type": "transcript",
                    "transcript": transcript,
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        logger.info("transcription_client_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("transcription_websocket_error", session_id=session_id, error=str(e))
        ws_manager.disconnect(session_id)


@router.post("/upload")
async def upload_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    Upload audio chunk for transcription
    
    Args:
        audio: Audio file chunk
        session_id: Session identifier
    
    Returns:
        Transcription result
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        logger.info("audio_chunk_received", 
                   session_id=session_id, 
                   size=len(audio_data))
        
        # Process with transcription agent
        # Note: This is a simplified version - you may need to adjust based on your agent's actual API
        transcription_result = await transcription_agent.run({
            "audio_data": audio_data,
            "session_id": session_id
        })
        
        # Extract transcript text
        transcript_text = transcription_result.get("text", "")
        
        if transcript_text:
            # Store in session
            if session_id not in sessions:
                sessions[session_id] = {
                    "transcript": [],
                    "started_at": datetime.now().isoformat(),
                    "status": "active"
                }
            
            transcript_entry = {
                "text": transcript_text,
                "timestamp": datetime.now().isoformat(),
                "speaker": "Unknown",  # Could be enhanced with speaker detection
                "is_final": True
            }
            
            sessions[session_id]["transcript"].append(transcript_entry)
            
            # Send via WebSocket if connected
            if session_id in ws_manager.active_connections:
                await ws_manager.send_message(session_id, {
                    "type": "transcript_chunk",
                    **transcript_entry
                })
            
            return JSONResponse(content={
                "success": True,
                "transcript": transcript_text,
                "timestamp": transcript_entry["timestamp"]
            })
        
        return JSONResponse(content={
            "success": True,
            "transcript": "",
            "message": "No speech detected"
        })
        
    except Exception as e:
        logger.error("audio_upload_error", 
                    session_id=session_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start/{session_id}")
async def start_transcription(session_id: str):
    """
    Start a new transcription session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session info
    """
    if session_id not in sessions:
        sessions[session_id] = {
            "transcript": [],
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }
    
    logger.info("transcription_session_started", session_id=session_id)
    
    return {
        "session_id": session_id,
        "status": "started",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/stop/{session_id}")
async def stop_transcription(session_id: str):
    """
    Stop an active transcription session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Final transcript
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id]["status"] = "stopped"
    sessions[session_id]["ended_at"] = datetime.now().isoformat()
    
    logger.info("transcription_session_stopped", session_id=session_id)
    
    return {
        "session_id": session_id,
        "status": "stopped",
        "transcript": sessions[session_id]["transcript"],
        "timestamp": datetime.now().isoformat()
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get transcription session data
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session data including transcript
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id]


@router.get("/session/{session_id}/transcript")
async def get_transcript(session_id: str):
    """
    Get current transcript for a session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Transcript array
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "transcript": sessions[session_id].get("transcript", []),
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a transcription session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Success message
    """
    if session_id in sessions:
        del sessions[session_id]
    
    if session_id in ws_manager.active_connections:
        ws_manager.disconnect(session_id)
    
    logger.info("transcription_session_deleted", session_id=session_id)
    
    return {
        "success": True,
        "message": f"Session {session_id} deleted"
    }


@router.get("/sessions")
async def list_sessions():
    """
    List all active transcription sessions
    
    Returns:
        List of session IDs and their status
    """
    return {
        "sessions": [
            {
                "session_id": sid,
                "status": data.get("status"),
                "started_at": data.get("started_at"),
                "transcript_length": len(data.get("transcript", []))
            }
            for sid, data in sessions.items()
        ]
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "SpeechTranscriptionAgent",
        "active_sessions": len(sessions),
        "active_connections": len(ws_manager.active_connections)
    }
