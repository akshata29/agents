"""
WebSocket Router for Real-time Speech Transcription

Handles WebSocket connections for streaming audio from the frontend
and returning real-time transcription results.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, UploadFile, File, Form
from azure.cognitiveservices.speech import (
    SpeechRecognizer,
    ResultReason,
    CancellationReason,
    audio
)

from app.infra.settings import get_settings, Settings
from app.agents.speech_transcription_agent import SpeechTranscriptionAgent
from app.models.task_models import TranscriptSegment, SpeakerType

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/transcription", tags=["transcription"])

# Global orchestration service instance (will be injected from main.py)
orchestration_service = None


def set_orchestration_service(service):
    """Set the orchestration service instance (called from main.py)."""
    global orchestration_service
    orchestration_service = service


class TranscriptionWebSocketManager:
    """Manages WebSocket connections for real-time transcription."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.recognizers: Dict[str, SpeechRecognizer] = {}
        self.audio_streams: Dict[str, audio.PushAudioInputStream] = {}
        self.transcription_buffers: Dict[str, list] = {}
        self.event_loops: Dict[str, asyncio.AbstractEventLoop] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, settings: Settings):
        """Accept WebSocket connection and setup speech recognizer."""
        try:
            await websocket.accept()
            
            self.active_connections[session_id] = websocket
            self.event_loops[session_id] = asyncio.get_running_loop()  # Store the event loop
            self.transcription_buffers[session_id] = []
            
            logger.info("websocket_accepted", session_id=session_id)
            
            # **CREATE SESSION IN ORCHESTRATION SERVICE**
            global orchestration_service
            if orchestration_service:
                try:
                    await orchestration_service.create_session(
                        session_id=session_id,
                        workflow_type="real_time_advisor_session"
                    )
                    await orchestration_service.start_session(session_id)
                    logger.info("✓ Session created in OrchestrationService", session_id=session_id)
                except Exception as e:
                    logger.error("Failed to create session in orchestration", session_id=session_id, error=str(e))
            
            # Create speech transcription agent
            agent = SpeechTranscriptionAgent(settings)
            
            # Setup audio stream with exact format from Microsoft documentation
            # AudioStreamFormat(samples_per_second, bits_per_sample, channels)
            # Must be: 16kHz, 16-bit, mono (1 channel)
            audio_format = audio.AudioStreamFormat(
                samples_per_second=16000,
                bits_per_sample=16,
                channels=1
            )
            
            # Create push stream with the format
            push_stream = audio.PushAudioInputStream(stream_format=audio_format)
            self.audio_streams[session_id] = push_stream
            
            # Create audio config from the stream
            audio_config = audio.AudioConfig(stream=push_stream)
            
            # Create recognizer with speech config and audio config
            recognizer = SpeechRecognizer(
                speech_config=agent.speech_config,
                audio_config=audio_config
            )
            
            self.recognizers[session_id] = recognizer
            
            # Setup event handlers following Microsoft documentation pattern
            # Use lambda functions to match the sample code pattern
            recognizer.recognizing.connect(
                lambda evt: print(f"[TRANSCRIPTION] RECOGNIZING: {evt.result.text}") or
                           logger.info("RECOGNIZING", 
                                       session_id=session_id, 
                                       text=evt.result.text) 
                if evt.result.reason == ResultReason.RecognizingSpeech and len(evt.result.text) > 0
                else None
            )
            
            recognizer.recognized.connect(
                lambda evt: self._handle_recognized(session_id, evt, agent)
                if evt.result.reason == ResultReason.RecognizedSpeech
                else logger.warning("NOMATCH", session_id=session_id)
                if evt.result.reason == ResultReason.NoMatch
                else None
            )
            
            recognizer.canceled.connect(
                lambda evt: self._handle_canceled(session_id, evt)
            )
            
            recognizer.session_stopped.connect(
                lambda evt: logger.info("SESSION_STOPPED", session_id=session_id)
            )
            
            recognizer.session_started.connect(
                lambda evt: print(f"[TRANSCRIPTION] SESSION STARTED for session {session_id}") or
                           logger.info("SESSION_STARTED", 
                                       session_id=session_id,
                                       message="Azure Speech SDK session is ACTIVE and listening")
            )
            
            # Start continuous recognition (async method)
            # Following Microsoft docs: speech_recognizer.start_continuous_recognition_async()
            recognizer.start_continuous_recognition_async()
            
            print(f"[TRANSCRIPTION] Started continuous recognition for session {session_id}")
            logger.info("continuous_recognition_started", 
                       session_id=session_id,
                       audio_format="16kHz_mono_16bit_PCM",
                       message="Azure Speech SDK recognizer is now listening for audio")
            
        except Exception as e:
            logger.error("failed_to_setup_websocket", 
                       session_id=session_id, 
                       error=str(e),
                       exc_info=True)
            # Send error to client if websocket is connected
            if session_id in self.active_connections:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to setup transcription",
                        "error": str(e)
                    })
                except:
                    pass
            raise
    
    def disconnect(self, session_id: str):
        """Disconnect and cleanup resources."""
        # Stop recognition
        if session_id in self.recognizers:
            try:
                # Use async method following Microsoft docs
                self.recognizers[session_id].stop_continuous_recognition_async()
            except Exception as e:
                logger.warning("Error stopping recognition", error=str(e))
            del self.recognizers[session_id]
        
        # Close audio stream
        if session_id in self.audio_streams:
            try:
                self.audio_streams[session_id].close()
            except Exception as e:
                logger.warning("Error closing audio stream", error=str(e))
            del self.audio_streams[session_id]
        
        # Remove connection
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        # Remove event loop reference
        if session_id in self.event_loops:
            del self.event_loops[session_id]
        
        # Clear buffer
        if session_id in self.transcription_buffers:
            del self.transcription_buffers[session_id]
        
        logger.info("WebSocket transcription session ended", session_id=session_id)
    
    async def push_audio_data(self, session_id: str, audio_data: bytes):
        """Push audio data to the recognition stream."""
        if session_id in self.audio_streams:
            try:
                print(f"[TRANSCRIPTION] Pushing {len(audio_data)} bytes to session {session_id}")
                logger.info("pushing_audio_to_stream", 
                          session_id=session_id, 
                          audio_size=len(audio_data))
                
                # Write raw PCM data to the push stream
                # The audio data should already be in raw PCM format (16-bit, 16kHz, mono)
                self.audio_streams[session_id].write(audio_data)
                logger.debug("audio_pushed_successfully", session_id=session_id)
            except Exception as e:
                logger.error("Failed to write audio data", 
                           session_id=session_id, 
                           error=str(e),
                           exc_info=True)
                raise
        else:
            logger.warning("no_audio_stream_for_session", session_id=session_id)
    
    def _handle_recognized(self, session_id: str, evt, agent):
        """Synchronously handle recognized speech event."""
        print(f"[TRANSCRIPTION] RECOGNIZED: {evt.result.text}")
        logger.info("RECOGNIZED", 
                   session_id=session_id, 
                   text=evt.result.text,
                   offset=evt.result.offset,
                   duration=evt.result.duration)
        
        # Create segment
        segment = {
            "text": evt.result.text,
            "confidence": self._extract_confidence(evt.result),
            "start_time_seconds": evt.result.offset / 10000000,
            "end_time_seconds": (evt.result.offset + evt.result.duration) / 10000000,
            "speaker": agent.identify_speaker(evt.result.text),
            "timestamp": datetime.utcnow().isoformat(),
            "is_final": True
        }
        
        # Store in buffer
        self.transcription_buffers[session_id].append(segment)
        
        # Send via WebSocket synchronously
        if session_id in self.active_connections and session_id in self.event_loops:
            websocket = self.active_connections[session_id]
            loop = self.event_loops[session_id]
            print(f"[TRANSCRIPTION] Sending to WebSocket: {segment['text'][:50]}...")
            
            # Schedule the coroutine on the stored event loop
            future = asyncio.run_coroutine_threadsafe(
                websocket.send_json({
                    "type": "transcript_chunk",
                    "text": segment["text"],
                    "timestamp": segment["timestamp"],
                    "speaker": segment["speaker"],
                    "is_final": segment["is_final"],
                    "confidence": segment.get("confidence", 0.0),
                    "start_time": segment["start_time_seconds"],
                    "end_time": segment["end_time_seconds"]
                }),
                loop
            )
            
            # Wait for completion and check for errors
            try:
                future.result(timeout=1.0)  # Wait up to 1 second
                print(f"[TRANSCRIPTION] ✓ Sent transcript_chunk to WebSocket")
                logger.info("sent_transcript_chunk", session_id=session_id, text=segment["text"])
                
                # Trigger downstream agents (sentiment, entity/PII analysis) asynchronously
                if session_id in self.event_loops:
                    loop = self.event_loops[session_id]
                    asyncio.run_coroutine_threadsafe(
                        self._trigger_downstream_agents(session_id, segment),
                        loop
                    )
                
            except Exception as e:
                print(f"[TRANSCRIPTION] ✗ Error sending to WebSocket: {e}")
                logger.error("websocket_send_error", session_id=session_id, error=str(e))
        else:
            print(f"[TRANSCRIPTION] ERROR: No WebSocket connection for session {session_id}")
    
    async def _trigger_downstream_agents(self, session_id: str, segment: Dict[str, Any]):
        """
        Trigger MAF Concurrent Pattern for sentiment, entity, and recommendation analysis.
        
        Uses OrchestrationService which orchestrates parallel agent execution.
        """
        try:
            global orchestration_service
            
            if not orchestration_service:
                logger.debug("orchestration_service_not_available", session_id=session_id)
                return
            
            text = segment.get("text", "")
            speaker = segment.get("speaker", "unknown")
            
            logger.info(
                "Triggering MAF Concurrent Pattern",
                session_id=session_id,
                text_preview=text[:50]
            )
            
            # Use orchestration service to process transcript chunk
            # This triggers MAF execute_concurrent() with sentiment, entity_pii, and recommendations agents
            result = await orchestration_service.process_transcript_chunk(
                session_id=session_id,
                text=text,
                speaker=speaker,
                is_final=True
            )
            
            logger.info(
                "MAF Concurrent Pattern completed",
                session_id=session_id,
                sentiment_updated=result.get("sentiment_updated"),
                entities_updated=result.get("entities_updated"),
                recommendations_updated=result.get("recommendations_updated"),
                agents_executed=result.get("agents_executed", [])
            )
            
            # Get session data to send updates via WebSockets
            session_data = orchestration_service.get_session(session_id)
            logger.info(
                "Attempting to send WebSocket updates",
                session_id=session_id,
                has_session_data=session_data is not None
            )
            if not session_data:
                logger.warning("No session data found for WebSocket broadcast", session_id=session_id)
                return
            
            # Send updates to respective WebSocket connections
            # Import WebSocket managers
            from app.routers.sentiment import sentiment_ws_manager
            from app.api.entity_pii import entity_ws_manager
            from app.routers.recommendations import recommendations_ws_manager
            
            # Debug logging
            logger.info(
                "Checking WebSocket connections",
                session_id=session_id,
                sentiment_active=session_id in sentiment_ws_manager.active_connections if sentiment_ws_manager else False,
                entity_active=session_id in entity_ws_manager.active_connections if entity_ws_manager else False,
                recommendations_active=session_id in recommendations_ws_manager.active_connections if recommendations_ws_manager else False
            )
            
            # Send sentiment update if available
            if sentiment_ws_manager and session_id in sentiment_ws_manager.active_connections:
                sentiment_data = session_data["data"].get("sentiment")
                if sentiment_data:
                    await sentiment_ws_manager.send_sentiment_update(session_id, sentiment_data)
                    logger.info("✓ Sent sentiment update via WebSocket", session_id=session_id)
                else:
                    logger.warning("Sentiment data is None/empty", session_id=session_id)
            else:
                logger.warning(
                    "Sentiment WebSocket not connected",
                    session_id=session_id,
                    has_manager=sentiment_ws_manager is not None
                )
            
            # Send entity/PII update if available
            if entity_ws_manager and session_id in entity_ws_manager.active_connections:
                entity_data = session_data["data"].get("entities")
                if entity_data:
                    await entity_ws_manager.send_entity_update(session_id, entity_data)
                    logger.info("✓ Sent entity/PII update via WebSocket", session_id=session_id)
            
            # Send recommendations update if available
            if recommendations_ws_manager and session_id in recommendations_ws_manager.active_connections:
                recommendations_data = session_data["data"].get("recommendations")
                if recommendations_data:
                    await recommendations_ws_manager.send_recommendations(session_id, recommendations_data)
                    logger.info("✓ Sent recommendations update via WebSocket", session_id=session_id)
                else:
                    logger.warning("Recommendations data is None/empty", session_id=session_id)
            else:
                logger.warning(
                    "Recommendations WebSocket not connected",
                    session_id=session_id,
                    has_manager=recommendations_ws_manager is not None
                )
                    
        except ImportError as e:
            # WebSocket managers not yet initialized, skip
            logger.warning("websocket_managers_not_available", session_id=session_id, error=str(e), exc_info=True)
        except Exception as e:
            logger.error("concurrent_pattern_error", session_id=session_id, error=str(e), exc_info=True)
            logger.error("trigger_downstream_agents_error", 
                        session_id=session_id, 
                        error=str(e))
    
    def _handle_canceled(self, session_id: str, evt):
        """Synchronously handle canceled event."""
        from azure.cognitiveservices.speech import CancellationDetails
        
        cancellation_details = evt.cancellation_details if hasattr(evt, 'cancellation_details') else None
        
        logger.error("CANCELED", 
                    session_id=session_id, 
                    reason=evt.reason,
                    error_code=cancellation_details.error_code if cancellation_details else None,
                    error_details=cancellation_details.error_details if cancellation_details else None)
        
        if evt.reason == CancellationReason.Error and session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            error_msg = cancellation_details.error_details if cancellation_details else str(evt.reason)
            
            import asyncio
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({
                    "type": "error",
                    "message": "Recognition error",
                    "error": error_msg
                }),
                loop
            )
    
    async def _send_interim_result(self, session_id: str, text: str):
        """Send interim transcription result."""
        if session_id in self.active_connections:
            try:
                message = {
                    "type": "interim",
                    "text": text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error("Failed to send interim result", error=str(e))
    
    async def _send_final_result(self, session_id: str, segment: Dict[str, Any]):
        """Send final transcription result."""
        if session_id in self.active_connections:
            try:
                message = {
                    "type": "transcript_chunk",
                    "text": segment.get("text", ""),
                    "timestamp": segment.get("timestamp"),
                    "speaker": segment.get("speaker", "Unknown"),
                    "is_final": True,
                    "confidence": segment.get("confidence", 0.0)
                }
                await self.active_connections[session_id].send_json(message)
                logger.info("sent_transcript_chunk", session_id=session_id, text=segment.get("text"))
            except Exception as e:
                logger.error("Failed to send final result", error=str(e))
    
    async def _send_error(self, session_id: str, error_details: str):
        """Send error message."""
        if session_id in self.active_connections:
            try:
                message = {
                    "type": "error",
                    "error": error_details,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error("Failed to send error message", error=str(e))
    
    def _extract_confidence(self, result) -> float:
        """Extract confidence score from recognition result."""
        try:
            from azure.cognitiveservices.speech import PropertyId
            
            if hasattr(result, 'properties'):
                json_result = result.properties.get(PropertyId.SpeechServiceResponse_JsonResult)
                if json_result:
                    data = json.loads(json_result)
                    if 'NBest' in data and len(data['NBest']) > 0:
                        return data['NBest'][0].get('Confidence', 0.0)
            return 0.95
        except Exception:
            return 0.95
    
    def get_session_transcript(self, session_id: str) -> list:
        """Get accumulated transcript for a session."""
        return self.transcription_buffers.get(session_id, [])


# Global manager instance
ws_manager = TranscriptionWebSocketManager()


@router.websocket("/ws/{session_id}")
async def transcribe_websocket(
    websocket: WebSocket,
    session_id: str,
    settings: Settings = Depends(get_settings)
):
    """
    WebSocket endpoint for real-time speech transcription.
    
    Expected message format from client:
    - Binary: Raw audio data (PCM 16-bit, 16kHz, mono)
    - JSON: Control messages
    
    Response format:
    - interim: { "type": "interim", "text": "...", "timestamp": "..." }
    - final: { "type": "final", "segment": {...}, "timestamp": "..." }
    - error: { "type": "error", "error": "...", "timestamp": "..." }
    """
    logger.info("WebSocket connection requested", session_id=session_id)
    
    try:
        # Accept connection and setup transcription
        await ws_manager.connect(websocket, session_id, settings)
        
        # Listen for audio data
        while True:
            # Receive message (can be binary audio or JSON control)
            message = await websocket.receive()
            
            if "bytes" in message:
                # Binary audio data
                audio_data = message["bytes"]
                await ws_manager.push_audio_data(session_id, audio_data)
                
            elif "text" in message:
                # JSON control message
                try:
                    control = json.loads(message["text"])
                    
                    if control.get("type") == "stop":
                        # Client requested stop
                        logger.info("Client requested transcription stop", session_id=session_id)
                        break
                    
                    elif control.get("type") == "get_transcript":
                        # Send accumulated transcript
                        transcript = ws_manager.get_session_transcript(session_id)
                        await websocket.send_json({
                            "type": "transcript",
                            "segments": transcript,
                            "count": len(transcript)
                        })
                    
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON control message", session_id=session_id)
            
            else:
                # Unknown message type
                logger.warning("Unknown message type received", session_id=session_id)
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
    
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e), exc_info=True)
    
    finally:
        # Cleanup
        ws_manager.disconnect(session_id)


