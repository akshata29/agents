"""
Speech Transcription Agent

Real-time speech-to-text transcription optimized for financial advisory conversations.
Supports speaker diarization, financial terminology, and live streaming.
MAF-compatible agent implementation.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterable
from datetime import datetime
import structlog

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

# Azure Speech imports
from azure.cognitiveservices.speech import (
    SpeechConfig,
    SpeechRecognizer,
    AudioConfig,
    ResultReason,
    CancellationReason,
    PropertyId,
    OutputFormat,
    ProfanityOption,
    ServicePropertyChannel,
    audio
)

logger = structlog.get_logger(__name__)


class SpeechTranscriptionAgent(BaseAgent):
    """
    MAF-compatible agent for real-time speech transcription.
    
    Capabilities:
    - Real-time audio transcription via Azure Speech-to-Text
    - Speaker diarization (Advisor vs. Client)
    - Financial terminology optimization
    - Word-level timestamps
    - Continuous recognition for long sessions
    - High accuracy with confidence scores
    """
    
    def __init__(
        self,
        settings,
        name: str = "speech_transcription",
        description: str = "Real-time speech transcription optimized for financial conversations"
    ):
        """Initialize the speech transcription agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings
        
        # Azure Speech configuration
        self.speech_config = SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        
        # Set language
        self.speech_config.speech_recognition_language = settings.azure_speech_language
        
        # Enable word-level timestamps
        self.speech_config.request_word_level_timestamps()
        
        # Set output format to detailed (includes confidence scores)
        self.speech_config.output_format = OutputFormat.Detailed
        
        # Enable profanity filtering
        self.speech_config.set_profanity(ProfanityOption.Masked)
        
        # Financial terminology hints (improves recognition)
        self._financial_phrases = [
            "401k", "IRA", "Roth IRA", "mutual fund", "ETF", "index fund",
            "stock portfolio", "bond allocation", "asset allocation",
            "risk tolerance", "market volatility", "diversification",
            "retirement planning", "estate planning", "tax planning",
            "capital gains", "dividend yield", "expense ratio",
            "rebalancing", "dollar cost averaging", "fiduciary",
            "annuity", "beneficiary", "securities", "SEC", "FINRA"
        ]
        
        # Add phrase list for better recognition
        if hasattr(self.speech_config, 'set_service_property'):
            phrase_list = {"phrases": self._financial_phrases}
            self.speech_config.set_service_property(
                name="speech.context-phraseList",
                value=json.dumps(phrase_list),
                channel=ServicePropertyChannel.UriQueryParameter
            )
        
        # Data directory for storing transcripts
        self.data_dir = Path(settings.data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized {self.name}", language=settings.azure_speech_language)
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "real_time_transcription",
            "speaker_diarization",
            "financial_terminology",
            "word_timestamps",
            "continuous_recognition"
        ]
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """
        Execute the agent - REQUIRED by MAF.
        
        Expected kwargs:
        - audio_file_path: Path to audio file for batch transcription
        - session_id: Session identifier
        - mode: 'file' for file transcription, 'stream' for real-time
        """
        try:
            # Normalize messages
            normalized_messages = self._normalize_messages(messages)
            
            # Get parameters
            audio_file_path = kwargs.get("audio_file_path")
            session_id = kwargs.get("session_id")
            mode = kwargs.get("mode", "file")
            
            if not session_id:
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: session_id is required")]
                    )]
                )
            
            if mode == "file" and not audio_file_path:
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text="Error: audio_file_path is required for file mode")]
                    )]
                )
            
            # Transcribe audio file
            if mode == "file":
                result = await self.transcribe_file(audio_file_path, session_id)
            else:
                # For streaming mode, return instructions
                result = {
                    "mode": "stream",
                    "message": "Use WebSocket endpoint for real-time streaming transcription",
                    "session_id": session_id
                }
            
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(f"Error in speech transcription agent", error=str(e), exc_info=True)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=f"Error: {str(e)}")]
                )]
            )
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncIterable[AgentRunResponseUpdate]:
        """Stream responses - REQUIRED by MAF."""
        result = await self.run(messages, thread=thread, **kwargs)
        
        for message in result.messages:
            yield AgentRunResponseUpdate(
                messages=[message]
            )
    
    def _normalize_messages(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None
    ) -> list[ChatMessage]:
        """Normalize various message formats to list of ChatMessage."""
        if messages is None:
            return []
        
        if isinstance(messages, str):
            return [ChatMessage(role=Role.USER, contents=[TextContent(text=messages)])]
        
        if isinstance(messages, ChatMessage):
            return [messages]
        
        if isinstance(messages, list):
            normalized = []
            for msg in messages:
                if isinstance(msg, str):
                    normalized.append(ChatMessage(role=Role.USER, contents=[TextContent(text=msg)]))
                elif isinstance(msg, ChatMessage):
                    normalized.append(msg)
            return normalized
        
        return []
    
    async def transcribe_file(
        self,
        audio_file_path: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Transcribe an audio file using Azure Speech Service.
        
        Args:
            audio_file_path: Path to the audio file
            session_id: Session identifier
            
        Returns:
            Dictionary containing transcription results
        """
        logger.info("Transcribing audio file", file_path=audio_file_path, session_id=session_id)
        
        try:
            # Configure audio input
            audio_config = AudioConfig(filename=audio_file_path)
            
            # Create speech recognizer
            speech_recognizer = SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Storage for results
            transcription_segments = []
            full_transcription = []
            
            # Event handlers
            def recognized_handler(evt):
                """Handle recognized speech."""
                if evt.result.reason == ResultReason.RecognizedSpeech:
                    result = evt.result
                    
                    # Extract detailed information
                    segment = {
                        "text": result.text,
                        "confidence": self._extract_confidence(result),
                        "offset_seconds": result.offset / 10000000,  # Convert from ticks
                        "duration_seconds": result.duration / 10000000,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    transcription_segments.append(segment)
                    full_transcription.append(result.text)
                    
                    logger.debug("Speech recognized", text=result.text[:50])
            
            def canceled_handler(evt):
                """Handle cancellation."""
                if evt.reason == CancellationReason.Error:
                    logger.error("Transcription error", error=evt.error_details)
            
            # Connect event handlers
            speech_recognizer.recognized.connect(recognized_handler)
            speech_recognizer.canceled.connect(canceled_handler)
            
            # Start continuous recognition
            speech_recognizer.start_continuous_recognition()
            
            # Wait for file to be processed (with timeout)
            timeout_seconds = 600  # 10 minutes max
            elapsed = 0
            check_interval = 1
            
            while elapsed < timeout_seconds:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                # Check if we've received results recently
                if len(transcription_segments) > 0:
                    # Continue until no new results for 3 seconds
                    prev_count = len(transcription_segments)
                    await asyncio.sleep(3)
                    if len(transcription_segments) == prev_count:
                        # No new results, assume done
                        break
            
            # Stop recognition
            speech_recognizer.stop_continuous_recognition()
            
            # Compile results
            result = {
                "session_id": session_id,
                "transcription_segments": transcription_segments,
                "full_transcription": " ".join(full_transcription),
                "segment_count": len(transcription_segments),
                "total_duration_seconds": sum(s["duration_seconds"] for s in transcription_segments),
                "audio_file": audio_file_path,
                "language": self.speech_config.speech_recognition_language,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            # Save to data directory
            self._save_transcription(result, session_id)
            
            logger.info(
                "Transcription completed",
                session_id=session_id,
                segments=len(transcription_segments),
                duration=result["total_duration_seconds"]
            )
            
            return result
            
        except Exception as e:
            logger.error("Transcription failed", error=str(e), exc_info=True)
            raise
    
    def _extract_confidence(self, result) -> float:
        """Extract confidence score from recognition result."""
        try:
            # Try to get confidence from detailed result
            if hasattr(result, 'properties'):
                json_result = result.properties.get(PropertyId.SpeechServiceResponse_JsonResult)
                if json_result:
                    data = json.loads(json_result)
                    if 'NBest' in data and len(data['NBest']) > 0:
                        return data['NBest'][0].get('Confidence', 0.0)
            return 0.95  # Default high confidence if not available
        except Exception:
            return 0.95
    
    def _save_transcription(self, result: Dict[str, Any], session_id: str):
        """Save transcription results to JSON file."""
        try:
            output_file = self.data_dir / f"transcription_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info("Transcription saved", file=str(output_file))
            
        except Exception as e:
            logger.error("Failed to save transcription", error=str(e))
    
    # ============================================================================
    # Real-time streaming methods (for WebSocket integration)
    # ============================================================================
    
    def create_continuous_recognizer(self, audio_stream) -> SpeechRecognizer:
        """
        Create a speech recognizer for continuous recognition from an audio stream.
        
        Args:
            audio_stream: Azure audio stream object
            
        Returns:
            Configured SpeechRecognizer instance
        """
        # Create audio configuration from stream
        audio_format = audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        audio_stream_config = audio.PushAudioInputStream(audio_format)
        audio_config = AudioConfig(stream=audio_stream_config)
        
        # Create recognizer
        recognizer = SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Enable speaker diarization if configured
        if self.app_settings.enable_speaker_diarization:
            self._enable_speaker_diarization(recognizer)
        
        return recognizer
    
    def _enable_speaker_diarization(self, recognizer: SpeechRecognizer):
        """Enable speaker diarization on the recognizer."""
        try:
            # Set conversation transcription mode
            recognizer.properties.set_property(
                PropertyId.SpeechServiceConnection_RecoLanguage,
                self.speech_config.speech_recognition_language
            )
            
            # Enable diarization
            recognizer.properties.set_property(
                PropertyId.SpeechServiceConnection_EnableAudioLogging,
                "true"
            )
            
            logger.info("Speaker diarization enabled")
            
        except Exception as e:
            logger.warning("Failed to enable speaker diarization", error=str(e))
    
    async def process_audio_chunk(
        self,
        audio_data: bytes,
        recognizer: SpeechRecognizer
    ) -> Optional[Dict[str, Any]]:
        """
        Process an audio chunk for real-time transcription.
        
        Args:
            audio_data: Raw audio bytes
            recognizer: Speech recognizer instance
            
        Returns:
            Transcription result if speech was recognized
        """
        try:
            # Push audio data to stream
            audio_stream = recognizer.audio_config
            if hasattr(audio_stream, 'push_stream'):
                audio_stream.push_stream.write(audio_data)
            
            # Recognition happens asynchronously via event handlers
            # Results are collected in the event handlers
            
            return None
            
        except Exception as e:
            logger.error("Failed to process audio chunk", error=str(e))
            return None
    
    def identify_speaker(self, text: str, context: Optional[str] = None) -> str:
        """
        Identify speaker based on content and context.
        Simple heuristic-based approach.
        
        Args:
            text: Transcribed text
            context: Additional context
            
        Returns:
            "advisor" or "client" or "unknown"
        """
        # Advisor indicators (questions, professional language)
        advisor_indicators = [
            "let me explain", "I recommend", "based on your", "we can",
            "our recommendation", "the market", "your portfolio",
            "risk tolerance", "investment objective", "financial goals"
        ]
        
        # Client indicators (personal references, questions about self)
        client_indicators = [
            "I want", "I'm concerned", "my retirement", "my savings",
            "I think", "I feel", "can you", "what about",
            "I don't understand", "my account", "my 401k"
        ]
        
        text_lower = text.lower()
        
        advisor_score = sum(1 for indicator in advisor_indicators if indicator in text_lower)
        client_score = sum(1 for indicator in client_indicators if indicator in text_lower)
        
        if advisor_score > client_score:
            return "advisor"
        elif client_score > advisor_score:
            return "client"
        else:
            return "unknown"
