from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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
    def get_or_create_dot(db: Session, name: str, description: Optional[str] = None, module: Optional[str] = None) -> DOT:
        """Get existing DOT or create new one if it doesn't exist

        Args:
            db: Database session
            name: DOT name
            description: Optional description
            module: Optional module name. If provided, DOT will be module-specific.
                   This allows having separate DOTs per module (e.g., "Alger" for each module).

        Handles race conditions where multiple threads try to create the same DOT simultaneously.
        """
        from sqlalchemy.exc import IntegrityError
        import math

        # Validate and normalize the name
        if not name or (isinstance(name, float) and math.isnan(name)):
            raise ValueError("DOT name cannot be empty or NaN")

        normalized_name = str(name).strip()

        # Remove "DOT" prefix (case-insensitive) if present
        import re
        normalized_name = re.sub(r'^DOT\s+', '', normalized_name, flags=re.IGNORECASE).strip()

        # Additional validation
        if not normalized_name or normalized_name.lower() in ['nan', 'none', 'null', '']:
            raise ValueError(f"Invalid DOT name: '{name}'")

        # Try to find existing DOT by name and module (case-insensitive)
        # Module-aware lookup: same name can exist in different modules
        query = db.query(DOT).filter(
            or_(
                DOT.name.ilike(normalized_name),
                DOT.name.ilike(f"DOT {normalized_name}"),
                DOT.name.ilike(f"DOT_{normalized_name}")
            )
        )

        # Filter by module if provided
        if module:
            query = query.filter(DOT.module == module)
        else:
            # If no module specified, look for DOTs without a module
            query = query.filter(DOT.module.is_(None))

        existing_dot = query.first()
        
        # If found an existing DOT with prefix, normalize it
        if existing_dot and re.match(r'^DOT\s+', existing_dot.name, re.IGNORECASE):
            if existing_dot.name != normalized_name:
                existing_dot.name = normalized_name
                db.commit()
                db.refresh(existing_dot)
                logger.info(f"Normalized existing DOT name: '{existing_dot.name}' → '{normalized_name}'")

        if existing_dot:
            logger.debug(
                f"Found existing DOT: {existing_dot.name} (ID: {existing_dot.id})")
            return existing_dot

        # Create new DOT if not found
        try:
            new_dot = DOT(
                name=normalized_name,
                module=module,
                description=description or f"Auto-created DOT for region: {name}" + (f" (Module: {module})" if module else "")
            )
            db.add(new_dot)
            db.commit()
            db.refresh(new_dot)

            module_info = f" for module '{module}'" if module else ""
            logger.info(f"Created new DOT: {new_dot.name}{module_info} (ID: {new_dot.id})")
            return new_dot

        except IntegrityError as e:
            # Race condition: another thread created the DOT between our check and insert
            db.rollback()

            # Retry the query to get the DOT that was created by the other thread
            retry_query = db.query(DOT).filter(DOT.name.ilike(normalized_name))
            if module:
                retry_query = retry_query.filter(DOT.module == module)
            else:
                retry_query = retry_query.filter(DOT.module.is_(None))

            existing_dot = retry_query.first()
            
            if existing_dot:
                logger.debug(
                    f"Race condition resolved: Found DOT created by another thread: {existing_dot.name} (ID: {existing_dot.id})")
                return existing_dot
            else:
                # This should never happen, but log and re-raise if it does
                logger.error(
                    f"Race condition error but DOT still not found for '{normalized_name}': {str(e)}")
                raise
                
        except Exception as e:
            logger.error(
                f"Unexpected error in get_or_create_dot for name '{normalized_name}': {str(e)}")
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
    def list_dots_paginated(db: Session, page: int = 1, page_size: int = 25,
                            search: Optional[str] = None, module: Optional[str] = None) -> tuple[List[DOT], int]:
        """List DOTs with pagination, search, and module filter support"""
        query = db.query(DOT)

        # Apply search filter if provided
        if search:
            search_filter = DOT.name.ilike(f"%{search}%")
            query = query.filter(search_filter)

        # Apply module filter if provided
        if module:
            query = query.filter(DOT.module == module)

        # Get total count
        total = query.count()

        # Apply pagination
        skip = (page - 1) * page_size
        dots = query.order_by(DOT.module, DOT.name).offset(skip).limit(page_size).all()

        return dots, total

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
    def delete_dot(db: Session, dot_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Delete DOT and optionally all related records

        Args:
            db: Database session
            dot_id: ID of DOT to delete
            force: If True, deletes DOT with ALL related records (CASCADE DELETE)
                   If False, checks for related records and blocks deletion

        Returns:
            Dictionary with deletion statistics
        """
        try:
            dot = db.query(DOT).filter(DOT.id == dot_id).first()
            if not dot:
                return {"success": False, "error": "DOT not found"}

            # Count related records
            from models.user import User
            from models.park import Park
            from models.revenue import RevenueJournal, RevenueObjective, RevenueDOTCorporate
            from models.encaissement import EncaissementARDot, EncaissementAnomaly
            from models.creance import CreancePeriodiqueDot

            # Store DOT name separately
            dot_name = dot.name

            # Count related records (only numeric values)
            stats = {
                "users": db.query(User).filter(User.dot_id == dot_id).count(),
                "parks": db.query(Park).filter(Park.dot_id == dot_id).count(),
                "revenue_journals": db.query(RevenueJournal).filter(RevenueJournal.dot_id == dot_id).count(),
                "revenue_objectives": db.query(RevenueObjective).filter(RevenueObjective.dot_id == dot_id).count(),
                "monthly_objectives": db.query(RevenueDOTCorporate).filter(RevenueDOTCorporate.dot_id == dot_id).count(),
                "encaissement_records": db.query(EncaissementARDot).filter(EncaissementARDot.dot_id == dot_id).count(),
                "encaissement_anomalies": db.query(EncaissementAnomaly).filter(EncaissementAnomaly.dot_id == dot_id).count(),
                "creance_records": db.query(CreancePeriodiqueDot).filter(CreancePeriodiqueDot.dot_id == dot_id).count(),
            }

            total_records = sum(stats.values())

            # If force=False and records exist, block deletion
            if not force and total_records > 0:
                raise ValueError(
                    f"Cannot delete DOT '{dot_name}' - {total_records} related records exist. "
                    f"Use force=True to delete DOT with all related data. "
                    f"Records: {stats}"
                )

            # CASCADE DELETE: SQLAlchemy will automatically delete all related records
            # due to cascade="all, delete-orphan" in DOT model relationships
            logger.warning(f"🗑️  CASCADE DELETE: Deleting DOT '{dot_name}' (ID: {dot_id}) with {total_records} related records")
            logger.warning(f"   Breakdown: {stats}")

            db.delete(dot)
            db.commit()

            logger.info(f"✅ Deleted DOT: {dot_name} (ID: {dot_id}) and {total_records} related records")

            return {
                "success": True,
                "dot_id": dot_id,
                "dot_name": dot_name,
                "deleted_records": stats,
                "total_deleted": total_records
            }

        except Exception as e:
            logger.error(f"❌ Error deleting DOT {dot_id}: {str(e)}")
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
    def get_user_accessible_dots(db: Session, user_id: int, module: Optional[str] = None) -> List[int]:
        """Get list of DOT IDs that a user can access

        NEW BEHAVIOR: When module is specified, returns only DOTs that belong to that module.
        This allows each module to have its own set of DOTs (e.g., 4 "Alger" DOTs - one per module).

        Priority order for DOT resolution:
        1. If module specified: User-specific module DOT (UserModuleDOT) within that module's DOTs
        2. If module specified: User's global dot_id (accepts both module-specific and global DOTs)
        3. If module specified: Module default DOT (ModuleDOTConfig)
        4. If no module: User's global dot_id
        5. All DOTs within module (for superusers/staff)

        Args:
            db: Database session
            user_id: User ID
            module: Optional module name (e.g., 'parc_corporate_ngbss', 'chiffre_affaires')
                    If provided, only returns DOTs that belong to this module OR global DOTs (module=NULL)

        Returns:
            List of DOT IDs the user can access
        """
        try:
            from models.user import User
            from models.user_module_dot import UserModuleDOT
            from models.module_dot_config import ModuleDOTConfig

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []

            # Superusers and staff have access to all DOTs (within module if specified)
            if user.is_superuser or user.is_staff:
                query = db.query(DOT.id)
                if module:
                    # Include both module-specific DOTs AND global DOTs (module=NULL)
                    query = query.filter(
                        or_(DOT.module == module, DOT.module.is_(None))
                    )
                all_dots = query.all()
                return [dot.id for dot in all_dots]

            # If module is specified, only return DOTs from that module
            if module:
                # Priority 1: User-specific module DOT assignment
                module_dot = db.query(UserModuleDOT).filter(
                    UserModuleDOT.user_id == user_id,
                    UserModuleDOT.module == module
                ).first()

                if module_dot:
                    # Verify the DOT exists and belongs to this module OR is global
                    dot = db.query(DOT).filter(
                        DOT.id == module_dot.dot_id,
                        or_(DOT.module == module, DOT.module.is_(None))
                    ).first()

                    if dot:
                        logger.debug(
                            f"Using user-specific module DOT for user {user_id}, module '{module}': DOT {module_dot.dot_id}")
                        return [module_dot.dot_id]

                # Priority 2: Check if user's global DOT belongs to this module OR is a global DOT
                if user.dot_id:
                    dot = db.query(DOT).filter(
                        DOT.id == user.dot_id,
                        or_(DOT.module == module, DOT.module.is_(None))
                    ).first()

                    if dot:
                        logger.debug(
                            f"Using global DOT for user {user_id}, module '{module}': DOT {user.dot_id} (module: {dot.module or 'NULL'})")
                        return [user.dot_id]

                # Priority 3: Check for module-level default DOT
                module_config = db.query(ModuleDOTConfig).filter(
                    ModuleDOTConfig.module == module
                ).first()

                if module_config:
                    logger.debug(
                        f"Using module default DOT for user {user_id}, module '{module}': DOT {module_config.dot_id}")
                    return [module_config.dot_id]

                # No accessible DOT found for this module
                logger.warning(
                    f"User {user_id} has no accessible DOT for module '{module}'")
                return []

            # No module specified - fall back to global DOT assignment
            if user.dot_id:
                logger.debug(
                    f"Using global DOT for user {user_id}: DOT {user.dot_id}")
                return [user.dot_id]

            return []

        except Exception as e:
            logger.error(
                f"Error getting accessible DOTs for user {user_id}, module {module}: {str(e)}")
            return []

    @staticmethod
    def assign_user_to_module_dot(db: Session, user_id: int, module: str, dot_id: int) -> bool:
        """Assign a user to a specific DOT for a module"""
        try:
            from models.user import User
            from models.user_module_dot import UserModuleDOT, ALL_MODULES

            # Validate module
            if module not in ALL_MODULES:
                raise ValueError(f"Invalid module: {module}. Must be one of {ALL_MODULES}")

            # Verify DOT exists
            dot = db.query(DOT).filter(DOT.id == dot_id).first()
            if not dot:
                raise ValueError(f"DOT with ID {dot_id} not found")

            # Verify user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            # Check if assignment already exists
            existing = db.query(UserModuleDOT).filter(
                UserModuleDOT.user_id == user_id,
                UserModuleDOT.module == module
            ).first()

            if existing:
                # Update existing assignment
                existing.dot_id = dot_id
                logger.info(
                    f"Updated module DOT assignment: user {user.username} (ID: {user_id}) "
                    f"for module '{module}' to DOT {dot.name} (ID: {dot_id})")
            else:
                # Create new assignment
                module_dot = UserModuleDOT(
                    user_id=user_id,
                    module=module,
                    dot_id=dot_id
                )
                db.add(module_dot)
                logger.info(
                    f"Assigned user {user.username} (ID: {user_id}) to DOT {dot.name} (ID: {dot_id}) "
                    f"for module '{module}'")

            db.commit()
            return True

        except Exception as e:
            logger.error(
                f"Error assigning user {user_id} to DOT {dot_id} for module {module}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def unassign_user_from_module_dot(db: Session, user_id: int, module: str) -> bool:
        """Remove user's module-specific DOT assignment"""
        try:
            from models.user import User
            from models.user_module_dot import UserModuleDOT

            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            module_dot = db.query(UserModuleDOT).filter(
                UserModuleDOT.user_id == user_id,
                UserModuleDOT.module == module
            ).first()

            if module_dot:
                db.delete(module_dot)
                db.commit()
                logger.info(
                    f"Removed module DOT assignment for user {user.username} (ID: {user_id}) "
                    f"from module '{module}'")
                return True
            else:
                logger.warning(
                    f"No module DOT assignment found for user {user_id} in module '{module}'")
                return False

        except Exception as e:
            logger.error(
                f"Error removing module DOT assignment for user {user_id}, module {module}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_user_module_dots(db: Session, user_id: int) -> Dict[str, int]:
        """Get all module-specific DOT assignments for a user
        
        Returns:
            Dictionary mapping module names to DOT IDs
        """
        try:
            from models.user_module_dot import UserModuleDOT

            module_dots = db.query(UserModuleDOT).filter(
                UserModuleDOT.user_id == user_id
            ).all()

            return {md.module: md.dot_id for md in module_dots}

        except Exception as e:
            logger.error(
                f"Error getting module DOTs for user {user_id}: {str(e)}")
            return {}