@router.post("/upload")
async def upload_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    settings: Settings = Depends(get_settings)
):
    """
    Upload audio chunk for transcription (non-WebSocket alternative).
    
    This endpoint accepts audio data via HTTP POST for clients that
    prefer REST API over WebSocket streaming.
    
    Args:
        audio: Audio file (WAV, MP3, etc.)
        session_id: Session identifier
        settings: Application settings
        
    Returns:
        Transcription result
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        logger.info("audio_upload_received", 
                   session_id=session_id,
                   audio_size=len(audio_data),
                   filename=audio.filename)
        
        # If session has an active WebSocket with recognizer, push audio to it
        if session_id in ws_manager.audio_streams:
            # Push raw PCM audio data to the Azure Speech SDK stream
            # The audio should already be in raw PCM format (16-bit, 16kHz, mono)
            ws_manager.audio_streams[session_id].write(audio_data)
            
            return {
                "status": "success",
                "message": "Audio pushed to recognition stream",
                "session_id": session_id
            }
        else:
            # No active WebSocket - return message
            logger.warning("no_active_session", session_id=session_id)
            return {
                "status": "no_active_session",
                "message": f"No active WebSocket session found for {session_id}. Please connect via WebSocket first.",
                "session_id": session_id
            }
            
    except Exception as e:
        logger.error("audio_upload_error", 
                    session_id=session_id,
                    error=str(e))
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }


@router.get("/session/{session_id}/transcript")
async def get_session_transcript(session_id: str):
    """
    Get the accumulated transcript for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        JSON with transcript segments
    """
    transcript = ws_manager.get_session_transcript(session_id)
    
    return {
        "session_id": session_id,
        "segments": transcript,
        "count": len(transcript),
        "total_duration_seconds": sum(
            s.get("end_time_seconds", 0) - s.get("start_time_seconds", 0)
            for s in transcript
        )
    }


@router.post("/session/{session_id}/stop")
async def stop_transcription(session_id: str):
    """
    Stop transcription for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Status message
    """
    ws_manager.disconnect(session_id)
    
    return {
        "status": "success",
        "message": f"Transcription stopped for session {session_id}"
    }
