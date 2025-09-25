from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.role import Role, UserRole
from models.file_upload import (
    FileUploadWithPreviews, FileListResponse, FileUploadUpdate
)
from services.file_service import FileService
import logging

# Configure detailed logging
logger = logging.getLogger('file_management')

file_management_router = APIRouter()
file_service = FileService()


def check_admin_or_owner(current_user: User, db: Session, file_upload_user_id: int = None):
    """Helper function to check if user is admin or file owner using permission service"""
    from services.permission_service import PermissionService

    is_admin = PermissionService.is_admin(current_user, db)
    is_owner = file_upload_user_id == current_user.id if file_upload_user_id else False

    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Admin access required or must be file owner"
        )

    return is_admin


@file_management_router.get("/", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List files with pagination and filtering"""
    logger.info(f"File list request from user {current_user.id}")

    files_data = file_service.get_files_paginated(
        db, current_user.id, page, page_size, search, file_type
    )

    return files_data


@file_management_router.get("/{file_id}", response_model=FileUploadWithPreviews)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file details with previews"""
    try:
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)

        # Get file with all previews
        file_with_previews = file_service.get_file_with_previews(
            db, file_id, current_user.id
        )

        logger.info(f"File {file_id} retrieved by user {current_user.id}")
        return file_with_previews
    except HTTPException as e:
        if e.status_code == 404:
            # File not found - return appropriate error
            logger.info(f"File {file_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="File not found")
        raise e


@file_management_router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the original file"""
    try:
        # Get file upload record
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)

        # Check if user is admin or file owner
        check_admin_or_owner(current_user, db, file_upload.uploaded_by)

        # Check if file exists on disk
        if not os.path.exists(file_upload.file_path):
            logger.error(f"Physical file not found: {file_upload.file_path}")
            raise HTTPException(
                status_code=404,
                detail="Physical file not found on server"
            )

        logger.info(f"File {file_id} downloaded by user {current_user.id}")

        # Return file with original filename and MIME type
        return FileResponse(
            path=file_upload.file_path,
            filename=file_upload.original_filename,
            media_type=file_upload.mime_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading file: {str(e)}"
        )


@file_management_router.put("/{file_id}", response_model=FileUploadWithPreviews)
async def update_file(
    file_id: int,
    file_update: FileUploadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update file metadata (Admin only or owner)"""
    file_upload = file_service.get_file_upload(db, file_id, current_user.id)
    check_admin_or_owner(current_user, db, file_upload.uploaded_by)

    # Update file fields
    update_data = file_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(file_upload, field, value)

    try:
        db.commit()
        db.refresh(file_upload)
        logger.info(f"File {file_id} updated by user {current_user.id}")
        return file_upload
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating file: {str(e)}"
        )


@file_management_router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete uploaded file (Admin only or owner)"""
    try:
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)
        check_admin_or_owner(current_user, db, file_upload.uploaded_by)

        file_service.delete_file(db, file_id, current_user.id)
        logger.info(f"File {file_id} deleted by user {current_user.id}")
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}"
        )


@file_management_router.get("/user/{user_id}", response_model=FileListResponse)
async def get_user_files(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get files uploaded by specific user (Admin only)"""
    # RBAC: Only ADMIN can view other users' files
    from services.permission_service import PermissionService
    PermissionService.check_admin_permissions(current_user, db)

    files_data = file_service.get_files_by_user(
        db, user_id, page, page_size
    )

    logger.info(
        f"Files for user {user_id} retrieved by admin {current_user.id}")
    return files_data


@file_management_router.get("/stats/summary")
async def get_files_stats_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file statistics summary"""
    from sqlalchemy import func
    from models.file_upload import FileUpload

    # Get total files count
    total_files = db.query(FileUpload).count()

    # Get files by type
    files_by_type = db.query(
        FileUpload.file_type,
        func.count(FileUpload.id).label('count')
    ).group_by(FileUpload.file_type).all()

    # Get files by status
    files_by_status = db.query(
        FileUpload.processing_status,
        func.count(FileUpload.id).label('count')
    ).group_by(FileUpload.processing_status).all()

    # Get total file size
    total_size = db.query(func.sum(FileUpload.file_size)).scalar() or 0

    # Get recent uploads (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_uploads = db.query(FileUpload).filter(
        FileUpload.created_at >= week_ago
    ).count()

    stats = {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "recent_uploads_7_days": recent_uploads,
        "files_by_type": {item.file_type: item.count for item in files_by_type},
        "files_by_status": {item.processing_status: item.count for item in files_by_status}
    }

    logger.info(f"File stats summary requested by user {current_user.id}")
    return stats
