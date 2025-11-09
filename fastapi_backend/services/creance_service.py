"""
Créance Périodique DOT Service Layer
Provides data access methods with RBAC filtering for Créance Périodique DOT data
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging

from models.creance import (
    CreancePeriodiqueDot,
    CreanceAggregateView
)
from models.dot import DOT
from models.user import User
from services.permission_service import PermissionService

logger = logging.getLogger(__name__)


class CreanceService:
    """Service for accessing Créance Périodique DOT data with RBAC controls"""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Main Créance Périodique DOT Data Access
    # ========================================================================

    def get_creance_records(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 100,
        dot: Optional[str] = None,
        actel: Optional[str] = None,
        annee: Optional[str] = None,
        mois: Optional[str] = None,
        period_key: Optional[str] = None,
        produit: Optional[str] = None,
        cust_lev1: Optional[str] = None,
        cust_lev2: Optional[str] = None,
        cust_lev3: Optional[str] = None,
        file_upload_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[CreancePeriodiqueDot], int]:
        """
        Get créance records with RBAC filtering and pagination

        Args:
            current_user: Current authenticated user
            page: Page number (1-indexed)
            page_size: Records per page
            dot: Filter by DOT name
            actel: Filter by ACTEL
            annee: Filter by year
            mois: Filter by month
            period_key: Filter by period (YYYY-MM)
            produit: Filter by product
            cust_lev1: Filter by customer level 1
            cust_lev2: Filter by customer level 2
            cust_lev3: Filter by customer level 3
            file_upload_id: Filter by file upload
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (records list, total count)
        """
        # Build base query with RBAC filtering
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot),
            current_user
        )

        # Apply filters
        if dot:
            query = query.filter(
                CreancePeriodiqueDot.dot.ilike(f"%{dot}%")
            )

        if actel:
            query = query.filter(
                CreancePeriodiqueDot.actel.ilike(f"%{actel}%")
            )

        if annee:
            query = query.filter(CreancePeriodiqueDot.annee == annee)

        if mois:
            query = query.filter(CreancePeriodiqueDot.mois == mois)

        if period_key:
            query = query.filter(CreancePeriodiqueDot.period_key == period_key)

        if produit:
            query = query.filter(
                CreancePeriodiqueDot.produit.ilike(f"%{produit}%")
            )

        if cust_lev1:
            query = query.filter(
                CreancePeriodiqueDot.cust_lev1.ilike(f"%{cust_lev1}%")
            )

        if cust_lev2:
            query = query.filter(
                CreancePeriodiqueDot.cust_lev2.ilike(f"%{cust_lev2}%")
            )

        if cust_lev3:
            query = query.filter(
                CreancePeriodiqueDot.cust_lev3.ilike(f"%{cust_lev3}%")
            )

        if file_upload_id is not None:
            query = query.filter(CreancePeriodiqueDot.file_upload_id == file_upload_id)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(CreancePeriodiqueDot, sort_by, CreancePeriodiqueDot.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        offset = (page - 1) * page_size
        records = query.offset(offset).limit(page_size).all()

        return records, total

    def get_creance_by_id(
        self,
        record_id: int,
        current_user: User
    ) -> Optional[CreancePeriodiqueDot]:
        """Get single créance record by ID with RBAC check"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot),
            current_user
        )
        return query.filter(CreancePeriodiqueDot.id == record_id).first()

    # ========================================================================
    # Aggregate Views for Dashboard
    # ========================================================================

    def get_overview_stats(self, current_user: User) -> Dict[str, Any]:
        """
        Get overview statistics from pre-calculated aggregate views
        Returns global KPIs: Total Invoice Amounts, Total Créance, etc.
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(CreanceAggregateView),
            current_user
        )
        query = query.filter(CreanceAggregateView.view_type == "overview")

        overview = query.first()

        if overview:
            return {
                "total_invoice_amt_ht": float(overview.total_invoice_amt_ht or 0),
                "total_invoice_amt": float(overview.total_invoice_amt or 0),
                "total_open_amt": float(overview.total_open_amt or 0),
                "total_creance_ht": float(overview.total_creance_ht or 0),
                "total_creance_net": float(overview.total_creance_net or 0),
                "total_creance_brut": float(overview.total_creance_brut or 0),
                "total_avoir_amt": float(overview.total_avoir_amt or 0),
                "nombre_lignes": overview.nombre_lignes or 0
            }
        else:
            # Fallback: Calculate on the fly if aggregate doesn't exist
            return self._calculate_overview_stats(current_user)

    def get_by_dot_aggregates(self, current_user: User) -> List[Dict[str, Any]]:
        """
        Get DOT-level aggregates from pre-calculated views
        Used for DOT histogram (DOT vs Créance NET)
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(CreanceAggregateView),
            current_user
        )
        query = query.filter(CreanceAggregateView.view_type == "by_dot")
        query = query.order_by(CreanceAggregateView.dot_name.asc())

        aggregates = query.all()

        return [
            {
                "dot": agg.dot_name,
                "total_invoice_amt_ht": float(agg.total_invoice_amt_ht or 0),
                "total_invoice_amt": float(agg.total_invoice_amt or 0),
                "total_creance_net": float(agg.total_creance_net or 0),
                "total_creance_brut": float(agg.total_creance_brut or 0),
                "total_open_amt": float(agg.total_open_amt or 0),
                "nombre_lignes": agg.nombre_lignes or 0
            }
            for agg in aggregates
        ]

    def get_by_annee_aggregates(self, current_user: User) -> List[Dict[str, Any]]:
        """
        Get year-level aggregates from pre-calculated views
        Used for Year histogram (Year vs Créance NET)
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(CreanceAggregateView),
            current_user
        )
        query = query.filter(CreanceAggregateView.view_type == "by_annee")
        query = query.order_by(CreanceAggregateView.annee.asc())

        aggregates = query.all()

        return [
            {
                "annee": agg.annee,
                "total_invoice_amt_ht": float(agg.total_invoice_amt_ht or 0),
                "total_invoice_amt": float(agg.total_invoice_amt or 0),
                "total_creance_net": float(agg.total_creance_net or 0),
                "total_creance_brut": float(agg.total_creance_brut or 0),
                "total_open_amt": float(agg.total_open_amt or 0),
                "nombre_lignes": agg.nombre_lignes or 0
            }
            for agg in aggregates
        ]

    def get_by_produit_aggregates(self, current_user: User) -> List[Dict[str, Any]]:
        """
        Get product-level aggregates from pre-calculated views
        Used for Product histogram (Product vs Créance NET)
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(CreanceAggregateView),
            current_user
        )
        query = query.filter(CreanceAggregateView.view_type == "by_produit")
        query = query.order_by(CreanceAggregateView.produit.asc())

        aggregates = query.all()

        return [
            {
                "produit": agg.produit,
                "total_invoice_amt_ht": float(agg.total_invoice_amt_ht or 0),
                "total_invoice_amt": float(agg.total_invoice_amt or 0),
                "total_creance_net": float(agg.total_creance_net or 0),
                "total_creance_brut": float(agg.total_creance_brut or 0),
                "total_open_amt": float(agg.total_open_amt or 0),
                "nombre_lignes": agg.nombre_lignes or 0
            }
            for agg in aggregates
        ]

    def get_by_cust_lev2_aggregates(self, current_user: User) -> List[Dict[str, Any]]:
        """
        Get customer level 2 aggregates from pre-calculated views
        Used for Customer Level 2 histogram (CUST_LEV2 vs Créance NET)
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(CreanceAggregateView),
            current_user
        )
        query = query.filter(CreanceAggregateView.view_type == "by_cust_lev2")
        query = query.order_by(CreanceAggregateView.cust_lev2.asc())

        aggregates = query.all()

        return [
            {
                "cust_lev2": agg.cust_lev2,
                "total_invoice_amt_ht": float(agg.total_invoice_amt_ht or 0),
                "total_invoice_amt": float(agg.total_invoice_amt or 0),
                "total_creance_net": float(agg.total_creance_net or 0),
                "total_creance_brut": float(agg.total_creance_brut or 0),
                "total_open_amt": float(agg.total_open_amt or 0),
                "nombre_lignes": agg.nombre_lignes or 0
            }
            for agg in aggregates
        ]

    # ========================================================================
    # Export and Reporting
    # ========================================================================

    def get_records_for_export(
        self,
        current_user: User,
        dot: Optional[str] = None,
        annee: Optional[str] = None,
        period_key: Optional[str] = None,
        produit: Optional[str] = None,
        cust_lev2: Optional[str] = None
    ) -> List[CreancePeriodiqueDot]:
        """
        Get all records for export (CSV/Excel) with RBAC filtering
        No pagination - returns all matching records
        """
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot),
            current_user
        )

        # Apply filters
        if dot:
            query = query.filter(
                CreancePeriodiqueDot.dot.ilike(f"%{dot}%")
            )

        if annee:
            query = query.filter(CreancePeriodiqueDot.annee == annee)

        if period_key:
            query = query.filter(CreancePeriodiqueDot.period_key == period_key)

        if produit:
            query = query.filter(
                CreancePeriodiqueDot.produit.ilike(f"%{produit}%")
            )

        if cust_lev2:
            query = query.filter(
                CreancePeriodiqueDot.cust_lev2.ilike(f"%{cust_lev2}%")
            )

        # Sort by DOT, year, month
        query = query.order_by(
            CreancePeriodiqueDot.dot.asc(),
            CreancePeriodiqueDot.annee.desc(),
            CreancePeriodiqueDot.mois.asc()
        )

        return query.all()

    # ========================================================================
    # Statistics and Analytics
    # ========================================================================

    def get_statistics_by_dot(
        self,
        current_user: User,
        dot: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed statistics by DOT"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot),
            current_user
        )

        if dot:
            query = query.filter(
                CreancePeriodiqueDot.dot.ilike(f"%{dot}%")
            )

        # Aggregate statistics
        stats = query.with_entities(
            func.count(CreancePeriodiqueDot.id).label('total_lignes'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt')
        ).first()

        return {
            "total_lignes": stats.total_lignes or 0,
            "total_invoice_amt_ht": float(stats.total_invoice_amt_ht or 0),
            "total_invoice_amt": float(stats.total_invoice_amt or 0),
            "total_creance_net": float(stats.total_creance_net or 0),
            "total_creance_brut": float(stats.total_creance_brut or 0),
            "total_open_amt": float(stats.total_open_amt or 0)
        }

    def get_available_periods(self, current_user: User) -> List[str]:
        """Get list of available periods (YYYY-MM) with data"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot.period_key).distinct(),
            current_user
        )
        query = query.filter(CreancePeriodiqueDot.period_key.isnot(None))
        query = query.order_by(CreancePeriodiqueDot.period_key.desc())

        return [row[0] for row in query.all()]

    def get_available_years(self, current_user: User) -> List[str]:
        """Get list of available years with data"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot.annee).distinct(),
            current_user
        )
        query = query.filter(CreancePeriodiqueDot.annee.isnot(None))
        query = query.order_by(CreancePeriodiqueDot.annee.desc())

        return [row[0] for row in query.all()]

    def get_available_dots(self, current_user: User) -> List[str]:
        """Get list of available DOTs with data"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot.dot).distinct(),
            current_user
        )
        query = query.filter(CreancePeriodiqueDot.dot.isnot(None))
        query = query.order_by(CreancePeriodiqueDot.dot.asc())

        return [row[0] for row in query.all()]

    def get_available_products(self, current_user: User) -> List[str]:
        """Get list of available products with data"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot.produit).distinct(),
            current_user
        )
        query = query.filter(CreancePeriodiqueDot.produit.isnot(None))
        query = query.order_by(CreancePeriodiqueDot.produit.asc())

        return [row[0] for row in query.all()]

    def get_available_cust_lev2(self, current_user: User) -> List[str]:
        """Get list of available customer level 2 values with data"""
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot.cust_lev2).distinct(),
            current_user
        )
        query = query.filter(CreancePeriodiqueDot.cust_lev2.isnot(None))
        query = query.order_by(CreancePeriodiqueDot.cust_lev2.asc())

        return [row[0] for row in query.all()]

    # ========================================================================
    # RBAC Helper Methods
    # ========================================================================

    def _apply_rbac_filter(self, query, current_user: User):
        """
        Apply RBAC filtering to CreancePeriodiqueDot query based on user's DOT access
        """
        # Check if user is admin or has global access
        if self._has_global_access(current_user):
            return query

        # Filter by user's DOT
        if current_user.dot_id:
            query = query.filter(CreancePeriodiqueDot.dot_id == current_user.dot_id)
        else:
            # User has no DOT assigned - return empty result
            query = query.filter(False)

        return query

    def _apply_rbac_filter_aggregates(self, query, current_user: User):
        """Apply RBAC filtering to CreanceAggregateView query"""
        if self._has_global_access(current_user):
            return query

        if current_user.dot_id:
            query = query.filter(CreanceAggregateView.dot_id == current_user.dot_id)
        else:
            query = query.filter(False)

        return query

    def _has_global_access(self, user: User) -> bool:
        """
        Check if user has global access (admin, super_admin, or specific permission)
        """
        if not user:
            return False

        # Check if user has admin role
        if hasattr(user, 'role') and user.role in ['admin', 'super_admin']:
            return True

        # Check for global view permission
        try:
            if PermissionService.has_permission(user, self.db, "can_view_all_dots"):
                return True
        except:
            pass

        return False

    def _calculate_overview_stats(self, current_user: User) -> Dict[str, Any]:
        """
        Fallback method to calculate overview stats on the fly
        Used when aggregate views are not available
        """
        query = self._apply_rbac_filter(
            self.db.query(CreancePeriodiqueDot),
            current_user
        )

        stats = query.with_entities(
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes'),
            func.sum(CreancePeriodiqueDot.invoice_amt_ht).label('total_invoice_amt_ht'),
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.creance_ht).label('total_creance_ht'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.avoir_amt).label('total_avoir_amt')
        ).first()

        return {
            "total_invoice_amt_ht": float(stats.total_invoice_amt_ht or 0),
            "total_invoice_amt": float(stats.total_invoice_amt or 0),
            "total_open_amt": float(stats.total_open_amt or 0),
            "total_creance_ht": float(stats.total_creance_ht or 0),
            "total_creance_net": float(stats.total_creance_net or 0),
            "total_creance_brut": float(stats.total_creance_brut or 0),
            "total_avoir_amt": float(stats.total_avoir_amt or 0),
            "nombre_lignes": stats.nombre_lignes or 0
        }
