from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from core.security import get_current_user, get_password_hash
from models.user import User, UserResponse, UserUpdate, UserProfile, UserCreate
from models.role import Role, RoleResponse, UserRole, UserRoleCreate, RoleCreate, RoleUpdate
from models.permission import Permission, PermissionResponse, PermissionCreate, PermissionUpdate
from core.config import settings

users_router = APIRouter()


# ==================== USER CRUD OPERATIONS ====================

@users_router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role not found"
        )

    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id,
        UserRole.role_id == admin_role.id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
        )

    # Check if username already exists
    existing_user = db.query(User).filter(
        User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists
    existing_email = db.query(User).filter(
        User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=user_data.is_active,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )


@users_router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users (paginated)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@users_router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    return current_user


@users_router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "password" and value:
            value = get_password_hash(value)
        setattr(current_user, field, value)

    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )


@users_router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by username or email"""
    users = db.query(User).filter(
        (User.username.contains(q)) | (User.email.contains(q))
    ).all()
    return users


@users_router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific user profile"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@users_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user (Admin only or self)"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions - only admin can update other users, or user can update self
    if user_id != current_user.id:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            user_role = db.query(UserRole).filter(
                UserRole.user_id == current_user.id,
                UserRole.role_id == admin_role.id
            ).first()
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can update other users"
                )

    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "password" and value:
            value = get_password_hash(value)
        setattr(user, field, value)

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )


@users_router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user (Admin only)"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role not found"
        )

    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id,
        UserRole.role_id == admin_role.id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )

    # Prevent deleting self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    try:
        # Delete user roles first
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()

        # Delete user
        db.delete(user)
        db.commit()

        return {
            "success": True,
            "message": "User deleted successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting user"
        )


# ==================== ROLE CRUD OPERATIONS ====================

@users_router.get("/roles/", response_model=List[RoleResponse])
async def get_roles(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all roles"""
    roles = db.query(Role).all()
    return roles


@users_router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role


@users_router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new role (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create roles"
            )

    # Check if role already exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists"
        )

    role = Role(**role_data.dict())
    try:
        db.add(role)
        db.commit()
        db.refresh(role)
        return role
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating role"
        )


@users_router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update role (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update roles"
            )

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Update role fields
    update_data = role_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)

    try:
        db.commit()
        db.refresh(role)
        return role
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating role"
        )


@users_router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete role (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete roles"
            )

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if role is in use
    user_roles = db.query(UserRole).filter(UserRole.role_id == role_id).count()
    if user_roles > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that is assigned to users"
        )

    try:
        # Delete role permissions first
        from models.role import RolePermission
        db.query(RolePermission).filter(
            RolePermission.role_id == role_id).delete()

        # Delete role
        db.delete(role)
        db.commit()

        return {
            "success": True,
            "message": "Role deleted successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting role"
        )


# ==================== PERMISSION CRUD OPERATIONS ====================

@users_router.get("/permissions/", response_model=List[PermissionResponse])
async def get_permissions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all permissions"""
    permissions = db.query(Permission).all()
    return permissions


@users_router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific permission"""
    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return permission


@users_router.post("/permissions/", response_model=PermissionResponse)
async def create_permission(
    permission_data: PermissionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new permission (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create permissions"
            )

    # Check if permission already exists
    existing = db.query(Permission).filter(
        Permission.codename == permission_data.codename
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already exists"
        )

    permission = Permission(**permission_data.dict())
    try:
        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating permission"
        )


@users_router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update permission (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update permissions"
            )

    # Check if permission exists
    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    # Update permission fields
    update_data = permission_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)

    try:
        db.commit()
        db.refresh(permission)
        return permission
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating permission"
        )


@users_router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete permission (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete permissions"
            )

    # Check if permission exists
    permission = db.query(Permission).filter(
        Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    # Check if permission is assigned to roles
    from models.role import RolePermission
    role_permissions = db.query(RolePermission).filter(
        RolePermission.permission_id == permission_id
    ).count()
    if role_permissions > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete permission that is assigned to roles"
        )

    try:
        db.delete(permission)
        db.commit()

        return {
            "success": True,
            "message": "Permission deleted successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting permission"
        )


# ==================== ROLE ASSIGNMENT OPERATIONS ====================

@users_router.post("/assign-role")
async def assign_role(
    role_assignment: UserRoleCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign role to user (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can assign roles"
            )

    # Check if user exists
    user = db.query(User).filter(User.id == role_assignment.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_assignment.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if role is already assigned
    existing = db.query(UserRole).filter(
        UserRole.user_id == role_assignment.user_id,
        UserRole.role_id == role_assignment.role_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned to user"
        )

    # Assign role
    user_role = UserRole(**role_assignment.dict())
    try:
        db.add(user_role)
        db.commit()
        return {
            "success": True,
            "message": "Role assigned successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error assigning role"
        )


@users_router.delete("/users/{user_id}/roles/{role_id}")
async def remove_user_role(
    user_id: int,
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove role from user (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can remove roles"
            )

    # Check if user-role assignment exists
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found"
        )

    try:
        db.delete(user_role)
        db.commit()
        return {
            "success": True,
            "message": "Role removed successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing role"
        )


@users_router.get("/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user roles"""
    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    return user_roles


@users_router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get role permissions"""
    from models.role import RolePermission
    role_permissions = db.query(RolePermission).filter(
        RolePermission.role_id == role_id).all()
    return role_permissions


@users_router.post("/roles/{role_id}/update-permissions")
async def update_role_permissions(
    role_id: int,
    permission_ids: List[int],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update role permissions (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update role permissions"
            )

    # Check if role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Remove existing permissions
    from models.role import RolePermission
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

    # Add new permissions
    for permission_id in permission_ids:
        role_permission = RolePermission(
            role_id=role_id, permission_id=permission_id)
        db.add(role_permission)

    try:
        db.commit()
        return {
            "success": True,
            "message": "Role permissions updated successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating role permissions"
        )


# ==================== PERMISSION CHECKING ====================

@users_router.get("/check-role/{role_name}")
async def check_user_role(
    role_name: str,
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has specific role"""
    user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user_id,
        Role.name == role_name
    ).first()

    has_role = user_role is not None
    return {
        "user_id": user_id,
        "role_name": role_name,
        "has_role": has_role
    }


@users_router.get("/check-permission/{codename}")
async def check_user_permission(
    codename: str,
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has specific permission"""
    # This is a simplified check - in a real implementation,
    # you'd check permissions through roles
    from models.role import RolePermission
    user_permission = db.query(UserRole).join(Role).join(
        RolePermission
    ).join(Permission).filter(
        UserRole.user_id == user_id,
        Permission.codename == codename
    ).first()

    has_permission = user_permission is not None
    return {
        "user_id": user_id,
        "permission_codename": codename,
        "has_permission": has_permission
    }
