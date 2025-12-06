"""
Encaissement AR DOT Service Layer
Provides data access methods with RBAC filtering for Encaissement AR DOT data
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging

from models.encaissement import (
    EncaissementARDot,
    EncaissementAnomaly,
    EncaissementAggregateView
)
from models.dot import DOT
from models.user import User
from models.user_module_dot import MODULE_ENCAISSEMENT_AR_DOT
from services.permission_service import PermissionService
from services.dot_service import DOTService

logger = logging.getLogger(__name__)


class EncaissementService:
    """Service for accessing Encaissement AR DOT data with RBAC controls"""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Main Encaissement AR DOT Data Access
    # ========================================================================

    def get_encaissement_records(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 100,
        organisation: Optional[str] = None,
        mois: Optional[str] = None,
        n_fact: Optional[int] = None,
        typ_fact: Optional[str] = None,
        date_fact_from: Optional[date] = None,
        date_fact_to: Optional[date] = None,
        is_duplicate: Optional[bool] = None,
        is_anomaly: Optional[bool] = None,
        file_upload_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[EncaissementARDot], int]:
        """
        Get encaissement records with RBAC filtering and pagination

        Args:
            current_user: Current authenticated user
            page: Page number (1-indexed)
            page_size: Records per page
            organisation: Filter by organisation name
            mois: Filter by month (YYYY-MM)
            n_fact: Filter by invoice number
            typ_fact: Filter by invoice type
            date_fact_from: Filter by invoice date from
            date_fact_to: Filter by invoice date to
            is_duplicate: Filter duplicates
            is_anomaly: Filter anomalies
            file_upload_id: Filter by file upload
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (records list, total count)
        """
        # Build base query with RBAC filtering
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot),
            current_user
        )

        # Apply filters
        if organisation:
            query = query.filter(
                EncaissementARDot.organisation.ilike(f"%{organisation}%")
            )

        if mois:
            query = query.filter(EncaissementARDot.mois == mois)

        if n_fact is not None:
            query = query.filter(EncaissementARDot.n_fact == n_fact)

        if typ_fact:
            query = query.filter(EncaissementARDot.typ_fact == typ_fact)

        if date_fact_from:
            query = query.filter(EncaissementARDot.date_fact >= date_fact_from)

        if date_fact_to:
            query = query.filter(EncaissementARDot.date_fact <= date_fact_to)

        if is_duplicate is not None:
            query = query.filter(EncaissementARDot.is_duplicate == is_duplicate)

        if is_anomaly is not None:
            query = query.filter(EncaissementARDot.is_anomaly == is_anomaly)

        if file_upload_id is not None:
            query = query.filter(EncaissementARDot.file_upload_id == file_upload_id)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(EncaissementARDot, sort_by, EncaissementARDot.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        offset = (page - 1) * page_size
        records = query.offset(offset).limit(page_size).all()

        return records, total

    def get_encaissement_by_id(
        self,
        record_id: int,
        current_user: User
    ) -> Optional[EncaissementARDot]:
        """Get single encaissement record by ID with RBAC check"""
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot),
            current_user
        )
        return query.filter(EncaissementARDot.id == record_id).first()

    # ========================================================================
    # Anomaly Data Access
    # ========================================================================

    def get_anomalies(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 100,
        organisation: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        file_upload_id: Optional[int] = None
    ) -> Tuple[List[EncaissementAnomaly], int]:
        """Get encaissement anomalies with RBAC filtering"""
        # Build base query with RBAC filtering
        query = self._apply_rbac_filter_anomalies(
            self.db.query(EncaissementAnomaly),
            current_user
        )

        # Apply filters
        if organisation:
            query = query.filter(
                EncaissementAnomaly.organisation.ilike(f"%{organisation}%")
            )

        if anomaly_type:
            query = query.filter(EncaissementAnomaly.anomaly_type == anomaly_type)

        if file_upload_id is not None:
            query = query.filter(EncaissementAnomaly.file_upload_id == file_upload_id)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        records = query.order_by(EncaissementAnomaly.created_at.desc()).offset(offset).limit(page_size).all()

        return records, total

    def get_anomaly_statistics(self, current_user: User) -> Dict[str, Any]:
        """Get anomaly statistics with RBAC filtering"""
        query = self._apply_rbac_filter_anomalies(
            self.db.query(EncaissementAnomaly),
            current_user
        )

        total_anomalies = query.count()

        # Group by anomaly type
        by_type = self.db.query(
            EncaissementAnomaly.anomaly_type,
            func.count(EncaissementAnomaly.id).label('count')
        )
        by_type = self._apply_rbac_filter_anomalies(by_type, current_user)
        by_type = by_type.group_by(EncaissementAnomaly.anomaly_type).all()

        return {
            "total_anomalies": total_anomalies,
            "by_type": {item[0]: item[1] for item in by_type}
        }

    # ========================================================================
    # Aggregate Views for Dashboard
    # ========================================================================

    def get_overview_stats(self, current_user: User) -> Dict[str, Any]:
        """
        Get overview statistics from pre-calculated aggregate views
        Returns global KPIs: Total Montant TTC, Total Encaissement, Taux Encaissement
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(EncaissementAggregateView),
            current_user
        )
        query = query.filter(EncaissementAggregateView.view_type == "overview")

        overview = query.first()

        if overview:
            return {
                "total_montant_ttc": float(overview.total_montant_ttc or 0),
                "total_encaissement": float(overview.total_encaissement or 0),
                "total_montant_restant": float(overview.total_montant_restant or 0),
                "taux_encaissement": float(overview.taux_encaissement or 0),
                "nombre_factures": overview.nombre_factures or 0
            }
        else:
            # Fallback: Calculate on the fly if aggregate doesn't exist
            return self._calculate_overview_stats(current_user)

    def get_monthly_aggregates(
        self,
        current_user: User,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get monthly aggregates from pre-calculated views
        Used for combined bar chart (Montant TTC + Encaissement by month)
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(EncaissementAggregateView),
            current_user
        )
        query = query.filter(EncaissementAggregateView.view_type == "by_month")

        if year:
            query = query.filter(EncaissementAggregateView.mois.like(f"{year}-%"))

        query = query.order_by(EncaissementAggregateView.mois.asc())

        aggregates = query.all()

        return [
            {
                "mois": agg.mois,
                "total_montant_ttc": float(agg.total_montant_ttc or 0),
                "total_encaissement": float(agg.total_encaissement or 0),
                "total_montant_restant": float(agg.total_montant_restant or 0),
                "taux_encaissement": float(agg.taux_encaissement or 0),
                "nombre_factures": agg.nombre_factures or 0
            }
            for agg in aggregates
        ]

    def get_monthly_distribution(
        self,
        current_user: User,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get monthly distribution with percentages for pie chart
        Returns encaissement amount and percentage for each month
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(EncaissementAggregateView),
            current_user
        )
        query = query.filter(EncaissementAggregateView.view_type == "monthly_distribution")

        if year:
            query = query.filter(EncaissementAggregateView.mois.like(f"{year}-%"))

        query = query.order_by(EncaissementAggregateView.mois.asc())

        aggregates = query.all()

        return [
            {
                "mois": agg.mois,
                "total_encaissement": float(agg.total_encaissement or 0),
                "percentage": float(agg.percentage or 0)
            }
            for agg in aggregates
        ]

    def get_dot_aggregates(self, current_user: User) -> List[Dict[str, Any]]:
        """
        Get DOT-level aggregates from pre-calculated views
        Used for DOT and Taux d'encaissement bar chart
        """
        query = self._apply_rbac_filter_aggregates(
            self.db.query(EncaissementAggregateView),
            current_user
        )
        query = query.filter(EncaissementAggregateView.view_type == "by_dot")
        query = query.order_by(EncaissementAggregateView.organisation.asc())

        aggregates = query.all()

        return [
            {
                "organisation": agg.organisation,
                "total_montant_ttc": float(agg.total_montant_ttc or 0),
                "total_encaissement": float(agg.total_encaissement or 0),
                "total_montant_restant": float(agg.total_montant_restant or 0),
                "taux_encaissement": float(agg.taux_encaissement or 0),
                "nombre_factures": agg.nombre_factures or 0
            }
            for agg in aggregates
        ]

    # ========================================================================
    # Export and Reporting
    # ========================================================================

    def get_records_for_export(
        self,
        current_user: User,
        organisation: Optional[str] = None,
        mois: Optional[str] = None,
        date_fact_from: Optional[date] = None,
        date_fact_to: Optional[date] = None,
        include_duplicates: bool = True,
        include_anomalies: bool = True
    ) -> List[EncaissementARDot]:
        """
        Get all records for export (CSV/Excel) with RBAC filtering
        No pagination - returns all matching records
        """
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot),
            current_user
        )

        # Apply filters
        if organisation:
            query = query.filter(
                EncaissementARDot.organisation.ilike(f"%{organisation}%")
            )

        if mois:
            query = query.filter(EncaissementARDot.mois == mois)

        if date_fact_from:
            query = query.filter(EncaissementARDot.date_fact >= date_fact_from)

        if date_fact_to:
            query = query.filter(EncaissementARDot.date_fact <= date_fact_to)

        if not include_duplicates:
            query = query.filter(EncaissementARDot.is_duplicate == False)

        if not include_anomalies:
            query = query.filter(EncaissementARDot.is_anomaly == False)

        # Sort by organisation, typ_fact, n_fact (as per business rules)
        query = query.order_by(
            EncaissementARDot.organisation.asc(),
            EncaissementARDot.typ_fact.asc(),
            EncaissementARDot.n_fact.asc()
        )

        return query.all()

    # ========================================================================
    # Statistics and Analytics
    # ========================================================================

    def get_statistics_by_organisation(
        self,
        current_user: User,
        organisation: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed statistics by organisation"""
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot),
            current_user
        )

        if organisation:
            query = query.filter(
                EncaissementARDot.organisation.ilike(f"%{organisation}%")
            )

        # Aggregate statistics
        stats = query.with_entities(
            func.count(EncaissementARDot.id).label('total_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.sum(EncaissementARDot.montant_restant).label('total_montant_restant'),
            func.avg(EncaissementARDot.taux_encaissement).label('avg_taux')
        ).first()

        return {
            "total_factures": stats.total_factures or 0,
            "total_montant_ttc": float(stats.total_montant_ttc or 0),
            "total_encaissement": float(stats.total_encaissement or 0),
            "total_montant_restant": float(stats.total_montant_restant or 0),
            "average_taux_encaissement": float(stats.avg_taux or 0)
        }

    def get_available_months(self, current_user: User) -> List[str]:
        """Get list of available months with data"""
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot.mois).distinct(),
            current_user
        )
        query = query.filter(EncaissementARDot.mois.isnot(None))
        query = query.order_by(EncaissementARDot.mois.desc())

        return [row[0] for row in query.all()]

    def get_available_organisations(self, current_user: User) -> List[str]:
        """Get list of available organisations (DOTs) with data"""
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot.organisation).distinct(),
            current_user
        )
        query = query.filter(EncaissementARDot.organisation.isnot(None))
        query = query.order_by(EncaissementARDot.organisation.asc())

        return [row[0] for row in query.all()]

    # ========================================================================
    # RBAC Helper Methods
    # ========================================================================

    def _apply_rbac_filter(self, query, current_user: User):
        """
        Apply RBAC filtering to EncaissementARDot query based on user's DOT access
        Uses module-specific DOT assignments
        """
        # Check if user is admin or has global access
        if self._has_global_access(current_user):
            return query

        # Get module-specific accessible DOTs
        accessible_dots = DOTService.get_user_accessible_dots(
            self.db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        
        if accessible_dots:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dots))
        else:
            # User has no DOT assigned - return empty result
            query = query.filter(False)

        return query

    def _apply_rbac_filter_anomalies(self, query, current_user: User):
        """Apply RBAC filtering to EncaissementAnomaly query (module-specific)"""
        if self._has_global_access(current_user):
            return query

        accessible_dots = DOTService.get_user_accessible_dots(
            self.db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        
        if accessible_dots:
            query = query.filter(EncaissementAnomaly.dot_id.in_(accessible_dots))
        else:
            query = query.filter(False)

        return query

    def _apply_rbac_filter_aggregates(self, query, current_user: User):
        """Apply RBAC filtering to EncaissementAggregateView query (module-specific)"""
        if self._has_global_access(current_user):
            return query

        accessible_dots = DOTService.get_user_accessible_dots(
            self.db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        
        if accessible_dots:
            query = query.filter(EncaissementAggregateView.dot_id.in_(accessible_dots))
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
            self.db.query(EncaissementARDot),
            current_user
        )

        stats = query.with_entities(
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.sum(EncaissementARDot.montant_restant).label('total_montant_restant')
        ).first()

        total_montant_ttc = float(stats.total_montant_ttc or 0)
        total_encaissement = float(stats.total_encaissement or 0)

        taux_encaissement = 0.0
        if total_montant_ttc > 0:
            taux_encaissement = (total_encaissement / total_montant_ttc) * 100

        return {
            "total_montant_ttc": total_montant_ttc,
            "total_encaissement": total_encaissement,
            "total_montant_restant": float(stats.total_montant_restant or 0),
            "taux_encaissement": round(taux_encaissement, 2),
            "nombre_factures": stats.nombre_factures or 0
        }

    # ========================================================================
    # Duplicate Management
    # ========================================================================

    def get_duplicate_groups(
        self,
        current_user: User,
        composite_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get groups of duplicate records based on composite_key
        """
        query = self._apply_rbac_filter(
            self.db.query(EncaissementARDot),
            current_user
        )

        if composite_key:
            query = query.filter(EncaissementARDot.composite_key == composite_key)

        query = query.filter(EncaissementARDot.is_duplicate == True)
        query = query.order_by(
            EncaissementARDot.composite_key.asc(),
            EncaissementARDot.created_at.asc()
        )

        duplicates = query.all()

        # Group by composite_key
        grouped = {}
        for record in duplicates:
            key = record.composite_key
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(record)

        return [
            {
                "composite_key": key,
                "count": len(records),
                "records": records
            }
            for key, records in grouped.items()
        ]
