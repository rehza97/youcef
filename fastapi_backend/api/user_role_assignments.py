from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database.connection import get_db
from core.security import get_current_user
from models.role import Role, UserRole, UserRoleCreate
from models.user import User
from models.permission import Permission
from models.role import RolePermission
from services.permission_service import PermissionService

user_role_assignments_router = APIRouter()

# Request Models


class AssignRoleRequest(BaseModel):
    user_id: int
    role_id: int


class UpdateRolePermissionsRequest(BaseModel):
    permission_ids: List[int]

# Helper function to check admin permissions


def check_admin_permissions(current_user: User, db: Session):
    # Delegate to centralized permission service
    PermissionService.check_admin_permissions(current_user, db)


@user_role_assignments_router.post("/assign-role")
async def assign_role_to_user(
    assignment_data: AssignRoleRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a role to a user (Admin only)"""
    check_admin_permissions(current_user, db)

    # Check if user exists
    user = db.query(User).filter(User.id == assignment_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if role exists
    role = db.query(Role).filter(Role.id == assignment_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if user already has this role
    existing_assignment = db.query(UserRole).filter(
        UserRole.user_id == assignment_data.user_id,
        UserRole.role_id == assignment_data.role_id
    ).first()

    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {user.username} already has role {role.name}"
        )

    try:
        # Create role assignment
        user_role = UserRole(
            user_id=assignment_data.user_id,
            role_id=assignment_data.role_id
        )

        db.add(user_role)
        db.commit()

        return {
            "message": f"Role {role.name} assigned to user {user.username} successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning role: {str(e)}"
        )


@user_role_assignments_router.delete("/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a role from a user (Admin only)"""
    check_admin_permissions(current_user, db)

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Find the role assignment
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user.username} does not have role {role.name}"
        )

    try:
        db.delete(user_role)
        db.commit()

        return {
            "message": f"Role {role.name} removed from user {user.username} successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing role: {str(e)}"
        )


@user_role_assignments_router.get("/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all roles for a user"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get user roles
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    roles = []

    for user_role in user_roles:
        role = db.query(Role).filter(Role.id == user_role.role_id).first()
        if role:
            roles.append({
                "id": role.id,
                "name": role.name,
                "description": role.description
            })

    return {
        "user_id": user_id,
        "username": user.username,
        "roles": roles
    }


@user_role_assignments_router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all permissions for a role"""
    # Admin only
    PermissionService.check_admin_permissions(current_user, db)

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Fetch permissions linked to this role
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).filter(RolePermission.role_id == role_id).all()

    return {
        "role_id": role_id,
        "role_name": role.name,
        "permissions": [
            {
                "id": p.id,
                "codename": p.codename,
                "name": p.name,
                "description": p.description,
            }
            for p in permissions
        ],
    }


@user_role_assignments_router.post("/roles/{role_id}/update-permissions")
async def update_role_permissions(
    role_id: int,
    permission_data: UpdateRolePermissionsRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update permissions for a role (Admin only)"""
    check_admin_permissions(current_user, db)

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Validate provided permission IDs exist
    if permission_data.permission_ids:
        existing_permissions = db.query(Permission).filter(
            Permission.id.in_(permission_data.permission_ids)
        ).all()
        existing_ids = {p.id for p in existing_permissions}
        invalid_ids = [
            pid for pid in permission_data.permission_ids if pid not in existing_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission IDs: {invalid_ids}"
            )

    try:
        # Remove current mappings
        db.query(RolePermission).filter(
            RolePermission.role_id == role_id).delete()

        # Add new mappings
        for pid in permission_data.permission_ids:
            db.add(RolePermission(role_id=role_id, permission_id=pid))

        db.commit()

        return {
            "message": f"Permissions for role {role.name} updated successfully",
            "permission_ids": permission_data.permission_ids,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating role permissions: {str(e)}"
        )


@user_role_assignments_router.get("/check-role/{role_name}")
async def check_user_has_role(
    role_name: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user has a specific role"""
    # Find the role
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        return {"has_role": False, "message": "Role not found"}

    # Check if user has this role
    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id,
        UserRole.role_id == role.id
    ).first()

    return {
        "has_role": user_role is not None,
        "role_name": role_name,
        "user_id": current_user.id
    }


@user_role_assignments_router.get("/check-permission/{codename}")
async def check_user_has_permission(
    codename: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user has a specific permission"""
    has_permission = PermissionService.has_permission(
        current_user, db, codename)
    return {
        "has_permission": has_permission,
        "permission_codename": codename,
        "user_id": current_user.id,
    }
