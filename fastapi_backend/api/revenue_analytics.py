"""
Revenue Analytics API Endpoints
Handles data retrieval, filtering, and export for revenue data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.revenue import RevenueJournal, AccountDescription, RevenueObjective, RevenueAnomaly
from services.permission_service import PermissionService
from core.security import get_current_user
from pydantic import BaseModel
from datetime import datetime, date
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/revenue", tags=["Revenue Analytics"])


# ============================================================================
# Pydantic Schemas (import from revenue.py or define here)
# ============================================================================

class RevenueJournalResponse(BaseModel):
    id: int
    org_name: Optional[str]
    n_fact: Optional[str]
    date_fact: Optional[date]
    date_gl: Optional[date]
    n_client: Optional[str]
    client: Optional[str]
    cpt_comptable: Optional[str]
    chiffre_aff_exe_dzd: Optional[float]
    tva: Optional[float]
    chiffre_aff_exe_dzd_ttc: Optional[float]
    taux_realisation_ca: Optional[float]

    class Config:
        from_attributes = True


class RevenueListResponse(BaseModel):
    items: List[RevenueJournalResponse]
    total: int
    page: int
    page_size: int


class RevenueOverviewResponse(BaseModel):
    total_revenue: float
    total_revenue_ttc: float
    total_records: int
    by_org_name: Dict[str, float]
    by_month: Dict[str, float]
    by_month_objective: Dict[str, float] | None = None
    anomalies_count: int


class RevenueByOrgResponse(BaseModel):
    org_name: str
    total_revenue: float
    achievement_rate: Optional[float]
    objective: Optional[float]
    record_count: int


class RevenueByAccountResponse(BaseModel):
    cpt_comptable: str
    description: Optional[str]
    total_revenue: float
    record_count: int


# ============================================================================
# Data Retrieval Endpoints
# ============================================================================

@router.get("/overview", response_model=RevenueOverviewResponse)
async def get_revenue_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get overview of revenue data with aggregations
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(RevenueJournal)

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))

        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)

        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Total records
        total_records = query.count()

        # Create a subquery with explicit select()
        filtered_ids = query.with_entities(RevenueJournal.id).subquery()

        # Total revenue
        total_revenue = db.query(
            func.sum(RevenueJournal.chiffre_aff_exe_dzd)
        ).filter(RevenueJournal.id.in_(
            db.query(filtered_ids.c.id)
        )).scalar() or 0.0

        # Total revenue TTC
        total_revenue_ttc = db.query(
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc)
        ).filter(RevenueJournal.id.in_(
            db.query(filtered_ids.c.id)
        )).scalar() or 0.0

        # By Org Name
        by_org = db.query(
            RevenueJournal.org_name,
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label('total')
        ).filter(RevenueJournal.id.in_(
            db.query(filtered_ids.c.id)
        )).group_by(RevenueJournal.org_name).all()

        by_org_name = {row.org_name or "Unknown": float(
            row.total or 0) for row in by_org}

        # By Month (CA)
        by_month_data = db.query(
            func.date_trunc('month', RevenueJournal.date_gl).label('month'),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label('total')
        ).filter(RevenueJournal.id.in_(
            db.query(filtered_ids.c.id)
        )).group_by('month').all()

        by_month = {str(row.month): float(row.total or 0)
                    for row in by_month_data}

        # Monthly Objective series (distribute total objective equally across 12 months)
        # If there are months returned, use their year to build matching keys
        by_month_objective: Dict[str, float] = {}
        total_objective = db.query(
            func.sum(RevenueObjective.objectif_ca)).scalar() or 0.0

        if by_month_data and total_objective:
            # Group months by year to support multi-year datasets
            from collections import defaultdict
            months_by_year: Dict[int, list] = defaultdict(list)
            for row in by_month_data:
                dt = row.month
                year = getattr(dt, 'year', None)
                if isinstance(dt, str):
                    # Fallback in unlikely string case
                    try:
                        year = int(str(dt)[:4])
                    except Exception:
                        year = None
                if year is not None:
                    months_by_year[year].append(str(dt))

            # Distribute the total objective per year equally (12 months)
            # If multiple years, use the same total per year unless a per-year objective model is added later
            for year, month_keys in months_by_year.items():
                monthly_value = float(total_objective) / 12.0
                for mk in month_keys:
                    by_month_objective[mk] = monthly_value
        else:
            by_month_objective = {}

        # Anomalies count
        anomalies_count = db.query(RevenueAnomaly).count()

        return {
            "total_revenue": float(total_revenue),
            "total_revenue_ttc": float(total_revenue_ttc),
            "total_records": total_records,
            "by_org_name": by_org_name,
            "by_month": by_month,
            "by_month_objective": by_month_objective,
            "anomalies_count": anomalies_count
        }

    except Exception as e:
        logger.error(f"Error getting revenue overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-org", response_model=List[RevenueByOrgResponse])
async def get_revenue_by_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get revenue data grouped by organization (DOT)
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        query = db.query(
            RevenueJournal.org_name,
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label(
                'total_revenue'),
            func.avg(RevenueJournal.taux_realisation_ca).label(
                'avg_achievement'),
            func.count(RevenueJournal.id).label('record_count')
        )

        # Apply date filters
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        results = query.group_by(
            RevenueJournal.org_name).order_by(func.sum(RevenueJournal.chiffre_aff_exe_dzd).desc()).all()

        # Get objectives
        objectives_dict = {}
        objectives = db.query(RevenueObjective).all()
        for obj in objectives:
            objectives_dict[obj.dot_name] = obj.objectif_ca

        response = []
        for row in results:
            response.append(RevenueByOrgResponse(
                org_name=row.org_name or "Unknown",
                total_revenue=float(row.total_revenue or 0),
                achievement_rate=float(row.avg_achievement or 0),
                objective=objectives_dict.get(row.org_name),
                record_count=int(row.record_count)
            ))

        return response

    except Exception as e:
        logger.error(f"Error getting revenue by org: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-account", response_model=List[RevenueByAccountResponse])
async def get_revenue_by_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get revenue data grouped by account (Cpt Comptable)
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        query = db.query(
            RevenueJournal.cpt_comptable,
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label(
                'total_revenue'),
            func.count(RevenueJournal.id).label('record_count')
        )

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        results = query.group_by(RevenueJournal.cpt_comptable).order_by(
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).desc()).all()

        # Get account descriptions
        accounts_dict = {}
        accounts = db.query(AccountDescription).all()
        for acc in accounts:
            accounts_dict[acc.cpt_comptable] = acc.description_cpt_comptable

        response = []
        for row in results:
            response.append(RevenueByAccountResponse(
                cpt_comptable=row.cpt_comptable or "Unknown",
                description=accounts_dict.get(row.cpt_comptable),
                total_revenue=float(row.total_revenue or 0),
                record_count=int(row.record_count)
            ))

        return response

    except Exception as e:
        logger.error(f"Error getting revenue by account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# List and Filter Endpoints
# ============================================================================

@router.get("/list", response_model=RevenueListResponse)
async def list_revenue_journals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    org_name: Optional[List[str]] = Query(None),
    cpt_comptable: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None
):
    """
    List revenue journal entries with filtering and pagination
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        query = db.query(RevenueJournal)

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))

        if cpt_comptable:
            query = query.filter(
                RevenueJournal.cpt_comptable.ilike(f"%{cpt_comptable}%"))

        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)

        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        if search:
            search_filter = or_(
                RevenueJournal.org_name.ilike(f"%{search}%"),
                RevenueJournal.client.ilike(f"%{search}%"),
                RevenueJournal.n_fact.ilike(f"%{search}%"),
                RevenueJournal.n_client.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Total count
        total = query.count()

        # Pagination
        offset = (page - 1) * page_size
        items = query.order_by(RevenueJournal.date_gl.desc()).offset(
            offset).limit(page_size).all()

        return RevenueListResponse(
            items=[RevenueJournalResponse.from_orm(item) for item in items],
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error listing revenue journals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Export Endpoint
# ============================================================================

@router.get("/export")
async def export_revenue_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: str = Query("xlsx", regex="^(xlsx|csv)$")
):
    """
    Export revenue data to Excel or CSV
    Requires: can_export_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_export_analytics")

    try:
        # Build query (no limit for export)
        query = db.query(RevenueJournal)

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Fetch all data
        data = query.order_by(RevenueJournal.date_gl.desc()).all()

        # Convert to DataFrame
        records = []
        for item in data:
            records.append({
                "Org Name": item.org_name,
                "N Fact": item.n_fact,
                "Date Fact": item.date_fact,
                "Date GL": item.date_gl,
                "N Client": item.n_client,
                "Client": item.client,
                "Cpt Comptable": item.cpt_comptable,
                "Chiffre Aff Exe Dzd": item.chiffre_aff_exe_dzd,
                "TVA": item.tva,
                "Chiffre Aff Exe Dzd TTC": item.chiffre_aff_exe_dzd_ttc,
                "Taux Réalisation CA": item.taux_realisation_ca
            })

        df = pd.DataFrame(records)

        # Generate file
        output = io.BytesIO()

        if format == "xlsx":
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Revenue Data')
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"revenue_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:  # csv
            df.to_csv(output, index=False)
            media_type = "text/csv"
            filename = f"revenue_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        output.seek(0)

        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"Error exporting revenue data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
