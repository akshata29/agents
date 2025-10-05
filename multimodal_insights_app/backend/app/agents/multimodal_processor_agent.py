"""
Multimodal Processor Agent

Handles processing of audio, video, and PDF files using Azure AI services.
Extracts content, metadata, and stores results locally in JSON format.
MAF-compatible agent implementation.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterable
from datetime import datetime
import structlog
import sys

# Microsoft Agent Framework imports
from agent_framework import BaseAgent, ChatMessage, Role, TextContent, AgentRunResponse, AgentRunResponseUpdate, AgentThread

# Azure imports
from azure.cognitiveservices.speech import (
    SpeechConfig,
    SpeechRecognizer,
    AudioConfig,
    ResultReason,
    audio
)
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential

# Video processing
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None

logger = structlog.get_logger(__name__)


class MultimodalProcessorAgent(BaseAgent):
    """
    MAF-compatible agent for processing multimodal files.
    
    Capabilities:
    - Audio: Transcription via Azure Speech-to-Text
    - Video: Audio extraction + transcription, frame analysis
    - PDF: Content extraction via Azure Document Intelligence
    - Metadata extraction and storage
    """
    
    def __init__(self, settings, name: str = "multimodal_processor", description: str = "Processes audio, video, and PDF files to extract content and metadata"):
        """Initialize the multimodal processor agent."""
        super().__init__(name=name, description=description)
        
        self.app_settings = settings  # Keep reference to app settings
        
        # Azure Speech configuration
        self.speech_config = SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        self.speech_config.speech_recognition_language = "en-US"
        
        # Azure Document Intelligence client
        self.doc_intel_client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)
        )
        
        # Data directory for storing extracted content
        self.data_dir = Path(settings.data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized {self.name}")
    
    @property
    def capabilities(self) -> List[str]:
        """Agent capabilities."""
        return [
            "audio_transcription",
            "video_processing", 
            "pdf_extraction"
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
        - file_path: Path to the file to process
        - file_type: Type of file (audio, video, pdf)
        - session_id: Session identifier
        - file_id: File identifier
        """
        try:
            # Normalize messages to list of ChatMessage
            normalized_messages = self._normalize_messages(messages)
            
            # Extract task from last message
            last_message = normalized_messages[-1] if normalized_messages else None
            task = last_message.text if last_message and hasattr(last_message, 'text') else ""
            
            # Get parameters from kwargs
            file_path = kwargs.get("file_path")
            file_type = kwargs.get("file_type")
            session_id = kwargs.get("session_id")
            file_id = kwargs.get("file_id")
            
            if not all([file_path, file_type, session_id, file_id]):
                error_msg = "Missing required parameters: file_path, file_type, session_id, or file_id"
                return AgentRunResponse(
                    messages=[ChatMessage(
                        role=Role.ASSISTANT,
                        contents=[TextContent(text=f"Error: {error_msg}")]
                    )]
                )
            
            # Process the file
            result = await self.process_file(file_path, file_type, session_id, file_id)
            
            # Return result as ChatMessage
            result_text = json.dumps(result, ensure_ascii=False, default=str)
            return AgentRunResponse(
                messages=[ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text=result_text)]
                )]
            )
            
        except Exception as e:
            logger.error(f"Error in multimodal processor", error=str(e), exc_info=True)
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
        # For file processing, we don't stream intermediate results
        # Just yield the final result
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
    
    async def process_file(
        self,
        file_path: str,
        file_type: str,
        session_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """
        Process a file based on its type.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (audio, video, pdf)
            session_id: Session identifier
            file_id: File identifier
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        logger.info(f"Processing file", file_path=file_path, file_type=file_type)
        
        try:
            if file_type == "audio":
                result = await self._process_audio(file_path, session_id, file_id)
            elif file_type == "video":
                result = await self._process_video(file_path, session_id, file_id)
            elif file_type == "pdf":
                result = await self._process_pdf(file_path, session_id, file_id)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Save extracted content to JSON
            self._save_extracted_content(result, session_id, file_id)
            
            logger.info(f"Successfully processed file", file_id=file_id)
            return result
            
        except Exception as e:
            logger.error(f"Failed to process file", error=str(e), file_id=file_id)
            raise
    
    async def _process_audio(
        self,
        file_path: str,
        session_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """Process audio file using Azure Speech Batch Transcription API."""
        logger.info("Processing audio file with batch transcription", file_path=file_path)
        
        import aiohttp
        from urllib.parse import urlparse
        from datetime import datetime, timedelta
        from azure.storage.blob import BlobSasPermissions, generate_blob_sas
        from azure.storage.blob.aio import BlobServiceClient
        from azure.identity.aio import ClientSecretCredential
        
        if not file_path.startswith("https://"):
            raise ValueError(f"Batch transcription requires blob URL, got: {file_path}")
        
        # Parse the blob URL
        parsed_url = urlparse(file_path)
        path_parts = parsed_url.path.lstrip('/').split('/', 1)
        container_name = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""
        
        try:
            # Generate SAS token using Azure AD credentials
            credential = ClientSecretCredential(
                tenant_id=self.app_settings.azure_tenant_id,
                client_id=self.app_settings.azure_client_id,
                client_secret=self.app_settings.azure_client_secret
            )
            
            storage_account_url = f"https://{self.app_settings.azure_blob_storage_name}.blob.core.windows.net"
            
            async with BlobServiceClient(
                account_url=storage_account_url,
                credential=credential
            ) as blob_service_client:
                # Get user delegation key (allows SAS generation with Azure AD)
                start_time = datetime.utcnow()
                expiry_time = start_time + timedelta(hours=1)
                
                user_delegation_key = await blob_service_client.get_user_delegation_key(
                    key_start_time=start_time,
                    key_expiry_time=expiry_time
                )
                
                # Generate SAS token for the blob
                sas_token = generate_blob_sas(
                    account_name=self.app_settings.azure_blob_storage_name,
                    container_name=container_name,
                    blob_name=blob_name,
                    user_delegation_key=user_delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry_time,
                    start=start_time
                )
                
                blob_url_with_sas = f"{file_path}?{sas_token}"
                logger.info("Generated SAS token for blob", blob_name=blob_name)
            
            await credential.close()
            
            # Now use batch transcription API with SAS URL
            speech_key = self.app_settings.AZURE_SPEECH_KEY
            speech_region = self.app_settings.AZURE_SPEECH_REGION
            base_url = f"https://{speech_region}.api.cognitive.microsoft.com/speechtotext/v3.2"
            
            headers = {
                "Ocp-Apim-Subscription-Key": speech_key,
                "Content-Type": "application/json"
            }
            
            transcription_request = {
                "contentUrls": [blob_url_with_sas],
                "locale": "en-US",
                "displayName": f"Transcription_{file_id}",
                "properties": {
                    "diarizationEnabled": False,
                    "wordLevelTimestampsEnabled": True,
                    "punctuationMode": "DictatedAndAutomatic",
                    "profanityFilterMode": "Masked"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                # Submit transcription job
                logger.info("Submitting batch transcription job")
                async with session.post(
                    f"{base_url}/transcriptions",
                    headers=headers,
                    json=transcription_request
                ) as response:
                    if response.status != 201:
                        error_text = await response.text()
                        raise Exception(f"Failed to create transcription: {response.status} - {error_text}")
                    
                    transcription_response = await response.json()
                    transcription_id = transcription_response["self"].split("/")[-1]
                    logger.info("Transcription job created", transcription_id=transcription_id)
                
                # Poll for completion
                max_polls = 60  # 5 minutes max
                poll_count = 0
                
                while poll_count < max_polls:
                    await asyncio.sleep(5)
                    poll_count += 1
                    
                    async with session.get(
                        f"{base_url}/transcriptions/{transcription_id}",
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to get transcription status: {response.status}")
                        
                        status_response = await response.json()
                        status = status_response["status"]
                        
                        logger.info("Transcription status", status=status, poll=poll_count)
                        
                        if status == "Succeeded":
                            # Get the transcription files
                            files_url = status_response["links"]["files"]
                            async with session.get(files_url, headers=headers) as files_response:
                                if files_response.status != 200:
                                    raise Exception(f"Failed to get transcription files: {files_response.status}")
                                
                                files_data = await files_response.json()
                                
                                # Find and download transcription result
                                transcription_text = ""
                                for file_info in files_data["values"]:
                                    if file_info["kind"] == "Transcription":
                                        result_url = file_info["links"]["contentUrl"]
                                        async with session.get(result_url) as result_response:
                                            if result_response.status != 200:
                                                raise Exception(f"Failed to download result: {result_response.status}")
                                            
                                            result_data = await result_response.json()
                                            
                                            # Extract combined text
                                            phrases = []
                                            if "combinedRecognizedPhrases" in result_data:
                                                for phrase in result_data["combinedRecognizedPhrases"]:
                                                    if "display" in phrase:
                                                        phrases.append(phrase["display"])
                                            
                                            transcription_text = " ".join(phrases)
                                            logger.info("Transcription extracted", length=len(transcription_text))
                                            break
                            
                            # Cleanup: Delete the transcription job
                            try:
                                async with session.delete(
                                    f"{base_url}/transcriptions/{transcription_id}",
                                    headers=headers
                                ):
                                    logger.info("Transcription job deleted")
                            except Exception as e:
                                logger.warning("Failed to delete transcription job", error=str(e))
                            
                            return {
                                "file_id": file_id,
                                "session_id": session_id,
                                "file_type": "audio",
                                "transcription": transcription_text,
                                "text_content": transcription_text,
                                "audio_metadata": {
                                    "duration": status_response.get("duration"),
                                    "format": Path(file_path).suffix,
                                    "language": "en-US"
                                },
                                "processing_timestamp": datetime.utcnow().isoformat()
                            }
                        
                        elif status == "Failed":
                            error_msg = status_response.get("properties", {}).get("error", "Unknown error")
                            raise Exception(f"Transcription failed: {error_msg}")
                
                raise Exception(f"Transcription timed out after {max_polls * 5} seconds")
        
        except Exception as e:
            logger.error("Batch transcription failed", error=str(e), exc_info=True)
            raise
    
    async def _process_video(
        self,
        file_path: str,
        session_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """Process video file by extracting audio and transcribing."""
        logger.info("Processing video file", file_path=file_path)
        
        if VideoFileClip is None:
            raise ImportError("moviepy is required for video processing")
        
        # Extract audio from video
        video = VideoFileClip(file_path)
        audio_path = str(Path(file_path).with_suffix('.wav'))
        
        if video.audio is not None:
            video.audio.write_audiofile(audio_path, logger=None)
            
            # Process extracted audio
            audio_result = await self._process_audio(audio_path, session_id, file_id)
            
            # Clean up temporary audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            # Add video-specific metadata
            audio_result["file_type"] = "video"
            audio_result["audio_metadata"]["video_duration"] = video.duration
            audio_result["audio_metadata"]["video_fps"] = video.fps
            audio_result["audio_metadata"]["video_size"] = (video.w, video.h)
            
            video.close()
            return audio_result
        else:
            video.close()
            return {
                "file_id": file_id,
                "session_id": session_id,
                "file_type": "video",
                "transcription": None,
                "text_content": "Video has no audio track",
                "audio_metadata": {
                    "has_audio": False
                },
                "extraction_metadata": {
                    "service": "moviepy",
                    "timestamp": str(asyncio.get_event_loop().time())
                }
            }
    
    async def _process_pdf(
        self,
        file_path: str,
        session_id: str,
        file_id: str
    ) -> Dict[str, Any]:
        """Process PDF file using Azure Document Intelligence."""
        logger.info("Processing PDF file", file_path=file_path)
        
        # Check if file_path is a URL or local file
        if file_path.startswith("https://"):
            # For blob URLs, we need to use begin_analyze_document_from_url
            # But first, generate a SAS token if needed
            from urllib.parse import urlparse
            from datetime import datetime, timedelta
            from azure.storage.blob import BlobSasPermissions, generate_blob_sas
            from azure.storage.blob.aio import BlobServiceClient
            from azure.identity.aio import ClientSecretCredential
            
            parsed_url = urlparse(file_path)
            path_parts = parsed_url.path.lstrip('/').split('/', 1)
            container_name = path_parts[0]
            blob_name = path_parts[1] if len(path_parts) > 1 else ""
            
            # Generate SAS token for the blob
            credential = ClientSecretCredential(
                tenant_id=self.app_settings.azure_tenant_id,
                client_id=self.app_settings.azure_client_id,
                client_secret=self.app_settings.azure_client_secret
            )
            
            storage_account_url = f"https://{self.app_settings.azure_blob_storage_name}.blob.core.windows.net"
            
            async with BlobServiceClient(
                account_url=storage_account_url,
                credential=credential
            ) as blob_service_client:
                start_time = datetime.utcnow()
                expiry_time = start_time + timedelta(hours=1)
                
                user_delegation_key = await blob_service_client.get_user_delegation_key(
                    key_start_time=start_time,
                    key_expiry_time=expiry_time
                )
                
                sas_token = generate_blob_sas(
                    account_name=self.app_settings.azure_blob_storage_name,
                    container_name=container_name,
                    blob_name=blob_name,
                    user_delegation_key=user_delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry_time
                )
                
                blob_url_with_sas = f"{file_path}?{sas_token}"
            
            # Analyze document from URL
            logger.info("Analyzing PDF from blob URL", blob_url=file_path)
            poller = self.doc_intel_client.begin_analyze_document(
                "prebuilt-layout",
                AnalyzeDocumentRequest(url_source=blob_url_with_sas),
                output_content_format=DocumentContentFormat.MARKDOWN
            )
        else:
            # For local files, read and analyze from bytes
            logger.info("Analyzing PDF from local file", file_path=file_path)
            with open(file_path, "rb") as f:
                pdf_content = f.read()
            
            poller = self.doc_intel_client.begin_analyze_document(
                "prebuilt-layout",
                pdf_content,
                output_content_format=DocumentContentFormat.MARKDOWN
            )
        
        result = poller.result()
        
        # Extract text content (markdown format includes tables and structure)
        text_content = result.content if hasattr(result, 'content') else ""
        
        return {
            "file_id": file_id,
            "session_id": session_id,
            "file_type": "pdf",
            "text_content": text_content,
            "document_structure": {
                "page_count": len(result.pages) if hasattr(result, 'pages') and result.pages else 0,
                "languages": [lang.locale for lang in result.languages] if hasattr(result, 'languages') and result.languages else [],
                "character_count": len(text_content)
            },
            "extraction_metadata": {
                "service": "Azure Document Intelligence",
                "model": "prebuilt-layout",
                "output_format": "markdown",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        }
    
    def _save_extracted_content(
        self,
        content: Dict[str, Any],
        session_id: str,
        file_id: str
    ):
        """Save extracted content to JSON file."""
        session_dir = self.data_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = session_dir / f"{file_id}_extracted.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved extracted content", output_path=str(output_path))
    
    def get_extracted_content(
        self,
        session_id: str,
        file_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve previously extracted content."""
        content_path = self.data_dir / session_id / f"{file_id}_extracted.json"
        
        if content_path.exists():
            with open(content_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for the planner."""
        return {
            "agent_name": self.name,
            "description": self.description,
            "capabilities": [
                "transcribe_audio",
                "process_video",
                "extract_pdf_content",
                "extract_metadata"
            ],
            "supported_file_types": ["audio", "video", "pdf"],
            "azure_services": ["Speech-to-Text", "Document Intelligence"]
        }
