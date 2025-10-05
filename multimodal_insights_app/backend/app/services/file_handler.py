"""
File Handler Service

Manages file uploads, storage, and processing coordination.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles
import structlog
from fastapi import UploadFile
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import ClientSecretCredential

from ..models.task_models import FileMetadata, FileType, ProcessingStatus
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)


class FileHandler:
    """
    Service for handling multimodal file operations.
    
    Responsibilities:
    - File upload to Azure Blob Storage
    - File type detection
    - File validation
    - Storage management
    """
    
    def __init__(self, settings: Settings):
        """Initialize file handler."""
        self.settings = settings
        
        # Azure AD credential
        credential = ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret
        )
        
        # Azure Blob Storage client with Azure AD auth
        storage_account_url = f"https://{settings.azure_blob_storage_name}.blob.core.windows.net"
        self.blob_service_client = BlobServiceClient(
            account_url=storage_account_url,
            credential=credential
        )
        self.container_name = settings.azure_storage_container
        
        # Create directories for local temp storage
        self.upload_dir = Path(settings.upload_directory)
        self.data_dir = Path(settings.data_directory)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File extension mappings
        self.audio_extensions = set(settings.allowed_audio_extensions)
        self.video_extensions = set(settings.allowed_video_extensions)
        self.pdf_extensions = set(settings.allowed_pdf_extensions)
        
        logger.info("File handler initialized with Azure Blob Storage")
    
    async def initialize(self):
        """Initialize file handler resources and ensure container exists."""
        # Ensure blob container exists
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not await container_client.exists():
                await container_client.create_container()
                logger.info(f"Created blob container: {self.container_name}")
            else:
                logger.info(f"Using existing blob container: {self.container_name}")
        except Exception as e:
            logger.error(f"Failed to initialize blob container", error=str(e))
            raise
        logger.info("File handler ready")
    
    async def shutdown(self):
        """Cleanup file handler resources."""
        logger.info("File handler shutdown")
    
    async def save_upload(
        self,
        file: UploadFile,
        session_id: str,
        file_id: str
    ) -> FileMetadata:
        """
        Save uploaded file to Azure Blob Storage and create metadata.
        
        Args:
            file: Uploaded file
            session_id: Session identifier
            file_id: File identifier
            
        Returns:
            FileMetadata object
        """
        logger.info(f"Uploading file to Azure Blob Storage", filename=file.filename, session_id=session_id)
        
        try:
            # Validate file size
            file_size = 0
            content = await file.read()
            file_size = len(content)
            
            if file_size > self.settings.max_upload_size:
                raise ValueError(f"File size {file_size} exceeds maximum {self.settings.max_upload_size}")
            
            # Determine file type
            file_type = self._detect_file_type(file.filename)
            
            # Create blob name: session_id/file_id.extension
            file_extension = Path(file.filename).suffix
            blob_name = f"{session_id}/{file_id}{file_extension}"
            
            # Upload to Azure Blob Storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            await blob_client.upload_blob(content, overwrite=True)
            
            # Get blob URL
            blob_url = blob_client.url
            
            logger.info(
                "File uploaded to blob storage",
                file_id=file_id,
                blob_name=blob_name,
                blob_url=blob_url
            )
            
            # Create metadata
            metadata = FileMetadata(
                id=file_id,
                session_id=session_id,
                user_id="",  # Will be set by caller
                filename=file.filename,
                file_type=file_type,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                file_path=blob_url,  # Store blob URL as file_path
                processing_status=ProcessingStatus.PENDING
            )
            
            logger.info(
                "File saved successfully to Azure Blob Storage",
                file_id=file_id,
                blob_url=blob_url,
                file_type=file_type
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to upload file to blob storage", error=str(e), filename=file.filename)
            raise
    
    def _detect_file_type(self, filename: str) -> FileType:
        """Detect file type from filename extension."""
        extension = Path(filename).suffix.lower()
        
        if extension in self.audio_extensions:
            return FileType.AUDIO
        elif extension in self.video_extensions:
            return FileType.VIDEO
        elif extension in self.pdf_extensions:
            return FileType.PDF
        else:
            return FileType.UNKNOWN
    
    def get_file_path(self, session_id: str, file_id: str, extension: str) -> Path:
        """Get path for a file."""
        return self.upload_dir / session_id / f"{file_id}{extension}"
    
    def get_session_files(self, session_id: str) -> List[str]:
        """Get list of files in a session."""
        session_dir = self.upload_dir / session_id
        if not session_dir.exists():
            return []
        
        return [f.name for f in session_dir.iterdir() if f.is_file()]
    
    async def delete_file(self, session_id: str, file_id: str):
        """Delete a file."""
        session_dir = self.upload_dir / session_id
        if session_dir.exists():
            for file in session_dir.glob(f"{file_id}.*"):
                file.unlink()
                logger.info(f"Deleted file", file_path=str(file))
    
    async def delete_session_files(self, session_id: str):
        """Delete all files in a session."""
        session_dir = self.upload_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.info(f"Deleted session files", session_id=session_id)
    
    def validate_file_type(self, filename: str) -> bool:
        """Validate if file type is supported."""
        file_type = self._detect_file_type(filename)
        return file_type != FileType.UNKNOWN
    
    def get_extracted_content_path(self, session_id: str, file_id: str) -> Path:
        """Get path to extracted content JSON."""
        return self.data_dir / session_id / f"{file_id}_extracted.json"
