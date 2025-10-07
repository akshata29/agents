"""
File Handler Service for Deep Research Application

Manages file uploads, storage, and retrieval from Azure Blob Storage.
Adapted from multimodal_insights_app with research-specific optimizations.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles
import structlog
from fastapi import UploadFile
from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import ClientSecretCredential
from datetime import datetime

from ..models.file_models import FileMetadata, FileType, ProcessingStatus

logger = structlog.get_logger(__name__)


class FileHandler:
    """
    Service for handling document operations in deep research.
    
    Responsibilities:
    - File upload to Azure Blob Storage
    - File type detection and validation
    - Storage management
    - Document retrieval
    """
    
    def __init__(
        self,
        azure_tenant_id: str,
        azure_client_id: str,
        azure_client_secret: str,
        azure_blob_storage_name: str,
        azure_storage_container: str = "research-documents",
        upload_directory: str = "uploads",
        data_directory: str = "data"
    ):
        """Initialize file handler."""
        # Azure AD credential
        self.credential = ClientSecretCredential(
            tenant_id=azure_tenant_id,
            client_id=azure_client_id,
            client_secret=azure_client_secret
        )
        
        # Azure Blob Storage client with Azure AD auth
        storage_account_url = f"https://{azure_blob_storage_name}.blob.core.windows.net"
        self.blob_service_client = BlobServiceClient(
            account_url=storage_account_url,
            credential=self.credential
        )
        self.container_name = azure_storage_container
        self.storage_name = azure_blob_storage_name
        
        # Create directories for local temp storage
        self.upload_dir = Path(upload_directory)
        self.data_dir = Path(data_directory)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File extension mappings
        self.pdf_extensions = {".pdf"}
        self.docx_extensions = {".docx", ".doc"}
        self.txt_extensions = {".txt", ".text", ".md"}
        
        # Max file size (50 MB)
        self.max_upload_size = 50 * 1024 * 1024
        
        logger.info("File handler initialized", container=self.container_name)
    
    async def initialize(self):
        """Initialize file handler resources and ensure container exists."""
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
        await self.credential.close()
        await self.blob_service_client.close()
        logger.info("File handler shutdown")
    
    def _detect_file_type(self, filename: str) -> FileType:
        """
        Detect file type from filename extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            FileType enum value
            
        Raises:
            ValueError: If file type is not supported
        """
        ext = Path(filename).suffix.lower()
        
        if ext in self.pdf_extensions:
            return FileType.PDF
        elif ext in self.docx_extensions:
            return FileType.DOCX
        elif ext in self.txt_extensions:
            return FileType.TXT
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def save_upload(
        self,
        file: UploadFile,
        session_id: str,
        file_id: str,
        user_id: str = ""
    ) -> FileMetadata:
        """
        Save uploaded file to Azure Blob Storage and create metadata.
        
        Args:
            file: Uploaded file
            session_id: Session identifier
            file_id: File identifier
            user_id: User identifier
            
        Returns:
            FileMetadata object
        """
        logger.info(
            "Uploading file to Azure Blob Storage",
            filename=file.filename,
            session_id=session_id
        )
        
        try:
            # Read and validate file
            content = await file.read()
            file_size = len(content)
            
            if file_size > self.max_upload_size:
                raise ValueError(
                    f"File size {file_size} exceeds maximum {self.max_upload_size}"
                )
            
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
                blob_name=blob_name
            )
            
            # Create metadata
            metadata = FileMetadata(
                id=file_id,
                session_id=session_id,
                user_id=user_id,
                filename=file.filename,
                file_type=file_type,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                file_path=blob_url,
                processing_status=ProcessingStatus.PENDING
            )
            
            # Save metadata to local storage
            await self._save_metadata(metadata)
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to upload file", error=str(e), filename=file.filename)
            raise
    
    async def _save_metadata(self, metadata: FileMetadata):
        """Save file metadata to local JSON storage."""
        metadata_dir = self.data_dir / "file_metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_file = metadata_dir / f"{metadata.id}.json"
        
        async with aiofiles.open(metadata_file, "w") as f:
            await f.write(metadata.model_dump_json(indent=2))
        
        logger.debug("Saved file metadata", file_id=metadata.id)
    
    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """
        Retrieve file metadata by ID.
        
        Args:
            file_id: File identifier
            
        Returns:
            FileMetadata or None if not found
        """
        metadata_file = self.data_dir / "file_metadata" / f"{file_id}.json"
        
        if not metadata_file.exists():
            return None
        
        async with aiofiles.open(metadata_file, "r") as f:
            content = await f.read()
            return FileMetadata.model_validate_json(content)
    
    async def update_metadata(self, metadata: FileMetadata):
        """Update file metadata."""
        await self._save_metadata(metadata)
    
    async def list_documents(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[FileMetadata]:
        """
        List all processed documents, optionally filtered by user or session.
        
        Args:
            user_id: Filter by user ID
            session_id: Filter by session ID
            
        Returns:
            List of FileMetadata objects
        """
        metadata_dir = self.data_dir / "file_metadata"
        
        if not metadata_dir.exists():
            return []
        
        documents = []
        
        for metadata_file in metadata_dir.glob("*.json"):
            async with aiofiles.open(metadata_file, "r") as f:
                content = await f.read()
                metadata = FileMetadata.model_validate_json(content)
                
                # Apply filters
                if user_id and metadata.user_id != user_id:
                    continue
                if session_id and metadata.session_id != session_id:
                    continue
                
                # Only return successfully processed documents
                if metadata.processing_status == ProcessingStatus.COMPLETED:
                    documents.append(metadata)
        
        # Sort by upload timestamp (newest first)
        documents.sort(key=lambda x: x.upload_timestamp, reverse=True)
        
        return documents
    
    async def get_document_content(self, file_id: str) -> Optional[str]:
        """
        Retrieve processed markdown content for a document.
        
        Args:
            file_id: File identifier
            
        Returns:
            Markdown content or None if not found
        """
        metadata = await self.get_metadata(file_id)
        
        if not metadata or not metadata.markdown_path:
            return None
        
        markdown_file = self.data_dir / metadata.markdown_path
        
        if not markdown_file.exists():
            return None
        
        async with aiofiles.open(markdown_file, "r", encoding="utf-8") as f:
            return await f.read()
    
    async def save_markdown_content(
        self,
        file_id: str,
        markdown_content: str,
        metadata_updates: Optional[Dict[str, Any]] = None
    ):
        """
        Save extracted markdown content for a document.
        
        Args:
            file_id: File identifier
            markdown_content: Extracted markdown content
            metadata_updates: Optional metadata updates (page count, etc.)
        """
        # Get existing metadata
        metadata = await self.get_metadata(file_id)
        if not metadata:
            raise ValueError(f"File metadata not found: {file_id}")
        
        # Save markdown content
        markdown_dir = self.data_dir / "markdown" / metadata.session_id
        markdown_dir.mkdir(parents=True, exist_ok=True)
        
        markdown_file = markdown_dir / f"{file_id}.md"
        
        async with aiofiles.open(markdown_file, "w", encoding="utf-8") as f:
            await f.write(markdown_content)
        
        # Update metadata
        metadata.markdown_path = f"markdown/{metadata.session_id}/{file_id}.md"
        metadata.processing_status = ProcessingStatus.COMPLETED
        metadata.processed_timestamp = datetime.utcnow()
        
        if metadata_updates:
            metadata.metadata.update(metadata_updates)
        
        await self.update_metadata(metadata)
        
        logger.info("Saved markdown content", file_id=file_id)
