from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from models.dot import DOT
from models.user import DOTInfo

logger = logging.getLogger(__name__)
# Set to INFO level to suppress DEBUG logs during bulk processing
logger.setLevel(logging.INFO)


class DOTService:
    """Centralized service for DOT operations and business logic"""

    @staticmethod
    def get_or_create_dot(db: Session, name: str, description: Optional[str] = None) -> DOT:
        """Get existing DOT or create new one if it doesn't exist"""
        try:
            # Try to find existing DOT by name (case-insensitive)
            existing_dot = db.query(DOT).filter(
                DOT.name.ilike(name.strip())
            ).first()

            if existing_dot:
                logger.debug(
                    f"Found existing DOT: {existing_dot.name} (ID: {existing_dot.id})")
                return existing_dot

            # Create new DOT if not found
            new_dot = DOT(
                name=name.strip(),
                description=description or f"Auto-created DOT for region: {name}"
            )
            db.add(new_dot)
            db.commit()
            db.refresh(new_dot)

            logger.info(f"Created new DOT: {new_dot.name} (ID: {new_dot.id})")
            return new_dot

        except Exception as e:
            logger.error(
                f"Error in get_or_create_dot for name '{name}': {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_dot_by_id(db: Session, dot_id: int) -> Optional[DOT]:
        """Get DOT by ID"""
        return db.query(DOT).filter(DOT.id == dot_id).first()

    @staticmethod
    def get_dot_by_name(db: Session, name: str) -> Optional[DOT]:
        """Get DOT by name (case-insensitive)"""
        return db.query(DOT).filter(DOT.name.ilike(name.strip())).first()

    @staticmethod
    def list_dots(db: Session, skip: int = 0, limit: int = 100) -> List[DOT]:
        """List all DOTs with pagination"""
        return db.query(DOT).offset(skip).limit(limit).all()

    @staticmethod
    def update_dot(db: Session, dot_id: int, name: Optional[str] = None,
                   description: Optional[str] = None) -> Optional[DOT]:
        """Update DOT information"""
        try:
            dot = db.query(DOT).filter(DOT.id == dot_id).first()
            if not dot:
                return None

            if name is not None:
                # Check if new name conflicts with existing DOT
                existing_dot = db.query(DOT).filter(
                    DOT.name.ilike(name.strip()),
                    DOT.id != dot_id
                ).first()
                if existing_dot:
                    raise ValueError(f"DOT with name '{name}' already exists")
                dot.name = name.strip()

            if description is not None:
                dot.description = description

            db.commit()
            db.refresh(dot)

            logger.info(f"Updated DOT: {dot.name} (ID: {dot.id})")
            return dot

        except Exception as e:
            logger.error(f"Error updating DOT {dot_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def delete_dot(db: Session, dot_id: int) -> bool:
        """Delete DOT if no users are assigned to it"""
        try:
            dot = db.query(DOT).filter(DOT.id == dot_id).first()
            if not dot:
                return False

            # Check if any users are assigned to this DOT
            from models.user import User
            user_count = db.query(User).filter(User.dot_id == dot_id).count()
            if user_count > 0:
                raise ValueError(
                    f"Cannot delete DOT '{dot.name}' - {user_count} users are assigned to it")

            # Check if any parks are assigned to this DOT
            try:
                from models.park import Park
                park_count = db.query(Park).filter(
                    Park.dot_id == dot_id).count()
                if park_count > 0:
                    raise ValueError(
                        f"Cannot delete DOT '{dot.name}' - {park_count} parks are assigned to it")
            except ImportError:
                # Park model might not exist in all deployments
                pass

            db.delete(dot)
            db.commit()

            logger.info(f"Deleted DOT: {dot.name} (ID: {dot_id})")
            return True

        except Exception as e:
            logger.error(f"Error deleting DOT {dot_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_users_in_dot(db: Session, dot_id: int, skip: int = 0, limit: int = 100) -> List:
        """Get all users assigned to a specific DOT"""
        from models.user import User
        return db.query(User).filter(
            User.dot_id == dot_id,
            User.is_active == True
        ).offset(skip).limit(limit).all()

    @staticmethod
    def assign_user_to_dot(db: Session, user_id: int, dot_id: int) -> bool:
        """Assign a user to a DOT"""
        try:
            from models.user import User

            # Verify DOT exists
            dot = db.query(DOT).filter(DOT.id == dot_id).first()
            if not dot:
                raise ValueError(f"DOT with ID {dot_id} not found")

            # Update user's DOT assignment
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.dot_id = dot_id
            db.commit()

            logger.info(
                f"Assigned user {user.username} (ID: {user_id}) to DOT {dot.name} (ID: {dot_id})")
            return True

        except Exception as e:
            logger.error(
                f"Error assigning user {user_id} to DOT {dot_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def unassign_user_from_dot(db: Session, user_id: int) -> bool:
        """Remove user's DOT assignment"""
        try:
            from models.user import User

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            old_dot_id = user.dot_id
            user.dot_id = None
            db.commit()

            logger.info(
                f"Removed DOT assignment for user {user.username} (ID: {user_id}) from DOT ID: {old_dot_id}")
            return True

        except Exception as e:
            logger.error(
                f"Error removing DOT assignment for user {user_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_dot_statistics(db: Session, dot_id: int) -> Dict[str, Any]:
        """Get statistics for a specific DOT"""
        try:
            from models.user import User

            dot = db.query(DOT).filter(DOT.id == dot_id).first()
            if not dot:
                raise ValueError(f"DOT with ID {dot_id} not found")

            # Count users
            user_count = db.query(User).filter(
                User.dot_id == dot_id,
                User.is_active == True
            ).count()

            # Count parks (if Park model exists)
            park_count = 0
            try:
                from models.park import Park
                park_count = db.query(Park).filter(
                    Park.dot_id == dot_id).count()
            except ImportError:
                pass

            return {
                "dot_id": dot_id,
                "dot_name": dot.name,
                "description": dot.description,
                "active_users": user_count,
                "parks": park_count,
                "created_at": dot.created_at,
                "updated_at": dot.updated_at
            }

        except Exception as e:
            logger.error(
                f"Error getting statistics for DOT {dot_id}: {str(e)}")
            raise

    @staticmethod
    def validate_dot_access(db: Session, user_id: int, target_dot_id: int) -> bool:
        """Validate if user has access to data from a specific DOT"""
        try:
            from models.user import User

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            # Superusers and staff have access to all DOTs
            if user.is_superuser or user.is_staff:
                return True

            # Regular users can only access data from their assigned DOT
            return user.dot_id == target_dot_id

        except Exception as e:
            logger.error(
                f"Error validating DOT access for user {user_id}, DOT {target_dot_id}: {str(e)}")
            return False

    @staticmethod
    def get_user_accessible_dots(db: Session, user_id: int) -> List[int]:
        """Get list of DOT IDs that a user can access"""
        try:
            from models.user import User

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []

            # Superusers and staff have access to all DOTs
            if user.is_superuser or user.is_staff:
                all_dots = db.query(DOT.id).all()
                return [dot.id for dot in all_dots]

            # Regular users can only access their assigned DOT
            if user.dot_id:
                return [user.dot_id]

            return []

        except Exception as e:
            logger.error(
                f"Error getting accessible DOTs for user {user_id}: {str(e)}")
            return []
