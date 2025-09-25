"""
Permission service for role and permission management
Handles authorization checks and permission-related operations
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.role import Role, UserRole
from models.user import User
import logging

logger = logging.getLogger(__name__)


class PermissionService:
    """Service class for handling permission and authorization logic"""

    @staticmethod
    def check_admin_permissions(current_user: User, db: Session):
        """Check if current user has admin permissions"""
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            logger.error("Admin role not found in database")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role not found"
            )

        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()

        if not user_role:
            logger.warning(f"User {current_user.id} attempted unauthorized admin action")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        return True

    @staticmethod
    def check_moderator_permissions(current_user: User, db: Session):
        """Check if current user has moderator permissions"""
        # First check if user is admin (admins have all permissions)
        try:
            PermissionService.check_admin_permissions(current_user, db)
            return True
        except HTTPException:
            pass

        # Check for moderator role
        moderator_role = db.query(Role).filter(Role.name == "moderator").first()
        if not moderator_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Moderator role not found"
            )

        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == moderator_role.id
        ).first()

        if not user_role:
            logger.warning(f"User {current_user.id} attempted unauthorized moderator action")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Moderator access required"
            )

        return True

    @staticmethod
    def has_permission(current_user: User, db: Session, permission_codename: str) -> bool:
        """Check if user has specific permission"""
        try:
            from models.permission import Permission
            from models.role import RolePermission

            # Get user roles
            user_roles = db.query(UserRole).filter(
                UserRole.user_id == current_user.id
            ).all()

            if not user_roles:
                return False

            role_ids = [ur.role_id for ur in user_roles]

            # Get permission
            permission = db.query(Permission).filter(
                Permission.codename == permission_codename
            ).first()

            if not permission:
                return False

            # Check if any of user's roles have this permission
            role_permission = db.query(RolePermission).filter(
                RolePermission.role_id.in_(role_ids),
                RolePermission.permission_id == permission.id
            ).first()

            return role_permission is not None

        except Exception as e:
            logger.error(f"Error checking permission {permission_codename} for user {current_user.id}: {e}")
            return False

    @staticmethod
    def require_permission(current_user: User, db: Session, permission_codename: str):
        """Require specific permission or raise HTTPException"""
        if not PermissionService.has_permission(current_user, db, permission_codename):
            logger.warning(f"User {current_user.id} lacks required permission: {permission_codename}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_codename}"
            )

    @staticmethod
    def get_user_permissions(current_user: User, db: Session) -> list:
        """Get all permissions for a user"""
        try:
            from models.permission import Permission
            from models.role import RolePermission

            # Get user roles
            user_roles = db.query(UserRole).filter(
                UserRole.user_id == current_user.id
            ).all()

            if not user_roles:
                return []

            role_ids = [ur.role_id for ur in user_roles]

            # Get all permissions for user's roles
            permissions = db.query(Permission).join(
                RolePermission, Permission.id == RolePermission.permission_id
            ).filter(
                RolePermission.role_id.in_(role_ids)
            ).distinct().all()

            return [perm.codename for perm in permissions]

        except Exception as e:
            logger.error(f"Error getting permissions for user {current_user.id}: {e}")
            return []

    @staticmethod
    def get_user_roles(current_user: User, db: Session) -> list:
        """Get all roles for a user"""
        try:
            user_roles = db.query(UserRole).filter(
                UserRole.user_id == current_user.id
            ).all()

            if not user_roles:
                return []

            role_ids = [ur.role_id for ur in user_roles]
            roles = db.query(Role).filter(Role.id.in_(role_ids)).all()

            return [{'id': role.id, 'name': role.name, 'description': role.description} for role in roles]

        except Exception as e:
            logger.error(f"Error getting roles for user {current_user.id}: {e}")
            return []

    @staticmethod
    def is_admin(current_user: User, db: Session) -> bool:
        """Check if user is admin (non-raising version)"""
        try:
            PermissionService.check_admin_permissions(current_user, db)
            return True
        except HTTPException:
            return False

    @staticmethod
    def is_moderator(current_user: User, db: Session) -> bool:
        """Check if user is moderator (non-raising version)"""
        try:
            PermissionService.check_moderator_permissions(current_user, db)
            return True
        except HTTPException:
            return False

    # DOT-specific RBAC methods based on cursor rules
    @staticmethod
    def check_super_user_permissions(current_user: User, db: Session):
        """Check if current user has SUPER_USER permissions"""
        # First check if user is admin (admins have all permissions)
        try:
            PermissionService.check_admin_permissions(current_user, db)
            return True
        except HTTPException:
            pass

        # Check for SUPER_USER role
        super_user_role = db.query(Role).filter(Role.name == "SUPER_USER").first()
        if not super_user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SUPER_USER role not found"
            )

        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == super_user_role.id
        ).first()

        if not user_role:
            logger.warning(f"User {current_user.id} attempted unauthorized SUPER_USER action")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SUPER_USER access required"
            )

        return True

    @staticmethod
    def check_dot_user_permissions(current_user: User, db: Session, required_dot: str = None):
        """Check if current user has DOT_USER permissions for specific DOT"""
        # First check if user is admin or super_user (they have all access)
        try:
            PermissionService.check_admin_permissions(current_user, db)
            return True
        except HTTPException:
            pass

        try:
            PermissionService.check_super_user_permissions(current_user, db)
            return True
        except HTTPException:
            pass

        # Check for DOT_USER role
        dot_user_role = db.query(Role).filter(Role.name == "DOT_USER").first()
        if not dot_user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="DOT_USER role not found"
            )

        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == dot_user_role.id
        ).first()

        if not user_role:
            logger.warning(f"User {current_user.id} attempted unauthorized DOT_USER action")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="DOT_USER access required"
            )

        # If specific DOT is required, check if user belongs to that DOT
        if required_dot:
            user_dot = getattr(current_user, 'dot_region', None) or getattr(current_user, 'organization', None)
            if user_dot != required_dot:
                logger.warning(f"DOT_USER {current_user.id} attempted access to {required_dot}, but belongs to {user_dot}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: User does not belong to {required_dot}"
                )

        return True

    @staticmethod
    def get_user_dot_region(current_user: User, db: Session) -> str:
        """Get the DOT region for a DOT_USER"""
        # Admins and super users can access all DOTs
        if PermissionService.is_admin(current_user, db) or PermissionService.is_super_user(current_user, db):
            return None  # No restriction

        # For DOT_USER, return their specific DOT region
        return getattr(current_user, 'dot_region', None) or getattr(current_user, 'organization', None)

    @staticmethod
    def is_super_user(current_user: User, db: Session) -> bool:
        """Check if user is SUPER_USER (non-raising version)"""
        try:
            PermissionService.check_super_user_permissions(current_user, db)
            return True
        except HTTPException:
            return False

    @staticmethod
    def is_dot_user(current_user: User, db: Session) -> bool:
        """Check if user is DOT_USER (non-raising version)"""
        try:
            PermissionService.check_dot_user_permissions(current_user, db)
            return True
        except HTTPException:
            return False

    @staticmethod
    def require_admin_or_super_user(current_user: User, db: Session):
        """Require ADMIN or SUPER_USER role"""
        if not (PermissionService.is_admin(current_user, db) or PermissionService.is_super_user(current_user, db)):
            logger.warning(f"User {current_user.id} lacks ADMIN or SUPER_USER access")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ADMIN or SUPER_USER access required"
            )

    @staticmethod
    def require_upload_access(current_user: User, db: Session):
        """Require upload access (ADMIN only per cursor rules)"""
        PermissionService.check_admin_permissions(current_user, db)