from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from core.security import get_current_user
from models.permission import Permission, PermissionResponse, PermissionCreate, PermissionUpdate
from models.role import Role
from models.user import User
from services.permission_service import PermissionService
import logging

logger = logging.getLogger(__name__)

permission_management_router = APIRouter()
permission_service = PermissionService()


@permission_management_router.get("/permissions/", response_model=List[PermissionResponse])
async def get_permissions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all permissions"""
    logger.info(f"Permissions list requested by user {current_user.id}")
    # Restrict listing permissions to admin or can_manage_rbac
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")
    permissions = db.query(Permission).all()
    return [PermissionResponse.from_orm(permission) for permission in permissions]


@permission_management_router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get permission by ID"""
    logger.info(
        f"Permission {permission_id} requested by user {current_user.id}")
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")
    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return PermissionResponse.from_orm(permission)


@permission_management_router.post("/permissions/", response_model=PermissionResponse)
async def create_permission(
    permission: PermissionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new permission (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    # Check if permission codename already exists
    existing_permission = db.query(Permission).filter(
        Permission.codename == permission.codename
    ).first()
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission codename already exists"
        )

    db_permission = Permission(
        codename=permission.codename,
        name=permission.name,
        description=permission.description
    )
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)

    logger.info(
        f"Permission '{permission.codename}' created by admin {current_user.id}")
    return PermissionResponse.from_orm(db_permission)


@permission_management_router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update permission (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    # Check if new codename conflicts with existing permission
    if permission_update.codename and permission_update.codename != permission.codename:
        existing_permission = db.query(Permission).filter(
            Permission.codename == permission_update.codename
        ).first()
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission codename already exists"
            )

    # Update permission fields
    update_data = permission_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)

    db.commit()
    db.refresh(permission)

    logger.info(
        f"Permission {permission_id} updated by admin {current_user.id}")
    return PermissionResponse.from_orm(permission)


@permission_management_router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete permission (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    # Prevent deletion of system permissions
    system_permissions = [
        'view_users', 'edit_users', 'delete_users', 'manage_roles',
        'send_messages', 'view_messages', 'manage_notifications'
    ]
    if permission.codename in system_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system permissions"
        )

    # Check if permission is assigned to any roles
    from models.role import RolePermission
    role_assignments = db.query(RolePermission).filter(
        RolePermission.permission_id == permission_id
    ).count()

    if role_assignments > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete permission. It is assigned to {role_assignments} roles"
        )

    db.delete(permission)
    db.commit()

    logger.info(
        f"Permission {permission_id} deleted by admin {current_user.id}")
    return {"message": "Permission deleted successfully"}


@permission_management_router.get("/permissions/{permission_id}/roles")
async def get_permission_roles(
    permission_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all roles that have a specific permission (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    from models.role import RolePermission, RoleResponse
    role_permissions = db.query(RolePermission).filter(
        RolePermission.permission_id == permission_id
    ).all()

    roles = []
    for role_permission in role_permissions:
        role = db.query(Role).filter(
            Role.id == role_permission.role_id).first()
        if role:
            roles.append({
                'role_id': role.id,
                'role_name': role.name,
                'description': role.description,
                'assigned_at': role_permission.created_at.isoformat() if role_permission.created_at else None
            })

    logger.info(
        f"Permission {permission_id} roles list requested by admin {current_user.id}")
    return {
        'permission': PermissionResponse.from_orm(permission),
        'roles': roles,
        'total_roles': len(roles)
    }


@permission_management_router.post("/permissions/bulk-create")
async def bulk_create_permissions(
    permissions: List[PermissionCreate],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create multiple permissions at once (Admin or can_manage_rbac)"""
    if not (permission_service.is_admin(current_user, db) or permission_service.has_permission(current_user, db, "can_manage_rbac")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Permission required: can_manage_rbac")

    if len(permissions) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create more than 50 permissions at once"
        )

    created_permissions = []
    skipped_permissions = []

    for perm_data in permissions:
        # Check if permission already exists
        existing_permission = db.query(Permission).filter(
            Permission.codename == perm_data.codename
        ).first()

        if existing_permission:
            skipped_permissions.append({
                'codename': perm_data.codename,
                'reason': 'Already exists'
            })
            continue

        try:
            db_permission = Permission(
                codename=perm_data.codename,
                name=perm_data.name,
                description=perm_data.description
            )
            db.add(db_permission)
            db.flush()  # Get ID without committing
            created_permissions.append(
                PermissionResponse.from_orm(db_permission))

        except Exception as e:
            skipped_permissions.append({
                'codename': perm_data.codename,
                'reason': f'Error: {str(e)}'
            })

    db.commit()

    logger.info(
        f"Bulk permission creation by admin {current_user.id}: {len(created_permissions)} created, {len(skipped_permissions)} skipped")

    return {
        'created': created_permissions,
        'skipped': skipped_permissions,
        'summary': {
            'created_count': len(created_permissions),
            'skipped_count': len(skipped_permissions),
            'total_requested': len(permissions)
        }
    }
