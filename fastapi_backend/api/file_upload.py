from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.role import Role, UserRole
from models.file_upload import FileUploadResponse
from services.file_service import FileService
from services.notification_service import NotificationService
import logging

# Configure detailed logging for file uploads
file_logger = logging.getLogger('file_upload')
file_logger.setLevel(logging.DEBUG)

file_upload_router = APIRouter()
file_service = FileService()


def check_upload_access(current_user: User, db: Session):
    """Helper function to check upload access using permission service"""
    from services.permission_service import PermissionService
    PermissionService.require_permission(current_user, db, "can_upload_files")


@file_upload_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file (Requires can_upload_files permission)"""
    check_upload_access(current_user, db)
    file_logger.info(
        f"File upload request received from user {current_user.id}")

    try:
        # Upload file
        uploaded_file = await file_service.save_uploaded_file(
            db, file, current_user.id
        )
        file_logger.info(f"File uploaded successfully: {uploaded_file.id}")

        # Send notification
        await NotificationService.send_notification(
            db,
            user_id=current_user.id,
            title="File Upload",
            message=f"File '{file.filename}' uploaded successfully",
            notification_type="file_upload",
            data={"file_id": uploaded_file.id}
        )

        return uploaded_file

    except Exception as e:
        file_logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )


@file_upload_router.post("/upload-batch", response_model=List[FileUploadResponse])
async def upload_batch_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload multiple files (Requires can_upload_files permission)"""
    check_upload_access(current_user, db)

    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files allowed per batch upload"
        )

    uploaded_files = []
    failed_uploads = []

    for file in files:
        try:
            uploaded_file = await file_service.save_uploaded_file(
                db, file, current_user.id
            )
            uploaded_files.append(uploaded_file)
            file_logger.info(f"File uploaded successfully: {uploaded_file.id}")

        except Exception as e:
            file_logger.error(f"Failed to upload {file.filename}: {str(e)}")
            failed_uploads.append({"filename": file.filename, "error": str(e)})

    # Send notification for batch upload
    await NotificationService.send_notification(
        db,
        user_id=current_user.id,
        title="Batch File Upload",
        message=f"Uploaded {len(uploaded_files)} files successfully. {len(failed_uploads)} failed.",
        notification_type="batch_upload",
        data={
            "successful_uploads": len(uploaded_files),
            "failed_uploads": len(failed_uploads),
            "failures": failed_uploads
        }
    )

    if failed_uploads:
        file_logger.warning(f"Some files failed to upload: {failed_uploads}")

    return uploaded_files
