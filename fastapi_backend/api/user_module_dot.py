"""
User Module DOT Management API
Allows managing module-specific DOT assignments for users
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.user_module_dot import (
    UserModuleDOT,
    MODULE_PARC_CORPORATE_NGBSS,
    MODULE_CHIFFRE_AFFAIRES,
    MODULE_ENCAISSEMENT_AR_DOT,
    MODULE_CREANCE_PERIODIQUE_DOT,
    ALL_MODULES
)
from services.dot_service import DOTService
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)

user_module_dot_router = APIRouter(prefix="/api/user-module-dots", tags=["User Module DOT"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class UserModuleDOTCreate(BaseModel):
    """Schema for creating a module-specific DOT assignment"""
    user_id: int
    module: str
    dot_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "module": "parc_corporate_ngbss",
                "dot_id": 5
            }
        }


class UserModuleDOTResponse(BaseModel):
    """Schema for module-specific DOT assignment response"""
    id: int
    user_id: int
    dot_id: int
    module: str
    dot_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserModuleDOTUpdate(BaseModel):
    """Schema for updating a module-specific DOT assignment"""
    dot_id: int


# ============================================================================
# Endpoints
# ============================================================================

@user_module_dot_router.get("/modules", response_model=List[str])
async def get_available_modules(
    current_user: User = Depends(get_current_user)
):
    """Get list of available modules"""
    return ALL_MODULES


@user_module_dot_router.post("", response_model=UserModuleDOTResponse)
async def assign_user_to_module_dot(
    assignment: UserModuleDOTCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a user to a specific DOT for a module
    
    Requires admin or superuser permissions
    """
    try:
        # Check permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Assign the DOT
        DOTService.assign_user_to_module_dot(
            db=db,
            user_id=assignment.user_id,
            module=assignment.module,
            dot_id=assignment.dot_id
        )

        # Fetch the created/updated assignment
        module_dot = db.query(UserModuleDOT).filter(
            UserModuleDOT.user_id == assignment.user_id,
            UserModuleDOT.module == assignment.module
        ).first()

        if not module_dot:
            raise HTTPException(status_code=500, detail="Failed to create assignment")

        # Get DOT name
        dot = DOTService.get_dot_by_id(db, assignment.dot_id)
        dot_name = dot.name if dot else None

        return UserModuleDOTResponse(
            id=module_dot.id,
            user_id=module_dot.user_id,
            dot_id=module_dot.dot_id,
            module=module_dot.module,
            dot_name=dot_name
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning user to module DOT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to assign: {str(e)}")


@user_module_dot_router.get("/user/{user_id}", response_model=Dict[str, UserModuleDOTResponse])
async def get_user_module_dots(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all module-specific DOT assignments for a user
    
    Users can view their own assignments, admins can view any user's assignments
    """
    try:
        # Check if user can view this (own profile or admin)
        if current_user.id != user_id:
            PermissionService.check_admin_permissions(current_user, db)

        # Get all module DOT assignments
        module_dots = db.query(UserModuleDOT).filter(
            UserModuleDOT.user_id == user_id
        ).all()

        result = {}
        for md in module_dots:
            dot = DOTService.get_dot_by_id(db, md.dot_id)
            result[md.module] = UserModuleDOTResponse(
                id=md.id,
                user_id=md.user_id,
                dot_id=md.dot_id,
                module=md.module,
                dot_name=dot.name if dot else None
            )

        return result

    except Exception as e:
        logger.error(f"Error getting user module DOTs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve: {str(e)}")


@user_module_dot_router.get("/module/{module}", response_model=List[UserModuleDOTResponse])
async def get_module_dot_assignments(
    module: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all DOT assignments for a specific module
    
    Requires admin permissions
    """
    try:
        # Check permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Validate module
        if module not in ALL_MODULES:
            raise HTTPException(status_code=400, detail=f"Invalid module: {module}")

        # Get all assignments for this module
        module_dots = db.query(UserModuleDOT).filter(
            UserModuleDOT.module == module
        ).all()

        result = []
        for md in module_dots:
            dot = DOTService.get_dot_by_id(db, md.dot_id)
            result.append(UserModuleDOTResponse(
                id=md.id,
                user_id=md.user_id,
                dot_id=md.dot_id,
                module=md.module,
                dot_name=dot.name if dot else None
            ))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting module DOT assignments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve: {str(e)}")


@user_module_dot_router.put("/user/{user_id}/module/{module}", response_model=UserModuleDOTResponse)
async def update_user_module_dot(
    user_id: int,
    module: str,
    update: UserModuleDOTUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a user's module-specific DOT assignment
    
    Requires admin permissions
    """
    try:
        # Check permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Validate module
        if module not in ALL_MODULES:
            raise HTTPException(status_code=400, detail=f"Invalid module: {module}")

        # Update assignment
        DOTService.assign_user_to_module_dot(
            db=db,
            user_id=user_id,
            module=module,
            dot_id=update.dot_id
        )

        # Fetch updated assignment
        module_dot = db.query(UserModuleDOT).filter(
            UserModuleDOT.user_id == user_id,
            UserModuleDOT.module == module
        ).first()

        if not module_dot:
            raise HTTPException(status_code=404, detail="Assignment not found")

        dot = DOTService.get_dot_by_id(db, module_dot.dot_id)

        return UserModuleDOTResponse(
            id=module_dot.id,
            user_id=module_dot.user_id,
            dot_id=module_dot.dot_id,
            module=module_dot.module,
            dot_name=dot.name if dot else None
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user module DOT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")


@user_module_dot_router.delete("/user/{user_id}/module/{module}")
async def remove_user_module_dot(
    user_id: int,
    module: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a user's module-specific DOT assignment
    
    Requires admin permissions
    """
    try:
        # Check permissions
        PermissionService.check_admin_permissions(current_user, db)

        # Validate module
        if module not in ALL_MODULES:
            raise HTTPException(status_code=400, detail=f"Invalid module: {module}")

        # Remove assignment
        DOTService.unassign_user_from_module_dot(
            db=db,
            user_id=user_id,
            module=module
        )

        return {"message": f"Removed DOT assignment for user {user_id} in module {module}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user module DOT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove: {str(e)}")





