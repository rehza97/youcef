from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.file_upload import (
    FileUploadResponse, FilePreviewResponse, FileUploadWithPreviews,
    FileListResponse, FileProcessingStatus, FilePreviewRequest, FileUpload
)
from services.file_service import FileService

files_router = APIRouter()
file_service = FileService()


@files_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload Excel or CSV file"""
    try:
        # Validate file
        file_service.validate_file(file)

        # Save file
        file_path, filename = file_service.save_file(file, current_user.id)

        # Get file info
        file_size = os.path.getsize(file_path)
        mime_type = file.content_type or "application/octet-stream"
        file_type = file_service.get_file_type(file.filename, mime_type)

        file_info = {
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file_type,
            "mime_type": mime_type
        }

        # Create database record
        file_upload = file_service.create_file_upload_record(
            db, file_info, current_user.id)

        # Process file and create previews
        try:
            file_service.update_processing_status(
                db, file_upload.id, "processing")

            if file_type == "excel":
                previews = file_service.process_excel_file(file_path)
            else:  # csv
                previews = [file_service.process_csv_file(file_path)]

            # Create preview records
            file_service.create_file_preview_records(
                db, file_upload.id, previews)

            # Update status to completed
            file_service.update_processing_status(
                db, file_upload.id, "completed")

        except Exception as e:
            # Update status to failed
            file_service.update_processing_status(
                db, file_upload.id, "failed", str(e))
            raise HTTPException(
                status_code=500, detail=f"Error processing file: {str(e)}")

        return file_upload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error uploading file: {str(e)}")


@files_router.get("/", response_model=FileListResponse)
async def get_user_files(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's uploaded files with pagination"""
    skip = (page - 1) * per_page
    files, total = file_service.get_user_files(
        db, current_user.id, skip, per_page)

    return FileListResponse(
        files=files,
        total=total,
        page=page,
        per_page=per_page
    )


@files_router.get("/{file_id}", response_model=FileUploadWithPreviews)
async def get_file_details(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file details with previews"""
    file_upload = file_service.get_file_upload(db, file_id, current_user.id)
    previews = file_service.get_file_previews(db, file_id, current_user.id)

    return FileUploadWithPreviews(
        **file_upload.__dict__,
        file_previews=previews
    )


@files_router.get("/{file_id}/previews", response_model=List[FilePreviewResponse])
async def get_file_previews(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file previews"""
    file_service.get_file_upload(db, file_id, current_user.id)  # Check access
    previews = file_service.get_file_previews(db, file_id, current_user.id)

    return previews


@files_router.post("/{file_id}/preview", response_model=List[FilePreviewResponse])
async def generate_file_preview(
    file_id: int,
    preview_request: FilePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate new preview for file"""
    file_upload = file_service.get_file_upload(db, file_id, current_user.id)

    try:
        # Process file again with new parameters
        if file_upload.file_type == "excel":
            previews = file_service.process_excel_file(
                file_upload.file_path,
                preview_request.max_rows
            )
        else:  # csv
            previews = [file_service.process_csv_file(
                file_upload.file_path,
                preview_request.max_rows
            )]

        # Delete existing previews
        existing_previews = file_service.get_file_previews(
            db, file_id, current_user.id)
        for preview in existing_previews:
            db.delete(preview)
        db.commit()

        # Create new preview records
        new_previews = file_service.create_file_preview_records(
            db, file_upload.id, previews)

        return new_previews

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating preview: {str(e)}")


@files_router.get("/{file_id}/status", response_model=FileProcessingStatus)
async def get_file_processing_status(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file processing status"""
    file_upload = file_service.get_file_upload(db, file_id, current_user.id)

    return FileProcessingStatus(
        file_id=file_upload.id,
        status=file_upload.processing_status,
        message=None,
        error=file_upload.error_message
    )


@files_router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete uploaded file"""
    try:
        file_service.delete_file(db, file_id, current_user.id)
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting file: {str(e)}")


@files_router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download uploaded file"""
    file_upload = file_service.get_file_upload(db, file_id, current_user.id)

    if not os.path.exists(file_upload.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_upload.file_path,
        filename=file_upload.original_filename,
        media_type=file_upload.mime_type
    )


@files_router.get("/stats/summary")
async def get_file_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file upload statistics for current user"""
    from sqlalchemy import func

    # Get total files
    total_files = db.query(func.count(FileUpload.id)).filter(
        FileUpload.uploaded_by == current_user.id
    ).scalar()

    # Get files by type
    excel_files = db.query(func.count(FileUpload.id)).filter(
        FileUpload.uploaded_by == current_user.id,
        FileUpload.file_type == "excel"
    ).scalar()

    csv_files = db.query(func.count(FileUpload.id)).filter(
        FileUpload.uploaded_by == current_user.id,
        FileUpload.file_type == "csv"
    ).scalar()

    # Get total file size
    total_size = db.query(func.sum(FileUpload.file_size)).filter(
        FileUpload.uploaded_by == current_user.id
    ).scalar() or 0

    # Get processing status counts
    pending_files = db.query(func.count(FileUpload.id)).filter(
        FileUpload.uploaded_by == current_user.id,
        FileUpload.processing_status == "pending"
    ).scalar()

    completed_files = db.query(func.count(FileUpload.id)).filter(
        FileUpload.uploaded_by == current_user.id,
        FileUpload.processing_status == "completed"
    ).scalar()

    failed_files = db.query(func.count(FileUpload.id)).filter(
        FileUpload.uploaded_by == current_user.id,
        FileUpload.processing_status == "failed"
    ).scalar()

    return {
        "total_files": total_files,
        "excel_files": excel_files,
        "csv_files": csv_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "pending_files": pending_files,
        "completed_files": completed_files,
        "failed_files": failed_files
    }
