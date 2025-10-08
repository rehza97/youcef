from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database.connection import get_db
from core.security import get_current_user
from models.dot import DOT
from models.user import User
from services.dot_service import DOTService
from services.permission_service import PermissionService

router = APIRouter(prefix="/api/dots", tags=["dots"])


# Pydantic Schemas
class DOTBase(BaseModel):
    """Base DOT schema"""
    name: str = Field(..., min_length=1, max_length=255,
                      description="DOT name")
    description: Optional[str] = Field(None, description="DOT description")


class DOTCreate(DOTBase):
    """Schema for creating a DOT"""
    pass


class DOTUpdate(BaseModel):
    """Schema for updating a DOT"""
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="DOT name")
    description: Optional[str] = Field(None, description="DOT description")


class DOTResponse(DOTBase):
    """Schema for DOT response"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DOTStatistics(BaseModel):
    """Schema for DOT statistics"""
    dot_id: int
    dot_name: str
    description: Optional[str] = None
    active_users: int
    parks: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DOTListResponse(BaseModel):
    """Schema for paginated DOT list"""
    items: List[DOTResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# DOT CRUD Endpoints

@router.post("/", response_model=DOTResponse, status_code=status.HTTP_201_CREATED)
def create_dot(
    dot: DOTCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new DOT (Admin only)

    - **name**: Unique DOT name (required)
    - **description**: Optional description of the DOT
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        new_dot = DOTService.get_or_create_dot(
            db=db,
            name=dot.name,
            description=dot.description
        )
        return new_dot
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create DOT: {str(e)}"
        )


@router.get("/", response_model=DOTListResponse)
def list_dots(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search DOT name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all DOTs with pagination

    - Admins/Super Users can see all DOTs
    - Regular users can only see their assigned DOT
    """
    try:
        # Get DOTs based on user permissions
        if current_user.is_superuser or current_user.is_staff:
            # Admins can see all DOTs with search
            dots, total = DOTService.list_dots_paginated(
                db=db,
                page=page,
                page_size=page_size,
                search=search
            )
        elif current_user.dot_id:
            # Regular users can only see their assigned DOT
            user_dot = DOTService.get_dot_by_id(
                db=db, dot_id=current_user.dot_id)
            dots = [user_dot] if user_dot else []
            total = 1 if user_dot else 0
        else:
            dots = []
            total = 0

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return DOTListResponse(
            items=dots,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list DOTs: {str(e)}"
        )


@router.get("/{dot_id}", response_model=DOTResponse)
def get_dot(
    dot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific DOT by ID

    - Users can only access DOTs they have permission for
    """
    # Validate access to this DOT
    if not DOTService.validate_dot_access(db=db, user_id=current_user.id, target_dot_id=dot_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this DOT"
        )

    dot = DOTService.get_dot_by_id(db=db, dot_id=dot_id)
    if not dot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DOT with ID {dot_id} not found"
        )

    return dot


@router.put("/{dot_id}", response_model=DOTResponse)
def update_dot(
    dot_id: int,
    dot_update: DOTUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a DOT (Admin only)

    - **name**: New DOT name (optional)
    - **description**: New description (optional)
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        updated_dot = DOTService.update_dot(
            db=db,
            dot_id=dot_id,
            name=dot_update.name,
            description=dot_update.description
        )
        if not updated_dot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DOT with ID {dot_id} not found"
            )
        return updated_dot
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update DOT: {str(e)}"
        )


@router.delete("/{dot_id}", status_code=status.HTTP_200_OK)
def delete_dot(
    dot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a DOT (Admin only)

    - Cannot delete if users or parks are assigned to it
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        success = DOTService.delete_dot(db=db, dot_id=dot_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DOT with ID {dot_id} not found"
            )
        return {
            "success": True,
            "message": f"DOT {dot_id} deleted successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete DOT: {str(e)}"
        )


@router.get("/{dot_id}/statistics", response_model=DOTStatistics)
def get_dot_statistics(
    dot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a specific DOT

    - Shows active users, park count, and other metrics
    """
    # Validate access to this DOT
    if not DOTService.validate_dot_access(db=db, user_id=current_user.id, target_dot_id=dot_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this DOT"
        )

    try:
        statistics = DOTService.get_dot_statistics(db=db, dot_id=dot_id)
        return statistics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DOT statistics: {str(e)}"
        )


@router.get("/{dot_id}/users")
def get_dot_users(
    dot_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get users assigned to a specific DOT (Admin only)

    Returns paginated list of users
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        skip = (page - 1) * page_size
        users = DOTService.get_users_in_dot(
            db=db,
            dot_id=dot_id,
            skip=skip,
            limit=page_size
        )

        # Count total users in DOT
        from models.user import User as UserModel
        total = db.query(UserModel).filter(
            UserModel.dot_id == dot_id,
            UserModel.is_active == True
        ).count()

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "users": users,
            "dot_id": dot_id,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DOT users: {str(e)}"
        )


@router.post("/{dot_id}/assign-user/{user_id}", status_code=status.HTTP_200_OK)
def assign_user_to_dot(
    dot_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a user to a DOT (Admin only)
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        success = DOTService.assign_user_to_dot(
            db=db,
            user_id=user_id,
            dot_id=dot_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign user to DOT"
            )

        return {
            "success": True,
            "message": f"User {user_id} assigned to DOT {dot_id}"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign user: {str(e)}"
        )


@router.delete("/{dot_id}/unassign-user/{user_id}", status_code=status.HTTP_200_OK)
def unassign_user_from_dot(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove user's DOT assignment (Admin only)
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        success = DOTService.unassign_user_from_dot(db=db, user_id=user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unassign user from DOT"
            )

        return {
            "success": True,
            "message": f"User {user_id} unassigned from DOT"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unassign user: {str(e)}"
        )
