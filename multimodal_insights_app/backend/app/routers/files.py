"""
Files Router - Multimodal Insights Application

REST API endpoints for file upload and management.
Built from scratch for multimodal content processing.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status, Request
from fastapi.responses import FileResponse
from typing import List, Optional
import structlog

from ..models.task_models import FileMetadata, FileUploadResponse
from ..services.file_handler import FileHandler
from ..persistence.cosmos_memory import CosmosMemoryStore
from ..infra.settings import Settings
from ..auth.auth_utils import get_authenticated_user_details

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])

# Dependency to get file handler instance
_file_handler: Optional[FileHandler] = None
_memory_store: Optional[CosmosMemoryStore] = None


def set_file_handler(file_handler: FileHandler, memory_store: CosmosMemoryStore):
    """Set the file handler instance (called from main.py)."""
    global _file_handler, _memory_store
    _file_handler = file_handler
    _memory_store = memory_store


def get_file_handler() -> FileHandler:
    """Dependency to get file handler instance."""
    if _file_handler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File handler not initialized"
        )
    return _file_handler


def get_memory_store() -> CosmosMemoryStore:
    """Dependency to get memory store instance."""
    if _memory_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory store not initialized"
        )
    return _memory_store


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    session_id: str = Form(...),
    file_handler: FileHandler = Depends(get_file_handler),
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """
    Upload one or more files (audio, video, or PDF).
    
    Supported formats:
    - Audio: .mp3, .wav, .m4a, .flac, .ogg
    - Video: .mp4, .avi, .mov, .mkv, .wmv
    - PDF: .pdf
    
    Args:
        request: FastAPI request (for extracting user from headers)
        files: List of files to upload
        session_id: Session ID for organizing files
    
    Returns:
        Action response with file metadata
    """
    # Extract user details from Azure EasyAuth headers (or local dev mock)
    user_details = get_authenticated_user_details(request.headers)
    user_id = user_details.get("user_principal_id", "unknown-user")
    
    logger.info(
        "Uploading files via API",
        file_count=len(files),
        session_id=session_id,
        user_id=user_id,
        user_name=user_details.get("user_name", "unknown")
    )
    
    try:
        # Validate file count
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        if len(files) > 10:  # Reasonable limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 files per upload"
            )
        
        # Ensure session exists in Cosmos DB
        existing_session = await memory_store.get_session(session_id)
        if not existing_session:
            from ..models.task_models import Session as SessionModel
            new_session = SessionModel(
                session_id=session_id,
                user_id=user_id
            )
            await memory_store.create_session(new_session)
            logger.info("Created new session in Cosmos DB", session_id=session_id)
        
        # Process uploads
        file_metadata_list = []
        
        for upload_file in files:
            # Validate file type
            if not upload_file.filename:
                continue
            
            file_ext = upload_file.filename.lower().split('.')[-1]
            supported_extensions = [
                'mp3', 'wav', 'm4a', 'flac', 'ogg',  # Audio
                'mp4', 'avi', 'mov', 'mkv', 'wmv',  # Video
                'pdf'  # PDF
            ]
            
            if file_ext not in supported_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_ext}. Supported: {', '.join(supported_extensions)}"
                )
            
            # Generate unique file ID
            import uuid
            file_id = str(uuid.uuid4())
            
            # Save file to local storage
            file_metadata = await file_handler.save_upload(
                upload_file,
                session_id,
                file_id
            )
            
            # Set user_id on metadata
            file_metadata.user_id = user_id
            
            # Save metadata to Cosmos DB
            await memory_store.create_file_metadata(file_metadata)
            
            logger.info(
                "File metadata saved to Cosmos",
                file_id=file_metadata.id,
                session_id=session_id
            )
            
            file_metadata_list.append(file_metadata)
        
        logger.info(
            "Files uploaded successfully",
            file_count=len(file_metadata_list),
            session_id=session_id
        )
        
        return FileUploadResponse(
            status="success",
            message=f"Successfully uploaded {len(file_metadata_list)} file(s)",
            data={
                "session_id": session_id,
                "files": [
                    {
                        "id": fm.id,
                        "filename": fm.filename,
                        "file_type": fm.file_type.value,
                        "file_size": fm.file_size
                    }
                    for fm in file_metadata_list
                ]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload files", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=List[FileMetadata])
async def list_session_files(
    session_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """
    List all files for a session.
    
    Args:
        session_id: Session ID
    
    Returns:
        List of file metadata
    """
    logger.info("Listing session files via API", session_id=session_id)
    
    try:
        files = await memory_store.get_files_for_session(session_id)
        
        logger.info(
            "Session files retrieved",
            session_id=session_id,
            file_count=len(files)
        )
        
        return files
        
    except Exception as e:
        logger.error(f"Failed to list session files", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileMetadata)
async def get_file_metadata(
    file_id: str,
    session_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """
    Get metadata for a specific file.
    
    Args:
        file_id: File ID
        session_id: Session ID
    
    Returns:
        File metadata
    """
    logger.info("Getting file metadata via API", file_id=file_id)
    
    try:
        file_metadata = await memory_store.get_file_metadata(file_id, session_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found"
            )
        
        return file_metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file metadata", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file metadata: {str(e)}"
        )


@router.delete("/{file_id}", response_model=FileUploadResponse)
async def delete_file(
    file_id: str,
    session_id: str,
    file_handler: FileHandler = Depends(get_file_handler),
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """
    Delete a file and its metadata.
    
    Args:
        file_id: File ID
        session_id: Session ID
    
    Returns:
        Action response with deletion confirmation
    """
    logger.info("Deleting file via API", file_id=file_id)
    
    try:
        # Get file metadata
        file_metadata = await memory_store.get_file_metadata(file_id, session_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found"
            )
        
        # Delete physical file
        import os
        if os.path.exists(file_metadata.file_path):
            os.remove(file_metadata.file_path)
        
        # Delete extracted content if exists
        if file_metadata.extracted_content_path and os.path.exists(file_metadata.extracted_content_path):
            os.remove(file_metadata.extracted_content_path)
        
        # Note: We don't delete from Cosmos DB as it maintains history
        # But we could mark it as deleted
        file_metadata.processing_status = "deleted"
        await memory_store.update_file_metadata(file_metadata)
        
        logger.info("File deleted successfully", file_id=file_id)
        
        return FileUploadResponse(
            status="success",
            message=f"File {file_metadata.filename} deleted successfully",
            data={"file_id": file_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    session_id: str,
    memory_store: CosmosMemoryStore = Depends(get_memory_store)
):
    """
    Download original uploaded file.
    
    Args:
        file_id: File ID
        session_id: Session ID
    
    Returns:
        File download response
    """
    logger.info("Downloading file via API", file_id=file_id)
    
    try:
        # Get file metadata
        file_metadata = await memory_store.get_file_metadata(file_id, session_id)
        
        if not file_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found"
            )
        
        # Check if file exists
        import os
        if not os.path.exists(file_metadata.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Physical file not found"
            )
        
        # Return file
        return FileResponse(
            path=file_metadata.file_path,
            filename=file_metadata.filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )
