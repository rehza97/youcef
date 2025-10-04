from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from core.security import get_current_user
from models.role import Role, RoleResponse, RoleCreate, RoleUpdate
from models.user import User
from services.permission_service import PermissionService
import logging

logger = logging.getLogger(__name__)

role_management_router = APIRouter()
permission_service = PermissionService()


@role_management_router.get("/roles/", response_model=List[RoleResponse])
async def get_roles(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all roles"""
    logger.info(f"Roles list requested by user {current_user.id}")
    # Restrict listing roles to admin or can_manage_rbac
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")
    roles = db.query(Role).all()

    # Build response with counts
    role_responses = []
    for role in roles:
        role_dict = {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "permissions_count": len(role.permissions),
            "users_count": len(role.users)
        }
        role_responses.append(RoleResponse(**role_dict))

    return role_responses


@role_management_router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get role by ID"""
    logger.info(f"Role {role_id} requested by user {current_user.id}")
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return RoleResponse.from_orm(role)


@role_management_router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new role (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    # Check if role name already exists
    existing_role = db.query(Role).filter(Role.name == role.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )

    db_role = Role(
        name=role.name,
        description=role.description
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)

    logger.info(f"Role '{role.name}' created by admin {current_user.id}")
    return RoleResponse.from_orm(db_role)


@role_management_router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update role (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if new name conflicts with existing role
    if role_update.name and role_update.name != role.name:
        existing_role = db.query(Role).filter(
            Role.name == role_update.name).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists"
            )

    # Update role fields
    update_data = role_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)

    logger.info(f"Role {role_id} updated by admin {current_user.id}")
    return RoleResponse.from_orm(role)


@role_management_router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete role (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Prevent deletion of system roles
    system_roles = ['admin', 'user', 'moderator']
    if role.name in system_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )

    # Check if role is assigned to any users
    from models.role import UserRole
    user_assignments = db.query(UserRole).filter(
        UserRole.role_id == role_id).count()
    if user_assignments > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role. It is assigned to {user_assignments} users"
        )

    db.delete(role)
    db.commit()

    logger.info(f"Role {role_id} deleted by admin {current_user.id}")
    return {"message": "Role deleted successfully"}


@role_management_router.get("/roles/{role_id}/users")
async def get_role_users(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users assigned to a specific role (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    from models.role import UserRole
    user_roles = db.query(UserRole).filter(UserRole.role_id == role_id).all()

    users = []
    for user_role in user_roles:
        user = db.query(User).filter(User.id == user_role.user_id).first()
        if user:
            users.append({
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'assigned_at': user_role.created_at.isoformat() if user_role.created_at else None
            })

    logger.info(
        f"Role {role_id} users list requested by admin {current_user.id}")
    return {
        'role': RoleResponse.from_orm(role),
        'users': users,
        'total_users': len(users)
    }
