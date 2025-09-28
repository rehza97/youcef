from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.file_upload import FileUpload
from services.secure_file_service import secure_file_service
from services.audit_service import audit_service
from services.dot_service import DOTService
from services.permission_service import PermissionService

router = APIRouter(prefix="/api/secure-files", tags=["secure-files"])

# Response Models

class SecureFileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    mime_type: str
    uploaded_by: int
    upload_context: str
    created_at: datetime
    can_download: bool

class FileUploadResponse(BaseModel):
    success: bool
    file_id: int
    filename: str
    original_filename: str
    file_size: int
    message: str

# File Upload Endpoints

@router.post("/upload", response_model=FileUploadResponse)
async def upload_secure_file(
    file: UploadFile = File(...),
    upload_context: str = Query("general", description="Upload context"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload file with comprehensive security validation"""
    try:
        # Check upload permissions
        PermissionService.require_upload_access(current_user, db)

        # Validate upload context
        valid_contexts = ["general", "message", "broadcast", "document", "image"]
        if upload_context not in valid_contexts:
            raise HTTPException(status_code=400, detail="Invalid upload context")

        # Save file securely
        file_upload = await secure_file_service.save_file_securely(
            db=db,
            file=file,
            user_id=current_user.id,
            upload_context=upload_context
        )

        return FileUploadResponse(
            success=True,
            file_id=file_upload.id,
            filename=file_upload.filename,
            original_filename=file_upload.original_filename,
            file_size=file_upload.file_size,
            message="File uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="file_upload_failed",
            resource_type="file",
            details=f"Failed to upload file: {str(e)}",
            severity="error"
        )
        raise HTTPException(status_code=500, detail="Failed to upload file")

@router.post("/upload-batch")
async def upload_multiple_secure_files(
    files: List[UploadFile] = File(...),
    upload_context: str = Query("general"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload multiple files with security validation"""
    try:
        # Check upload permissions
        PermissionService.require_upload_access(current_user, db)

        # Validate file count
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")

        successful_uploads = []
        failed_uploads = []

        for file in files:
            try:
                file_upload = await secure_file_service.save_file_securely(
                    db=db,
                    file=file,
                    user_id=current_user.id,
                    upload_context=upload_context
                )
                successful_uploads.append({
                    "file_id": file_upload.id,
                    "original_filename": file_upload.original_filename,
                    "file_size": file_upload.file_size
                })
            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": str(e)
                })

        return {
            "success": True,
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "total_successful": len(successful_uploads),
            "total_failed": len(failed_uploads)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process batch upload")

# File Management Endpoints

@router.get("/my-files", response_model=List[SecureFileResponse])
async def get_my_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    file_type: Optional[str] = Query(None),
    upload_context: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's uploaded files"""
    try:
        query = db.query(FileUpload).filter(FileUpload.uploaded_by == current_user.id)

        if file_type:
            query = query.filter(FileUpload.file_type == file_type)

        if upload_context:
            query = query.filter(FileUpload.file_metadata.contains(f'"upload_context": "{upload_context}"'))

        files = query.order_by(FileUpload.created_at.desc()).offset(offset).limit(limit).all()

        formatted_files = []
        for file_upload in files:
            # Parse metadata to get upload context
            import json
            try:
                metadata = json.loads(file_upload.file_metadata or '{}')
                context = metadata.get('upload_context', 'unknown')
            except:
                context = 'unknown'

            formatted_files.append(SecureFileResponse(
                id=file_upload.id,
                filename=file_upload.filename,
                original_filename=file_upload.original_filename,
                file_size=file_upload.file_size,
                file_type=file_upload.file_type,
                mime_type=file_upload.mime_type,
                uploaded_by=file_upload.uploaded_by,
                upload_context=context,
                created_at=file_upload.created_at,
                can_download=True  # User can always download their own files
            ))

        return formatted_files

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve files")

@router.get("/accessible-files", response_model=List[SecureFileResponse])
async def get_accessible_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get files accessible to user based on DOT permissions"""
    try:
        # Get user's accessible DOTs
        accessible_dots = DOTService.get_user_accessible_dots(db, current_user.id)

        # For admins, show all files
        if current_user.is_superuser or current_user.is_staff:
            query = db.query(FileUpload)
        else:
            # For regular users, show files from users in same DOTs
            users_in_dots = db.query(User).filter(User.dot_id.in_(accessible_dots)).all()
            user_ids = [u.id for u in users_in_dots]
            query = db.query(FileUpload).filter(FileUpload.uploaded_by.in_(user_ids))

        files = query.order_by(FileUpload.created_at.desc()).offset(offset).limit(limit).all()

        formatted_files = []
        for file_upload in files:
            # Check if user can access this specific file
            can_download = secure_file_service.validate_file_access(
                db, file_upload, current_user, "download"
            )

            # Parse metadata
            import json
            try:
                metadata = json.loads(file_upload.file_metadata or '{}')
                context = metadata.get('upload_context', 'unknown')
            except:
                context = 'unknown'

            formatted_files.append(SecureFileResponse(
                id=file_upload.id,
                filename=file_upload.filename,
                original_filename=file_upload.original_filename,
                file_size=file_upload.file_size,
                file_type=file_upload.file_type,
                mime_type=file_upload.mime_type,
                uploaded_by=file_upload.uploaded_by,
                upload_context=context,
                created_at=file_upload.created_at,
                can_download=can_download
            ))

        return formatted_files

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve accessible files")

@router.get("/{file_id}/download")
async def download_secure_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download file with security validation"""
    try:
        # Get file upload record
        file_upload = db.query(FileUpload).filter(FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        # Validate access
        if not secure_file_service.validate_file_access(db, file_upload, current_user, "download"):
            raise HTTPException(status_code=403, detail="Access denied to this file")

        # Get secure file path
        file_path = secure_file_service.get_secure_file_path(file_upload)
        if not file_path:
            raise HTTPException(status_code=404, detail="File not available")

        # Log file download
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="file_downloaded",
            resource_type="file",
            resource_id=file_id,
            details=f"Downloaded file: {file_upload.original_filename}",
            severity="info"
        )

        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(file_path),
            filename=file_upload.original_filename,
            media_type=file_upload.mime_type
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to download file")

@router.delete("/{file_id}")
async def delete_secure_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete file securely"""
    try:
        # Get file upload record
        file_upload = db.query(FileUpload).filter(FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        # Check if user can delete the file
        can_delete = (
            file_upload.uploaded_by == current_user.id or  # File owner
            current_user.is_superuser or current_user.is_staff  # Admin
        )

        if not can_delete:
            raise HTTPException(status_code=403, detail="Permission denied")

        # Delete file securely
        success = secure_file_service.delete_file_securely(db, file_upload)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file")

        return {
            "success": True,
            "message": "File deleted successfully",
            "file_id": file_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete file")

@router.get("/{file_id}/info")
async def get_file_info(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file information"""
    try:
        # Get file upload record
        file_upload = db.query(FileUpload).filter(FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        # Validate access
        if not secure_file_service.validate_file_access(db, file_upload, current_user, "view"):
            raise HTTPException(status_code=403, detail="Access denied to this file")

        # Get uploader info
        uploader = db.query(User).filter(User.id == file_upload.uploaded_by).first()

        # Parse metadata
        import json
        try:
            metadata = json.loads(file_upload.file_metadata or '{}')
        except:
            metadata = {}

        return {
            "id": file_upload.id,
            "original_filename": file_upload.original_filename,
            "file_size": file_upload.file_size,
            "file_type": file_upload.file_type,
            "mime_type": file_upload.mime_type,
            "uploaded_by": {
                "id": uploader.id,
                "username": uploader.username
            } if uploader else None,
            "upload_context": metadata.get('upload_context', 'unknown'),
            "file_hash": metadata.get('hash'),
            "created_at": file_upload.created_at.isoformat(),
            "can_download": secure_file_service.validate_file_access(db, file_upload, current_user, "download"),
            "can_delete": (
                file_upload.uploaded_by == current_user.id or
                current_user.is_superuser or current_user.is_staff
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get file info")

# Admin File Management

@router.get("/admin/all-files")
async def get_all_files_admin(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    file_type: Optional[str] = Query(None),
    uploader_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all files (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        query = db.query(FileUpload)

        if file_type:
            query = query.filter(FileUpload.file_type == file_type)

        if uploader_id:
            query = query.filter(FileUpload.uploaded_by == uploader_id)

        files = query.order_by(FileUpload.created_at.desc()).offset(offset).limit(limit).all()

        formatted_files = []
        for file_upload in files:
            uploader = db.query(User).filter(User.id == file_upload.uploaded_by).first()

            # Parse metadata
            import json
            try:
                metadata = json.loads(file_upload.file_metadata or '{}')
                context = metadata.get('upload_context', 'unknown')
                file_hash = metadata.get('hash', 'unknown')
            except:
                context = 'unknown'
                file_hash = 'unknown'

            formatted_files.append({
                "id": file_upload.id,
                "original_filename": file_upload.original_filename,
                "file_size": file_upload.file_size,
                "file_type": file_upload.file_type,
                "mime_type": file_upload.mime_type,
                "upload_context": context,
                "file_hash": file_hash,
                "uploader": {
                    "id": uploader.id,
                    "username": uploader.username
                } if uploader else None,
                "created_at": file_upload.created_at.isoformat()
            })

        return {
            "files": formatted_files,
            "total_files": len(formatted_files),
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve files")

@router.get("/stats")
async def get_file_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file upload statistics"""
    try:
        # Basic stats for all users
        user_file_count = db.query(FileUpload).filter(
            FileUpload.uploaded_by == current_user.id
        ).count()

        # Additional stats for admins
        if current_user.is_superuser or current_user.is_staff:
            total_files = db.query(FileUpload).count()
            total_size = db.query(func.sum(FileUpload.file_size)).scalar() or 0

            # File type distribution
            from sqlalchemy import func
            type_distribution = db.query(
                FileUpload.file_type,
                func.count(FileUpload.id).label('count'),
                func.sum(FileUpload.file_size).label('total_size')
            ).group_by(FileUpload.file_type).all()

            return {
                "user_files": user_file_count,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_type_distribution": [
                    {
                        "type": item.file_type,
                        "count": item.count,
                        "size_mb": round((item.total_size or 0) / (1024 * 1024), 2)
                    }
                    for item in type_distribution
                ]
            }
        else:
            return {
                "user_files": user_file_count
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get file statistics")