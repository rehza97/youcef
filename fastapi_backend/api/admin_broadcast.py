from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from services.secure_file_service import secure_file_service
from services.admin_broadcast_service import admin_broadcast_service
from services.audit_service import audit_service
from services.permission_service import PermissionService

router = APIRouter(prefix="/api/admin/broadcast", tags=["admin-broadcast"])

# Request/Response Models


class MessageBroadcastRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    title: Optional[str] = Field(None, max_length=200)
    priority: str = Field("normal", pattern="^(low|normal|high|critical)$")


class FileBroadcastRequest(BaseModel):
    message: Optional[str] = Field(None, max_length=500)
    priority: str = Field("normal", pattern="^(low|normal|high|critical)$")


class DOTBroadcastRequest(FileBroadcastRequest):
    dot_id: int = Field(..., gt=0)


class UserBroadcastRequest(FileBroadcastRequest):
    user_ids: List[int] = Field(..., min_items=1, max_items=100)


class BroadcastResponse(BaseModel):
    success: bool
    broadcast_type: str
    file_id: Optional[int] = None
    recipients_notified: int
    realtime_notifications: int
    total_recipients: int
    message: Optional[str] = None

# File Broadcasting Endpoints


@router.post("/files/all-users", response_model=BroadcastResponse)
async def broadcast_file_to_all_users(
    file: UploadFile = File(...),
    message: Optional[str] = Form(None),
    priority: str = Form("normal"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Broadcast file to all active users (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Validate priority
        if priority not in ["low", "normal", "high", "critical"]:
            raise HTTPException(
                status_code=400, detail="Invalid priority level")

        # Save file securely
        file_upload = await secure_file_service.save_file_securely(
            db=db,
            file=file,
            user_id=current_user.id,
            upload_context="broadcast"
        )

        # Broadcast file
        result = await admin_broadcast_service.broadcast_file_to_all_users(
            db=db,
            admin_user=current_user,
            file_upload=file_upload,
            message=message,
            priority=priority
        )

        return BroadcastResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="file_broadcast_failed",
            resource_type="broadcast",
            details=f"Failed to broadcast file to all users: {str(e)}",
            severity="error"
        )
        raise HTTPException(status_code=500, detail="Failed to broadcast file")


@router.post("/files/dot/{dot_id}", response_model=BroadcastResponse)
async def broadcast_file_to_dot(
    dot_id: int,
    file: UploadFile = File(...),
    message: Optional[str] = Form(None),
    priority: str = Form("normal"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Broadcast file to users in specific DOT (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Validate priority
        if priority not in ["low", "normal", "high", "critical"]:
            raise HTTPException(
                status_code=400, detail="Invalid priority level")

        # Save file securely
        file_upload = await secure_file_service.save_file_securely(
            db=db,
            file=file,
            user_id=current_user.id,
            upload_context="broadcast"
        )

        # Broadcast file to DOT
        result = await admin_broadcast_service.broadcast_file_to_dot_users(
            db=db,
            admin_user=current_user,
            file_upload=file_upload,
            dot_id=dot_id,
            message=message,
            priority=priority
        )

        return BroadcastResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="file_broadcast_dot_failed",
            resource_type="broadcast",
            details=f"Failed to broadcast file to DOT {dot_id}: {str(e)}",
            severity="error"
        )
        raise HTTPException(
            status_code=500, detail="Failed to broadcast file to DOT")


@router.post("/files/users", response_model=BroadcastResponse)
async def broadcast_file_to_selected_users(
    file: UploadFile = File(...),
    user_ids: str = Form(..., description="Comma-separated user IDs"),
    message: Optional[str] = Form(None),
    priority: str = Form("normal"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Broadcast file to selected users (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Parse user IDs
        try:
            user_id_list = [int(uid.strip())
                            for uid in user_ids.split(',') if uid.strip()]
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid user IDs format")

        if len(user_id_list) > 100:
            raise HTTPException(
                status_code=400, detail="Too many recipients (max 100)")

        # Validate priority
        if priority not in ["low", "normal", "high", "critical"]:
            raise HTTPException(
                status_code=400, detail="Invalid priority level")

        # Save file securely
        file_upload = await secure_file_service.save_file_securely(
            db=db,
            file=file,
            user_id=current_user.id,
            upload_context="broadcast"
        )

        # Broadcast file to selected users
        result = await admin_broadcast_service.broadcast_file_to_selected_users(
            db=db,
            admin_user=current_user,
            file_upload=file_upload,
            user_ids=user_id_list,
            message=message,
            priority=priority
        )

        return BroadcastResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="file_broadcast_users_failed",
            resource_type="broadcast",
            details=f"Failed to broadcast file to selected users: {str(e)}",
            severity="error"
        )
        raise HTTPException(
            status_code=500, detail="Failed to broadcast file to users")

# Message Broadcasting Endpoints


@router.post("/messages/all-users", response_model=BroadcastResponse)
async def broadcast_message_to_all_users(
    request: MessageBroadcastRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Broadcast text message to all users (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        result = await admin_broadcast_service.broadcast_message_to_all_users(
            db=db,
            admin_user=current_user,
            message=request.message,
            title=request.title,
            priority=request.priority
        )

        return BroadcastResponse(**result, message="Message broadcast completed")

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="message_broadcast_failed",
            resource_type="broadcast",
            details=f"Failed to broadcast message: {str(e)}",
            severity="error"
        )
        raise HTTPException(
            status_code=500, detail="Failed to broadcast message")

# Broadcast Management Endpoints


@router.get("/files", response_model=List[dict])
async def get_broadcast_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get broadcast files accessible to user"""
    try:
        broadcast_files = admin_broadcast_service.get_broadcast_files(
            db=db,
            user=current_user,
            limit=limit,
            offset=offset
        )

        return broadcast_files

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve broadcast files")


@router.get("/files/{file_id}/download")
async def download_broadcast_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download broadcast file with security validation"""
    try:
        # Get file upload record
        from models.file_upload import FileUpload
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        # Validate access
        if not secure_file_service.validate_file_access(db, file_upload, current_user, "download"):
            raise HTTPException(
                status_code=403, detail="Access denied to this file")

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
            details=f"Downloaded broadcast file: {file_upload.original_filename}",
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


@router.delete("/files/{file_id}")
async def delete_broadcast_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete broadcast file (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Get file upload record
        from models.file_upload import FileUpload
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete file securely
        success = secure_file_service.delete_file_securely(db, file_upload)

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete file")

        # Log file deletion
        audit_service.log_activity(
            db=db,
            user_id=current_user.id,
            action="broadcast_file_deleted",
            resource_type="file",
            resource_id=file_id,
            details=f"Deleted broadcast file: {file_upload.original_filename}",
            severity="info"
        )

        return {
            "success": True,
            "message": "File deleted successfully",
            "file_id": file_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete file")

# Analytics Endpoints


@router.get("/analytics/summary")
async def get_broadcast_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get broadcast analytics (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Get broadcast activity summary
        summary = audit_service.get_activity_summary(db)

        # Filter for broadcast-related activities
        broadcast_actions = [action for action in summary.get("top_actions", {}).keys()
                             if "broadcast" in action]

        broadcast_summary = {
            "total_broadcasts": sum(summary.get("top_actions", {}).get(action, 0)
                                    for action in broadcast_actions),
            "broadcast_actions": {action: count for action, count in summary.get("top_actions", {}).items()
                                  if "broadcast" in action},
            "period": summary.get("period", {}),
            "severity_breakdown": summary.get("severity_breakdown", {})
        }

        return broadcast_summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve analytics")

# User Management for Broadcasting


@router.get("/users/by-dot/{dot_id}")
async def get_dot_users_for_broadcast(
    dot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users in DOT for broadcasting (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        from services.dot_service import DOTService
        users = DOTService.get_users_in_dot(db, dot_id, skip=0, limit=1000)

        formatted_users = []
        for user in users:
            formatted_users.append({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active
            })

        return {
            "dot_id": dot_id,
            "users": formatted_users,
            "total_users": len(formatted_users)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve DOT users")


@router.get("/users/all")
async def get_all_users_for_broadcast(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users for broadcasting (Admin only)"""
    try:
        # Check admin permissions
        PermissionService.check_admin_permissions(current_user, db)

        query = db.query(User).filter(User.is_active == True)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (User.username.ilike(search_filter)) |
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter))
            )

        users = query.limit(limit).all()

        formatted_users = []
        for user in users:
            dot_info = None
            if user.dot:
                dot_info = {
                    "id": user.dot.id,
                    "name": user.dot.name
                }

            formatted_users.append({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "dot": dot_info
            })

        return {
            "users": formatted_users,
            "total_users": len(formatted_users)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve users")
