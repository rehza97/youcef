from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime

from database.connection import get_db
from core.security import get_current_user
from models.dot import DOT, AVAILABLE_MODULES
from models.user import User
from services.dot_service import DOTService
from services.permission_service import PermissionService

router = APIRouter(prefix="/api/dots", tags=["dots"])


# Pydantic Schemas
class DOTBase(BaseModel):
    """Base DOT schema"""
    name: str = Field(..., min_length=1, max_length=255,
                      description="DOT name")
    module: Optional[str] = Field(None, description=f"Module this DOT belongs to. Must be one of: {', '.join(AVAILABLE_MODULES)}")
    description: Optional[str] = Field(None, description="DOT description")

    @validator('module')
    def validate_module(cls, v):
        """Validate that module is in AVAILABLE_MODULES or None"""
        if v is not None and v not in AVAILABLE_MODULES:
            raise ValueError(f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")
        return v


class DOTCreate(DOTBase):
    """Schema for creating a DOT"""
    pass


class DOTUpdate(BaseModel):
    """Schema for updating a DOT"""
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="DOT name")
    module: Optional[str] = Field(None, description=f"Module this DOT belongs to. Must be one of: {', '.join(AVAILABLE_MODULES)}")
    description: Optional[str] = Field(None, description="DOT description")

    @validator('module')
    def validate_module(cls, v):
        """Validate that module is in AVAILABLE_MODULES or None"""
        if v is not None and v not in AVAILABLE_MODULES:
            raise ValueError(f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")
        return v


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

    - **name**: DOT name (unique per module)
    - **module**: Optional module this DOT belongs to (e.g., 'parc_corporate_ngbss', 'chiffre_affaires')
    - **description**: Optional description of the DOT

    Note: Same DOT name can exist in different modules (e.g., 4 "Alger" DOTs - one per module)
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        new_dot = DOTService.get_or_create_dot(
            db=db,
            name=dot.name,
            description=dot.description,
            module=dot.module
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
    module: Optional[str] = Query(None, description="Filter by module"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all DOTs with pagination

    - Admins/Super Users can see all DOTs
    - Regular users can only see their assigned DOT
    - Optional module filter to show only DOTs for a specific module
    """
    try:
        # Get DOTs based on user permissions
        if current_user.is_superuser or current_user.is_staff:
            # Admins can see all DOTs with search and module filter
            dots, total = DOTService.list_dots_paginated(
                db=db,
                page=page,
                page_size=page_size,
                search=search,
                module=module
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
    force: bool = Query(False, description="If true, delete DOT with ALL related records (CASCADE DELETE). Use with caution!"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a DOT (Admin only)

    **Parameters:**
    - **dot_id**: ID of the DOT to delete
    - **force**: If `false` (default), blocks deletion if related records exist
                 If `true`, performs CASCADE DELETE of DOT and ALL related data:
                   - Users
                   - Parks
                   - Revenue journals & objectives
                   - Encaissement records
                   - Créance records
                   - All other related data

    **⚠️ WARNING:** Using `force=true` will permanently delete the DOT and ALL its data!

    **Returns:**
    - Deletion statistics showing all deleted records
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        result = DOTService.delete_dot(db=db, dot_id=dot_id, force=force)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", f"DOT with ID {dot_id} not found")
            )

        return {
            "success": True,
            "message": f"DOT '{result['dot_name']}' deleted successfully" +
                      (f" with {result['total_deleted']} related records" if force else ""),
            "deleted_records": result.get("deleted_records", {}),
            "total_deleted": result.get("total_deleted", 0)
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


# ============================================================================
# Enhanced Module-Specific Endpoints
# ============================================================================

class DOTModuleSummary(BaseModel):
    """Summary of DOTs grouped by module"""
    module: Optional[str]
    count: int
    dots: List[DOTResponse]

    class Config:
        from_attributes = True


class BulkDOTUpdate(BaseModel):
    """Schema for bulk DOT updates"""
    dot_ids: List[int] = Field(..., description="List of DOT IDs to update")
    module: Optional[str] = Field(None, description="New module assignment")

    @validator('module')
    def validate_module(cls, v):
        """Validate that module is in AVAILABLE_MODULES or None"""
        if v is not None and v not in AVAILABLE_MODULES:
            raise ValueError(f"Invalid module. Must be one of: {', '.join(AVAILABLE_MODULES)}")
        return v


class DOTUsageStats(BaseModel):
    """Detailed usage statistics for a DOT"""
    dot_id: int
    dot_name: str
    module: Optional[str]
    users_count: int
    parks_count: int
    revenue_records: int
    encaissement_records: int
    creance_records: int
    can_delete: bool
    deletion_blockers: List[str]


@router.get("/modules/summary", response_model=List[DOTModuleSummary])
def get_dots_by_module(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get DOTs grouped by module

    Returns a summary showing how many DOTs belong to each module,
    including null (global) DOTs.
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        # Get all unique modules including None
        from sqlalchemy import distinct

        modules_query = db.query(distinct(DOT.module)).all()
        modules = [m[0] for m in modules_query]

        result = []
        for module in modules:
            # Get DOTs for this module
            if module:
                dots = db.query(DOT).filter(DOT.module == module).order_by(DOT.name).all()
            else:
                dots = db.query(DOT).filter(DOT.module.is_(None)).order_by(DOT.name).all()

            result.append(DOTModuleSummary(
                module=module,
                count=len(dots),
                dots=dots
            ))

        # Sort: named modules first (alphabetically), then None
        result.sort(key=lambda x: (x.module is None, x.module or ''))

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DOTs by module: {str(e)}"
        )


@router.post("/bulk-update", status_code=status.HTTP_200_OK)
def bulk_update_dots(
    bulk_update: BulkDOTUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk update DOT module assignments (Admin only)

    Allows assigning multiple DOTs to a module at once.
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        updated_count = 0
        errors = []

        for dot_id in bulk_update.dot_ids:
            try:
                dot = db.query(DOT).filter(DOT.id == dot_id).first()
                if not dot:
                    errors.append(f"DOT ID {dot_id} not found")
                    continue

                dot.module = bulk_update.module
                updated_count += 1

            except Exception as e:
                errors.append(f"DOT ID {dot_id}: {str(e)}")

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "total_requested": len(bulk_update.dot_ids),
            "errors": errors
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update DOTs: {str(e)}"
        )


@router.get("/{dot_id}/usage", response_model=DOTUsageStats)
def get_dot_usage_stats(
    dot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed usage statistics for a DOT

    Shows exactly what data is associated with this DOT and whether it can be safely deleted.
    """
    PermissionService.check_admin_permissions(current_user, db)

    try:
        dot = db.query(DOT).filter(DOT.id == dot_id).first()
        if not dot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DOT with ID {dot_id} not found"
            )

        # Count users
        from models.user import User as UserModel
        users_count = db.query(UserModel).filter(UserModel.dot_id == dot_id).count()

        # Count parks
        parks_count = 0
        try:
            from models.park import Park
            parks_count = db.query(Park).filter(Park.dot_id == dot_id).count()
        except ImportError:
            pass

        # Count revenue records
        revenue_records = 0
        try:
            from models.revenue import RevenueJournal
            revenue_records = db.query(RevenueJournal).filter(RevenueJournal.dot_id == dot_id).count()
        except ImportError:
            pass

        # Count encaissement records
        encaissement_records = 0
        try:
            from models.encaissement import EncaissementARDot
            encaissement_records = db.query(EncaissementARDot).filter(EncaissementARDot.dot_id == dot_id).count()
        except ImportError:
            pass

        # Count créance records
        creance_records = 0
        try:
            from models.creance import CreancePeriodiqueDot
            creance_records = db.query(CreancePeriodiqueDot).filter(CreancePeriodiqueDot.dot_id == dot_id).count()
        except ImportError:
            pass

        # Determine if can delete
        blockers = []
        if users_count > 0:
            blockers.append(f"{users_count} user(s) assigned")
        if parks_count > 0:
            blockers.append(f"{parks_count} park record(s)")
        if revenue_records > 0:
            blockers.append(f"{revenue_records} revenue record(s)")
        if encaissement_records > 0:
            blockers.append(f"{encaissement_records} encaissement record(s)")
        if creance_records > 0:
            blockers.append(f"{creance_records} créance record(s)")

        can_delete = len(blockers) == 0

        return DOTUsageStats(
            dot_id=dot_id,
            dot_name=dot.name,
            module=dot.module,
            users_count=users_count,
            parks_count=parks_count,
            revenue_records=revenue_records,
            encaissement_records=encaissement_records,
            creance_records=creance_records,
            can_delete=can_delete,
            deletion_blockers=blockers
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DOT usage stats: {str(e)}"
        )
