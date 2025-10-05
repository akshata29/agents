"""
Export Router - Multimodal Insights Application

REST API endpoints for exporting analysis results.
Built from scratch for multimodal content processing.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import structlog

from ..models.task_models import ActionResponse
from ..services.export_service import ExportService
from ..infra.settings import Settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])

# Dependency to get export service instance
_export_service: Optional[ExportService] = None


def set_export_service(export_service: ExportService):
    """Set the export service instance (called from main.py)."""
    global _export_service
    _export_service = export_service


def get_export_service() -> ExportService:
    """Dependency to get export service instance."""
    if _export_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Export service not initialized"
        )
    return _export_service


@router.post("/plans/{plan_id}", response_model=ActionResponse)
async def export_plan_results(
    plan_id: str,
    session_id: str = Query(..., description="Session ID"),
    export_format: str = Query(
        default="markdown",
        description="Export format (markdown, pdf, json, html)"
    ),
    include_metadata: bool = Query(
        default=True,
        description="Include execution metadata in export"
    ),
    export_service: ExportService = Depends(get_export_service)
):
    """
    Export plan execution results in specified format.
    
    Supported formats:
    - markdown (.md): Clean, readable Markdown document
    - html (.html): Styled HTML page with CSS
    - pdf (.pdf): Professional PDF document
    - json (.json): Structured JSON data
    
    Args:
        plan_id: Plan ID to export
        session_id: Session ID
        export_format: Export format
        include_metadata: Whether to include metadata
    
    Returns:
        Action response with export file information
    """
    logger.info(
        "Exporting plan results via API",
        plan_id=plan_id,
        format=export_format
    )
    
    # Validate format
    valid_formats = ["markdown", "md", "pdf", "json", "html"]
    if export_format.lower() not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export format. Supported: {', '.join(valid_formats)}"
        )
    
    try:
        # Export results
        result = await export_service.export_results(
            plan_id=plan_id,
            session_id=session_id,
            export_format=export_format,
            include_metadata=include_metadata
        )
        
        logger.info(
            "Plan results exported successfully",
            plan_id=plan_id,
            format=result["format"],
            filename=result["filename"]
        )
        
        return ActionResponse(
            status="success",
            message=f"Results exported successfully as {result['format']}",
            data={
                "filename": result["filename"],
                "format": result["format"],
                "size_bytes": result["size_bytes"],
                "download_url": f"/api/export/download/{result['filename']}"
            }
        )
        
    except ValueError as e:
        logger.error(f"Validation error during export", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to export results", error=str(e), plan_id=plan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export results: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_export(
    filename: str,
    export_service: ExportService = Depends(get_export_service)
):
    """
    Download an exported file.
    
    Args:
        filename: Name of the export file
    
    Returns:
        File download response
    """
    logger.info("Downloading export via API", filename=filename)
    
    try:
        # Get file path
        file_path = await export_service.get_export_file(filename)
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export file {filename} not found"
            )
        
        # Determine media type based on extension
        media_types = {
            ".md": "text/markdown",
            ".html": "text/html",
            ".pdf": "application/pdf",
            ".json": "application/json"
        }
        
        extension = file_path.suffix.lower()
        media_type = media_types.get(extension, "application/octet-stream")
        
        # Return file
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_exports(
    session_id: Optional[str] = Query(
        default=None,
        description="Filter by session ID (optional)"
    ),
    export_service: ExportService = Depends(get_export_service)
):
    """
    List all available exports.
    
    Args:
        session_id: Optional session ID filter
    
    Returns:
        List of export file information
    """
    logger.info("Listing exports via API", session_id=session_id)
    
    try:
        exports = await export_service.list_exports(session_id)
        
        logger.info(
            "Exports listed successfully",
            export_count=len(exports)
        )
        
        # Add download URLs
        for export in exports:
            export["download_url"] = f"/api/export/download/{export['filename']}"
        
        return exports
        
    except Exception as e:
        logger.error(f"Failed to list exports", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list exports: {str(e)}"
        )


@router.delete("/{filename}", response_model=ActionResponse)
async def delete_export(
    filename: str,
    export_service: ExportService = Depends(get_export_service)
):
    """
    Delete an export file.
    
    Args:
        filename: Name of the export file to delete
    
    Returns:
        Action response with deletion confirmation
    """
    logger.info("Deleting export via API", filename=filename)
    
    try:
        # Get file path
        file_path = await export_service.get_export_file(filename)
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export file {filename} not found"
            )
        
        # Delete file
        import os
        os.remove(file_path)
        
        logger.info("Export deleted successfully", filename=filename)
        
        return ActionResponse(
            status="success",
            message=f"Export {filename} deleted successfully",
            data={"filename": filename}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete export", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete export: {str(e)}"
        )
