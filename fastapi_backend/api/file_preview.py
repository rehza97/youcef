from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.file_upload import FilePreviewResponse, FilePreviewRequest, FilePreviewListResponse
from services.file_service import FileService
import logging

logger = logging.getLogger('file_preview')

file_preview_router = APIRouter()
file_service = FileService()


@file_preview_router.get("/{file_id}/preview")
async def get_or_generate_file_preview(
    file_id: int,
    max_rows: int = Query(50, description="Maximum number of rows to preview"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file preview - generates one if none exists"""
    try:
        # Get file upload record
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)

        # Check if previews already exist
        existing_previews = file_service.get_file_previews(
            db, file_id, current_user.id)

        if existing_previews:
            logger.info(f"Returning existing previews for file {file_id}")
            return FilePreviewListResponse(
                data=existing_previews,
                total=len(existing_previews)
            )

        # No previews exist, generate one
        logger.info(
            f"Generating new preview for file {file_id} with {max_rows} rows")

        # Create preview request
        class PreviewRequest:
            def __init__(self, max_rows):
                self.max_rows = max_rows

        preview_request = PreviewRequest(max_rows)

        # Generate preview
        previews = await file_service.generate_file_preview(
            db, file_upload, preview_request, current_user.id
        )

        logger.info(f"Generated {len(previews)} previews for file {file_id}")
        return FilePreviewListResponse(
            data=previews,
            total=len(previews)
        )

    except Exception as e:
        logger.error(
            f"Failed to get/generate preview for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get preview: {str(e)}"
        )


@file_preview_router.get("/{file_id}/previews", response_model=FilePreviewListResponse)
async def get_file_previews(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file previews"""
    try:
        file_service.get_file_upload(
            db, file_id, current_user.id)  # Check access
        previews = file_service.get_file_previews(db, file_id, current_user.id)
        logger.info(
            f"Previews for file {file_id} retrieved by user {current_user.id}")
        return FilePreviewListResponse(
            data=previews,
            total=len(previews)
        )
    except HTTPException as e:
        if e.status_code == 404:
            # File not found - return empty array instead of error
            logger.info(
                f"File {file_id} not found, returning empty previews array")
            return FilePreviewListResponse(data=[], total=0)
        raise e


@file_preview_router.post("/{file_id}/preview", response_model=FilePreviewListResponse)
async def generate_file_preview(
    file_id: int,
    preview_request: FilePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate new preview for file"""
    file_upload = file_service.get_file_upload(db, file_id, current_user.id)

    try:
        previews = await file_service.generate_file_preview(
            db, file_upload, preview_request, current_user.id
        )

        logger.info(
            f"Preview generated for file {file_id} by user {current_user.id}")
        return FilePreviewListResponse(
            data=previews,
            total=len(previews)
        )

    except Exception as e:
        logger.error(f"Preview generation failed for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Preview generation failed: {str(e)}"
        )


@file_preview_router.delete("/{file_id}/previews/{preview_id}")
async def delete_file_preview(
    file_id: int,
    preview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file preview"""
    file_service.get_file_upload(db, file_id, current_user.id)  # Check access

    try:
        file_service.delete_file_preview(db, preview_id, current_user.id)
        logger.info(f"Preview {preview_id} deleted by user {current_user.id}")
        return {"message": "Preview deleted successfully"}

    except Exception as e:
        logger.error(f"Preview deletion failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting preview: {str(e)}"
        )


@file_preview_router.get("/{file_id}/previews/{preview_id}/data")
async def get_preview_data(
    file_id: int,
    preview_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get preview data content with pagination"""
    file_service.get_file_upload(db, file_id, current_user.id)  # Check access

    try:
        preview_data = file_service.get_preview_data(
            db, preview_id, current_user.id, page=page, per_page=per_page)
        logger.info(
            f"Preview data for {preview_id} retrieved by user {current_user.id} (page {page}, {per_page} items)")
        return preview_data

    except Exception as e:
        logger.error(f"Failed to get preview data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving preview data: {str(e)}"
        )


@file_preview_router.get("/{file_id}/preview/data")
async def get_file_preview_data(
    file_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file preview data with pagination - generates preview if needed"""
    try:
        # Get file upload record
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)

        # Check if previews exist
        existing_previews = file_service.get_file_previews(
            db, file_id, current_user.id)

        if not existing_previews:
            # Generate preview first
            logger.info(f"Generating preview for file {file_id}")

            class PreviewRequest:
                def __init__(self, max_rows):
                    self.max_rows = max_rows

            preview_request = PreviewRequest(100)  # Generate with more rows
            await file_service.generate_file_preview(
                db, file_upload, preview_request, current_user.id
            )
            existing_previews = file_service.get_file_previews(
                db, file_id, current_user.id)

        if not existing_previews:
            raise HTTPException(
                status_code=404, detail="No preview data available")

        # Get the first preview's data
        preview_id = existing_previews[0].id
        preview_data = file_service.get_preview_data(
            db, preview_id, current_user.id, page=page, per_page=per_page
        )

        logger.info(
            f"Preview data for file {file_id} retrieved (page {page}, {per_page} items)")
        return preview_data

    except Exception as e:
        logger.error(
            f"Failed to get preview data for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get preview data: {str(e)}"
        )
