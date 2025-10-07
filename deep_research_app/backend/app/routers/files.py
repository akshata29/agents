"""
Files Router - Deep Research Application

REST API endpoints for document upload, processing, and management.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from typing import List, Optional
import structlog
import uuid

from ..models.file_models import FileMetadata, FileUploadResponse
from ..services.file_handler import FileHandler
from ..services.document_intelligence_service import DocumentIntelligenceService
from ..models.file_models import ProcessingStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

# Dependency to get service instances
_file_handler: Optional[FileHandler] = None
_doc_intelligence: Optional[DocumentIntelligenceService] = None


def set_services(
    file_handler: FileHandler,
    doc_intelligence: DocumentIntelligenceService
):
    """Set the service instances (called from main.py)."""
    global _file_handler, _doc_intelligence
    _file_handler = file_handler
    _doc_intelligence = doc_intelligence


def get_file_handler() -> FileHandler:
    """Dependency to get file handler instance."""
    if _file_handler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File handler not initialized"
        )
    return _file_handler


def get_doc_intelligence() -> DocumentIntelligenceService:
    """Dependency to get document intelligence instance."""
    if _doc_intelligence is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document intelligence service not initialized"
        )
    return _doc_intelligence


async def process_document_background(
    file_id: str,
    file_handler: FileHandler,
    doc_intelligence: DocumentIntelligenceService
):
    """Background task to process uploaded document."""
    try:
        logger.info("Starting background document processing", file_id=file_id)
        
        # Get file metadata
        metadata = await file_handler.get_metadata(file_id)
        if not metadata:
            logger.error("File metadata not found", file_id=file_id)
            return
        
        # Update status to processing
        metadata.processing_status = ProcessingStatus.PROCESSING
        await file_handler.update_metadata(metadata)
        
        # Process document
        result = await doc_intelligence.process_document(metadata)
        
        # Save markdown content
        await file_handler.save_markdown_content(
            file_id=file_id,
            markdown_content=result["markdown_content"],
            metadata_updates=result["metadata"]
        )
        
        logger.info("Document processing completed", file_id=file_id)
        
    except Exception as e:
        logger.error("Document processing failed", error=str(e), file_id=file_id)
        
        # Update metadata with error
        metadata = await file_handler.get_metadata(file_id)
        if metadata:
            metadata.processing_status = ProcessingStatus.FAILED
            metadata.error_message = str(e)
            await file_handler.update_metadata(metadata)


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    session_id: str = Form(...),
    user_id: str = Form(default="")
):
    """
    Upload one or more documents (PDF, DOCX, TXT) for research.
    
    Supported formats:
    - PDF: .pdf
    - Word: .docx, .doc
    - Text: .txt, .md
    
    Args:
        background_tasks: FastAPI background tasks
        files: List of files to upload
        session_id: Session ID for organizing files
        user_id: User identifier
    
    Returns:
        FileUploadResponse with file metadata
    """
    file_handler = get_file_handler()
    doc_intelligence = get_doc_intelligence()
    
    logger.info(
        "Uploading files",
        file_count=len(files),
        session_id=session_id,
        user_id=user_id
    )
    
    try:
        # Validate file count
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        if len(files) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 files allowed per upload"
            )
        
        uploaded_files = []
        
        for file in files:
            # Generate unique file ID
            file_id = f"doc-{uuid.uuid4()}"
            
            # Save file to blob storage
            metadata = await file_handler.save_upload(
                file=file,
                session_id=session_id,
                file_id=file_id,
                user_id=user_id
            )
            
            uploaded_files.append(metadata)
            
            # Queue document processing in background
            background_tasks.add_task(
                process_document_background,
                file_id,
                file_handler,
                doc_intelligence
            )
        
        logger.info(
            "Files uploaded successfully",
            file_count=len(uploaded_files),
            session_id=session_id
        )
        
        return FileUploadResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_files)} file(s). Processing in background.",
            files=uploaded_files
        )
        
    except ValueError as e:
        logger.error("File validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("File upload failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/documents", response_model=List[FileMetadata])
async def list_documents(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    List all processed documents, optionally filtered by user or session.
    
    Args:
        user_id: Filter by user ID
        session_id: Filter by session ID
    
    Returns:
        List of FileMetadata for successfully processed documents
    """
    file_handler = get_file_handler()
    
    try:
        documents = await file_handler.list_documents(
            user_id=user_id,
            session_id=session_id
        )
        
        logger.info(
            "Retrieved documents",
            count=len(documents),
            user_id=user_id,
            session_id=session_id
        )
        
        return documents
        
    except Exception as e:
        logger.error("Failed to list documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/documents/{file_id}", response_model=FileMetadata)
async def get_document(file_id: str):
    """
    Get metadata for a specific document.
    
    Args:
        file_id: File identifier
    
    Returns:
        FileMetadata
    """
    file_handler = get_file_handler()
    
    try:
        metadata = await file_handler.get_metadata(file_id)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {file_id}"
            )
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document", error=str(e), file_id=file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )


@router.get("/documents/{file_id}/content")
async def get_document_content(file_id: str):
    """
    Get processed markdown content for a document.
    
    Args:
        file_id: File identifier
    
    Returns:
        Markdown content as plain text
    """
    file_handler = get_file_handler()
    
    try:
        content = await file_handler.get_document_content(file_id)
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document content not found or not yet processed: {file_id}"
            )
        
        return {"file_id": file_id, "content": content}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document content", error=str(e), file_id=file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document content: {str(e)}"
        )
