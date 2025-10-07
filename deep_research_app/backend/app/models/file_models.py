"""
File models for document upload and management in Deep Research Application.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported file types for upload."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class ProcessingStatus(str, Enum):
    """Status of file processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileMetadata(BaseModel):
    """Metadata for uploaded research documents."""
    id: str = Field(..., description="Unique file identifier")
    session_id: str = Field(..., description="Session that uploaded the file")
    user_id: str = Field(default="", description="User who uploaded the file")
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    file_path: str = Field(..., description="Azure Blob Storage URL")
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="Current processing status"
    )
    markdown_path: Optional[str] = Field(
        default=None,
        description="Path to extracted markdown content"
    )
    upload_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the file was uploaded"
    )
    processed_timestamp: Optional[datetime] = Field(
        default=None,
        description="When processing completed"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional file metadata (page count, word count, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc-123",
                "session_id": "session-456",
                "user_id": "user-789",
                "filename": "research_paper.pdf",
                "file_type": "pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf",
                "file_path": "https://storage.blob.core.windows.net/docs/research_paper.pdf",
                "processing_status": "completed",
                "markdown_path": "session-456/doc-123.md"
            }
        }


class FileUploadResponse(BaseModel):
    """Response from file upload endpoint."""
    success: bool = Field(..., description="Whether upload was successful")
    message: str = Field(..., description="Status message")
    files: List[FileMetadata] = Field(
        default_factory=list,
        description="Metadata for uploaded files"
    )


class DocumentContent(BaseModel):
    """Extracted content from a processed document."""
    file_id: str = Field(..., description="File identifier")
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Document type")
    markdown_content: str = Field(..., description="Extracted markdown content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata (pages, words, etc.)"
    )
    processed_timestamp: datetime = Field(..., description="Processing timestamp")


class DocumentSource(BaseModel):
    """Source attribution for research content from documents."""
    file_id: str = Field(..., description="File identifier")
    filename: str = Field(..., description="Document filename")
    content_excerpt: str = Field(..., description="Relevant excerpt from document")
    page_number: Optional[int] = Field(
        default=None,
        description="Page number if applicable"
    )
    relevance_score: float = Field(
        default=1.0,
        description="Relevance score for this source"
    )


class ResearchContext(BaseModel):
    """Research context combining web and document sources."""
    query: str = Field(..., description="Research query")
    web_sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Web search results"
    )
    document_sources: List[DocumentSource] = Field(
        default_factory=list,
        description="Document sources"
    )
    combined_context: str = Field(
        default="",
        description="Combined context for research"
    )
