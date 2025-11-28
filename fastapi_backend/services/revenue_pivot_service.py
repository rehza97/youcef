"""
Revenue Pivot Service
Generates and maintains pre-calculated pivot tables (TCD)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from decimal import Decimal

from models.revenue import RevenueJournal, RevenueObjective
from models.revenue_pivot import RevenuePivotCache, RevenuePivotMetadata

logger = logging.getLogger(__name__)


class RevenuePivotService:
    """Service for generating and managing revenue pivot tables"""

    def __init__(self, db: Session):
        self.db = db

    def generate_all_pivots(self, file_upload_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate all pivot tables (TCD)
        Called after revenue journal data is loaded
        """
        logger.info("🔄 Starting pivot table generation...")
        start_time = datetime.utcnow()

        results = {
            "overview": self._generate_overview_pivot(file_upload_id),
            "by_org": self._generate_by_org_pivot(file_upload_id),
            "by_month": self._generate_by_month_pivot(file_upload_id),
            "by_account": self._generate_by_account_pivot(file_upload_id),
            "by_org_month": self._generate_by_org_month_pivot(file_upload_id),
        }

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Pivot table generation completed in {duration:.2f}s")

        return results

    def _generate_overview_pivot(self, file_upload_id: Optional[int] = None) -> int:
        """Generate global overview pivot"""
        logger.info("📊 Generating overview pivot...")

        # Clear existing overview pivots
        self.db.query(RevenuePivotCache).filter(
            RevenuePivotCache.pivot_type == "overview"
        ).delete()

        # Calculate global metrics
        query = self.db.query(
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label("total_revenue"),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label("total_revenue_ttc"),
            func.avg(RevenueJournal.taux_realisation_ca).label("avg_achievement_rate"),
            func.count(RevenueJournal.id).label("record_count"),
            func.min(RevenueJournal.chiffre_aff_exe_dzd).label("min_revenue"),
            func.max(RevenueJournal.chiffre_aff_exe_dzd).label("max_revenue"),
        )

        if file_upload_id:
            query = query.filter(RevenueJournal.file_upload_id == file_upload_id)

        result = query.first()

        # Get total objective
        total_objective = self.db.query(
            func.sum(RevenueObjective.objectif_ca)
        ).scalar() or 0

        # Create pivot record
        pivot = RevenuePivotCache(
            file_upload_id=file_upload_id,
            pivot_type="overview",
            total_revenue=float(result.total_revenue or 0),
            total_revenue_ttc=float(result.total_revenue_ttc or 0),
            total_objective=float(total_objective),
            avg_achievement_rate=float(result.avg_achievement_rate or 0),
            record_count=int(result.record_count or 0),
            min_revenue=float(result.min_revenue or 0),
            max_revenue=float(result.max_revenue or 0),
        )

        self.db.add(pivot)
        self.db.commit()

        logger.info(f"✅ Overview pivot created: {result.record_count} records")
        return 1

    def _generate_by_org_pivot(self, file_upload_id: Optional[int] = None) -> int:
        """Generate pivot by organization (DOT)"""
        logger.info("📊 Generating by_org pivot...")

        # Clear existing
        self.db.query(RevenuePivotCache).filter(
            RevenuePivotCache.pivot_type == "by_org"
        ).delete()

        # Query grouped by org_name
        query = self.db.query(
            RevenueJournal.org_name,
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label("total_revenue"),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label("total_revenue_ttc"),
            func.avg(RevenueJournal.taux_realisation_ca).label("avg_achievement_rate"),
            func.count(RevenueJournal.id).label("record_count"),
        ).group_by(RevenueJournal.org_name)

        if file_upload_id:
            query = query.filter(RevenueJournal.file_upload_id == file_upload_id)

        results = query.all()

        # Get objectives by org
        objectives = self.db.query(RevenueObjective).all()
        # Use normalized dot_name for consistent matching
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        obj_dict = {
            RevenueProcessingHelpers.clean_org_name_for_matching(obj.dot_name): obj.objectif_ca 
            for obj in objectives
        }

        # Create pivot records
        pivots = []
        for row in results:
            # Normalize org_name for consistent objective lookup
            normalized_org_name = RevenueProcessingHelpers.clean_org_name_for_matching(row.org_name or "")
            objective = obj_dict.get(normalized_org_name, 0)

            pivot = RevenuePivotCache(
                file_upload_id=file_upload_id,
                pivot_type="by_org",
                org_name=row.org_name,
                total_revenue=float(row.total_revenue or 0),
                total_revenue_ttc=float(row.total_revenue_ttc or 0),
                total_objective=float(objective),
                avg_achievement_rate=float(row.avg_achievement_rate or 0),
                record_count=int(row.record_count or 0),
            )
            pivots.append(pivot)

        self.db.bulk_save_objects(pivots)
        self.db.commit()

        logger.info(f"✅ By_org pivot created: {len(pivots)} organizations")
        return len(pivots)

    def _generate_by_month_pivot(self, file_upload_id: Optional[int] = None) -> int:
        """Generate pivot by month"""
        logger.info("📊 Generating by_month pivot...")

        # Clear existing
        self.db.query(RevenuePivotCache).filter(
            RevenuePivotCache.pivot_type == "by_month"
        ).delete()

        # Query grouped by month
        query = self.db.query(
            func.to_char(RevenueJournal.date_gl, 'YYYY-MM').label('month'),
            func.extract('year', RevenueJournal.date_gl).label('year'),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label("total_revenue"),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label("total_revenue_ttc"),
            func.avg(RevenueJournal.taux_realisation_ca).label("avg_achievement_rate"),
            func.count(RevenueJournal.id).label("record_count"),
        ).group_by('month', 'year').order_by('month')

        if file_upload_id:
            query = query.filter(RevenueJournal.file_upload_id == file_upload_id)

        results = query.all()

        # Get total objective and distribute monthly
        total_objective = self.db.query(
            func.sum(RevenueObjective.objectif_ca)
        ).scalar() or 0
        monthly_objective = float(total_objective) / 12.0

        # Create pivot records
        pivots = []
        for row in results:
            pivot = RevenuePivotCache(
                file_upload_id=file_upload_id,
                pivot_type="by_month",
                month=row.month,
                year=int(row.year) if row.year else None,
                total_revenue=float(row.total_revenue or 0),
                total_revenue_ttc=float(row.total_revenue_ttc or 0),
                total_objective=monthly_objective,
                avg_achievement_rate=float(row.avg_achievement_rate or 0),
                record_count=int(row.record_count or 0),
            )
            pivots.append(pivot)

        self.db.bulk_save_objects(pivots)
        self.db.commit()

        logger.info(f"✅ By_month pivot created: {len(pivots)} months")
        return len(pivots)

    def _generate_by_account_pivot(self, file_upload_id: Optional[int] = None) -> int:
        """Generate pivot by account (Cpt Comptable)"""
        logger.info("📊 Generating by_account pivot...")

        # Clear existing
        self.db.query(RevenuePivotCache).filter(
            RevenuePivotCache.pivot_type == "by_account"
        ).delete()

        # Query grouped by cpt_comptable
        query = self.db.query(
            RevenueJournal.cpt_comptable,
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label("total_revenue"),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label("total_revenue_ttc"),
            func.avg(RevenueJournal.taux_realisation_ca).label("avg_achievement_rate"),
            func.count(RevenueJournal.id).label("record_count"),
        ).group_by(RevenueJournal.cpt_comptable)

        if file_upload_id:
            query = query.filter(RevenueJournal.file_upload_id == file_upload_id)

        results = query.all()

        # Create pivot records
        pivots = []
        for row in results:
            pivot = RevenuePivotCache(
                file_upload_id=file_upload_id,
                pivot_type="by_account",
                cpt_comptable=row.cpt_comptable,
                total_revenue=float(row.total_revenue or 0),
                total_revenue_ttc=float(row.total_revenue_ttc or 0),
                avg_achievement_rate=float(row.avg_achievement_rate or 0),
                record_count=int(row.record_count or 0),
            )
            pivots.append(pivot)

        self.db.bulk_save_objects(pivots)
        self.db.commit()

        logger.info(f"✅ By_account pivot created: {len(pivots)} accounts")
        return len(pivots)

    def _generate_by_org_month_pivot(self, file_upload_id: Optional[int] = None) -> int:
        """Generate pivot by organization AND month (2D pivot)"""
        logger.info("📊 Generating by_org_month pivot...")

        # Clear existing
        self.db.query(RevenuePivotCache).filter(
            RevenuePivotCache.pivot_type == "by_org_month"
        ).delete()

        # Query grouped by org_name AND month
        query = self.db.query(
            RevenueJournal.org_name,
            func.to_char(RevenueJournal.date_gl, 'YYYY-MM').label('month'),
            func.extract('year', RevenueJournal.date_gl).label('year'),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label("total_revenue"),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label("total_revenue_ttc"),
            func.avg(RevenueJournal.taux_realisation_ca).label("avg_achievement_rate"),
            func.count(RevenueJournal.id).label("record_count"),
        ).group_by(RevenueJournal.org_name, 'month', 'year')

        if file_upload_id:
            query = query.filter(RevenueJournal.file_upload_id == file_upload_id)

        results = query.all()

        # Get objectives by org
        objectives = self.db.query(RevenueObjective).all()
        # Use normalized dot_name for consistent matching
        from services.revenue_processing_helpers import RevenueProcessingHelpers
        obj_dict = {
            RevenueProcessingHelpers.clean_org_name_for_matching(obj.dot_name): obj.objectif_ca 
            for obj in objectives
        }

        # Create pivot records
        pivots = []
        for row in results:
            # Normalize org_name for consistent objective lookup
            normalized_org_name = RevenueProcessingHelpers.clean_org_name_for_matching(row.org_name or "")
            objective = obj_dict.get(normalized_org_name, 0)
            monthly_objective = float(objective) / 12.0

            pivot = RevenuePivotCache(
                file_upload_id=file_upload_id,
                pivot_type="by_org_month",
                org_name=row.org_name,
                month=row.month,
                year=int(row.year) if row.year else None,
                total_revenue=float(row.total_revenue or 0),
                total_revenue_ttc=float(row.total_revenue_ttc or 0),
                total_objective=monthly_objective,
                avg_achievement_rate=float(row.avg_achievement_rate or 0),
                record_count=int(row.record_count or 0),
            )
            pivots.append(pivot)

        self.db.bulk_save_objects(pivots)
        self.db.commit()

        logger.info(f"✅ By_org_month pivot created: {len(pivots)} combinations")
        return len(pivots)

    def get_pivot_data(
        self,
        pivot_type: str,
        org_name: Optional[str] = None,
        month: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[RevenuePivotCache]:
        """
        Retrieve pivot data with filters
        """
        query = self.db.query(RevenuePivotCache).filter(
            RevenuePivotCache.pivot_type == pivot_type
        )

        if org_name:
            query = query.filter(RevenuePivotCache.org_name == org_name)
        if month:
            query = query.filter(RevenuePivotCache.month == month)
        if year:
            query = query.filter(RevenuePivotCache.year == year)

        return query.all()

    def update_pivot_metadata(
        self, pivot_type: str, status: str, record_count: int = 0, error: str = None
    ):
        """Update pivot generation metadata"""
        metadata = self.db.query(RevenuePivotMetadata).filter(
            RevenuePivotMetadata.pivot_type == pivot_type
        ).first()

        if not metadata:
            metadata = RevenuePivotMetadata(pivot_type=pivot_type)
            self.db.add(metadata)

        metadata.generation_status = status
        metadata.record_count = record_count
        metadata.error_message = error
        metadata.last_generated_at = datetime.utcnow()
        metadata.updated_at = datetime.utcnow()

        self.db.commit()
