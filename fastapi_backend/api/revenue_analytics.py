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
    total_objective: float  # Total objective (not divided by months)
    anomalies_count: int


class RevenueByOrgResponse(BaseModel):
    """Response schema for revenue data grouped by organization (DOT)"""
    org_name: str                          # DOT name
    total_revenue: float                   # CA total
    achievement_rate: Optional[float]      # Taux de réalisation C.A (%)
    objective: Optional[float]             # Revenue objective for this DOT
    record_count: int                      # Number of revenue records


class RevenueByAccountResponse(BaseModel):
    cpt_comptable: str
    description: Optional[str]
    total_revenue: float
    record_count: int


class RevenueByMonthResponse(BaseModel):
    """Response schema for monthly revenue aggregations"""
    month: str  # YYYY-MM format
    total_revenue: float
    total_revenue_ttc: float
    achievement_rate: Optional[float]
    objective: Optional[float]
    record_count: int


class RevenueByTypeFactResponse(BaseModel):
    """Response schema for Type Fact aggregations"""
    typ_fact: str
    total_revenue: float
    total_revenue_ttc: float
    achievement_rate: Optional[float]
    record_count: int


class RevenueByTauxCAResponse(BaseModel):
    """Response schema for Taux CA range aggregations"""
    taux_range: str  # e.g., "0-25%", "25-50%"
    total_revenue: float
    record_count: int
    avg_achievement_rate: float


class RevenueFiltersResponse(BaseModel):
    """Response schema for available filter values"""
    org_names: List[str]
    months: List[str]  # Date GL months
    date_fact_months: List[str]  # Date Fact months
    typ_fact_list: List[str]  # Type Fact values
    cpt_comptable_list: List[Dict[str, str]]  # [{code, description}]
    achievement_rate_ranges: List[Dict[str, Any]]


class RevenuePivotResponse(BaseModel):
    """Response schema for pivot table aggregations"""
    dimensions: List[str]  # The dimensions used for grouping
    aggregations: List[str]  # The metrics aggregated
    data: Dict[str, Any]  # Pivot data structure
    summary: Dict[str, float]  # Total aggregations


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

        # Build objective query with same filters as revenue
        objective_query = db.query(func.sum(RevenueObjective.objectif_ca))

        # Apply org_name filter to objectives
        if org_name:
            objective_query = objective_query.filter(RevenueObjective.dot_name.in_(org_name))

        total_objective = objective_query.scalar() or 0.0

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
            "total_objective": float(total_objective),  # Include total objective
            "anomalies_count": anomalies_count
        }

    except Exception as e:
        logger.error(f"Error getting revenue overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview-data")
async def get_revenue_preview_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of records to preview"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    # Dynamic column filters - accept any column name with value
    # All column filters - support filtering on any column
    id: Optional[List[str]] = Query(None),
    file_upload_id: Optional[List[str]] = Query(None),
    dot_id: Optional[List[str]] = Query(None),
    org_name: Optional[List[str]] = Query(None),
    origine: Optional[List[str]] = Query(None),
    n_fact: Optional[List[str]] = Query(None),
    typ_fact: Optional[List[str]] = Query(None),
    n_client: Optional[List[str]] = Query(None),
    client: Optional[List[str]] = Query(None),
    delai_paie: Optional[List[str]] = Query(None),
    devise: Optional[List[str]] = Query(None),
    cpt_comptable: Optional[List[str]] = Query(None),
    periode_de_facturation: Optional[List[str]] = Query(None),
    creer_par: Optional[List[str]] = Query(None),
    uom: Optional[List[str]] = Query(None),
    tax: Optional[List[str]] = Query(None),
    n_ligne: Optional[List[str]] = Query(None),
    memo_line_id: Optional[List[str]] = Query(None),
    reference: Optional[List[str]] = Query(None),
    account_description_id: Optional[List[str]] = Query(None),
    revenue_objective_id: Optional[List[str]] = Query(None),
    # Date filters
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    start_date_fact: Optional[date] = None,
    end_date_fact: Optional[date] = None,
    # Numeric range filters
    taux_ca_min: Optional[float] = None,
    taux_ca_max: Optional[float] = None,
    chiffre_aff_exe_dzd_min: Optional[float] = None,
    chiffre_aff_exe_dzd_max: Optional[float] = None,
    # Boolean filters (can be string "true"/"false" or "Oui"/"Non")
    termine_flag: Optional[str] = Query(None),
    is_anomaly: Optional[str] = Query(None),
    # Search
    search: Optional[str] = None,
    # Ordering
    order_by: Optional[str] = Query(None, description="Column name to order by"),
    order_direction: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Order direction")
):
    """
    Get sample revenue journal records for dashboard preview with filtering support
    
    Returns up to `limit` revenue journal records with full details.
    All filters are applied to the preview data.
    
    Parameters:
        limit: Number of records to return (1-100, default 10)
        offset: Number of records to skip for pagination (default 0)
        All filter parameters are supported
    
    Returns:
        Dictionary with:
        - records: List of revenue journal records with key fields
        - total_available: Total records accessible (after filters)
        - preview_limit: Actual limit applied
        - preview_offset: Offset applied
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")
    
    try:
        # Build query
        query = db.query(RevenueJournal)
        
        # Apply all column filters dynamically - support ALL columns
        # Handle integer ID columns
        if id:
            try:
                int_ids = [int(v) for v in id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(RevenueJournal.id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if file_upload_id:
            try:
                int_ids = [int(v) for v in file_upload_id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(RevenueJournal.file_upload_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if dot_id:
            try:
                int_ids = [int(v) for v in dot_id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(RevenueJournal.dot_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if account_description_id:
            try:
                int_ids = [int(v) for v in account_description_id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(RevenueJournal.account_description_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if revenue_objective_id:
            try:
                int_ids = [int(v) for v in revenue_objective_id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(RevenueJournal.revenue_objective_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        
        # Handle string columns
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if origine:
            query = query.filter(RevenueJournal.origine.in_(origine))
        if n_fact:
            query = query.filter(RevenueJournal.n_fact.in_(n_fact))
        if typ_fact:
            query = query.filter(RevenueJournal.typ_fact.in_(typ_fact))
        if n_client:
            query = query.filter(RevenueJournal.n_client.in_(n_client))
        if client:
            query = query.filter(RevenueJournal.client.in_(client))
        if delai_paie:
            query = query.filter(RevenueJournal.delai_paie.in_(delai_paie))
        if devise:
            query = query.filter(RevenueJournal.devise.in_(devise))
        if cpt_comptable:
            query = query.filter(RevenueJournal.cpt_comptable.in_(cpt_comptable))
        if periode_de_facturation:
            query = query.filter(RevenueJournal.periode_de_facturation.in_(periode_de_facturation))
        if creer_par:
            query = query.filter(RevenueJournal.creer_par.in_(creer_par))
        if uom:
            query = query.filter(RevenueJournal.uom.in_(uom))
        if tax:
            query = query.filter(RevenueJournal.tax.in_(tax))
        if n_ligne:
            query = query.filter(RevenueJournal.n_ligne.in_(n_ligne))
        if memo_line_id:
            query = query.filter(RevenueJournal.memo_line_id.in_(memo_line_id))
        if reference:
            query = query.filter(RevenueJournal.reference.in_(reference))
        
        # Handle boolean filters - convert string to boolean
        if termine_flag is not None:
            bool_val = termine_flag.lower() in ["true", "oui", "yes", "1"] if isinstance(termine_flag, str) else bool(termine_flag)
            query = query.filter(RevenueJournal.termine_flag == bool_val)
        if is_anomaly is not None:
            bool_val = is_anomaly.lower() in ["true", "oui", "yes", "1"] if isinstance(is_anomaly, str) else bool(is_anomaly)
            query = query.filter(RevenueJournal.is_anomaly == bool_val)
        
        # Handle date filters (can accept list of date strings)
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)
        if start_date_fact:
            query = query.filter(RevenueJournal.date_fact >= start_date_fact)
        if end_date_fact:
            query = query.filter(RevenueJournal.date_fact <= end_date_fact)
        
        # Handle numeric range filters
        if taux_ca_min is not None:
            query = query.filter(RevenueJournal.taux_realisation_ca >= taux_ca_min)
        if taux_ca_max is not None:
            query = query.filter(RevenueJournal.taux_realisation_ca <= taux_ca_max)
        if chiffre_aff_exe_dzd_min is not None:
            query = query.filter(RevenueJournal.chiffre_aff_exe_dzd >= chiffre_aff_exe_dzd_min)
        if chiffre_aff_exe_dzd_max is not None:
            query = query.filter(RevenueJournal.chiffre_aff_exe_dzd <= chiffre_aff_exe_dzd_max)
        
        # Search
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    RevenueJournal.org_name.ilike(search_term),
                    RevenueJournal.n_fact.ilike(search_term),
                    RevenueJournal.client.ilike(search_term),
                    RevenueJournal.n_client.ilike(search_term),
                    RevenueJournal.cpt_comptable.ilike(search_term),
                    RevenueJournal.description_ligne_de_produit.ilike(search_term),
                    RevenueJournal.obj_fact.ilike(search_term),
                    RevenueJournal.reference.ilike(search_term)
                )
            )
        
        # Get total count for pagination info (after filters)
        total_count = query.count()
        
        # Apply ordering
        order_column = None
        if order_by:
            # Map column names to actual model attributes
            column_map = {
                "id": RevenueJournal.id,
                "org_name": RevenueJournal.org_name,
                "origine": RevenueJournal.origine,
                "n_fact": RevenueJournal.n_fact,
                "typ_fact": RevenueJournal.typ_fact,
                "date_fact": RevenueJournal.date_fact,
                "date_gl": RevenueJournal.date_gl,
                "n_client": RevenueJournal.n_client,
                "client": RevenueJournal.client,
                "cpt_comptable": RevenueJournal.cpt_comptable,
                "chiffre_aff_exe_dzd": RevenueJournal.chiffre_aff_exe_dzd,
                "taux_realisation_ca": RevenueJournal.taux_realisation_ca,
                "created_at": RevenueJournal.created_at,
            }
            order_column = column_map.get(order_by)
        
        if order_column:
            if order_direction == "asc":
                records = query.order_by(order_column.asc(), RevenueJournal.id.asc()) \
                    .offset(offset) \
                    .limit(limit) \
                    .all()
            else:
                records = query.order_by(order_column.desc(), RevenueJournal.id.desc()) \
                    .offset(offset) \
                    .limit(limit) \
                    .all()
        else:
            # Default ordering
            records = query.order_by(RevenueJournal.date_gl.desc(), RevenueJournal.id.desc()) \
                .offset(offset) \
                .limit(limit) \
                .all()
        
        # Convert to dict format with ALL columns
        records_data = []
        for record in records:
            records_data.append({
                "id": record.id,
                "file_upload_id": record.file_upload_id,
                "dot_id": record.dot_id,
                "org_name": record.org_name,
                "origine": record.origine,
                "n_fact": record.n_fact,
                "typ_fact": record.typ_fact,
                "date_fact": record.date_fact.isoformat() if record.date_fact else None,
                "n_client": record.n_client,
                "client": record.client,
                "delai_paie": record.delai_paie,
                "devise": record.devise,
                "obj_fact": record.obj_fact,
                "cpt_comptable": record.cpt_comptable,
                "date_facture_gl": record.date_facture_gl.isoformat() if record.date_facture_gl else None,
                "date_gl": record.date_gl.isoformat() if record.date_gl else None,
                "periode_de_facturation": record.periode_de_facturation,
                "reference": record.reference,
                "termine_flag": record.termine_flag,
                "tax_amount": float(record.tax_amount) if record.tax_amount else None,
                "creer_par": record.creer_par,
                "n_ligne": record.n_ligne,
                "description_ligne_de_produit": record.description_ligne_de_produit,
                "uom": record.uom,
                "qte": float(record.qte) if record.qte else None,
                "prix_uni": float(record.prix_uni) if record.prix_uni else None,
                "taux_change": float(record.taux_change) if record.taux_change else None,
                "mnt_ht": float(record.mnt_ht) if record.mnt_ht else None,
                "tax": record.tax,
                "mnt_tax": float(record.mnt_tax) if record.mnt_tax else None,
                "mnt_ttc": float(record.mnt_ttc) if record.mnt_ttc else None,
                "memo_line_id": record.memo_line_id,
                "chiffre_aff_exe_dzd": float(record.chiffre_aff_exe_dzd) if record.chiffre_aff_exe_dzd else 0.0,
                "tva": float(record.tva) if record.tva else None,
                "chiffre_aff_exe_dzd_ttc": float(record.chiffre_aff_exe_dzd_ttc) if record.chiffre_aff_exe_dzd_ttc else 0.0,
                "taux_realisation_ca": float(record.taux_realisation_ca) if record.taux_realisation_ca else None,
                "account_description_id": record.account_description_id,
                "revenue_objective_id": record.revenue_objective_id,
                "is_anomaly": record.is_anomaly,
                "anomaly_reason": record.anomaly_reason,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return {
            "records": records_data,
            "total_available": total_count,
            "preview_limit": limit,
            "preview_offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error getting revenue preview data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview-data/column-values")
async def get_revenue_column_values(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    column: str = Query(..., description="Column name to get unique values for"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of values to return")
):
    """
    Get unique values for a specific column in revenue_journal table.
    Used for populating dropdown filters.
    Supports ALL columns in the revenue_journal table.
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")
    
    try:
        # Map ALL column names to actual model attributes
        column_map = {
            "id": RevenueJournal.id,
            "file_upload_id": RevenueJournal.file_upload_id,
            "dot_id": RevenueJournal.dot_id,
            "org_name": RevenueJournal.org_name,
            "origine": RevenueJournal.origine,
            "n_fact": RevenueJournal.n_fact,
            "typ_fact": RevenueJournal.typ_fact,
            "date_fact": RevenueJournal.date_fact,
            "n_client": RevenueJournal.n_client,
            "client": RevenueJournal.client,
            "delai_paie": RevenueJournal.delai_paie,
            "devise": RevenueJournal.devise,
            "obj_fact": RevenueJournal.obj_fact,
            "cpt_comptable": RevenueJournal.cpt_comptable,
            "date_facture_gl": RevenueJournal.date_facture_gl,
            "date_gl": RevenueJournal.date_gl,
            "periode_de_facturation": RevenueJournal.periode_de_facturation,
            "reference": RevenueJournal.reference,
            "termine_flag": RevenueJournal.termine_flag,
            "tax_amount": RevenueJournal.tax_amount,
            "creer_par": RevenueJournal.creer_par,
            "n_ligne": RevenueJournal.n_ligne,
            "description_ligne_de_produit": RevenueJournal.description_ligne_de_produit,
            "uom": RevenueJournal.uom,
            "qte": RevenueJournal.qte,
            "prix_uni": RevenueJournal.prix_uni,
            "taux_change": RevenueJournal.taux_change,
            "mnt_ht": RevenueJournal.mnt_ht,
            "tax": RevenueJournal.tax,
            "mnt_tax": RevenueJournal.mnt_tax,
            "mnt_ttc": RevenueJournal.mnt_ttc,
            "memo_line_id": RevenueJournal.memo_line_id,
            "chiffre_aff_exe_dzd": RevenueJournal.chiffre_aff_exe_dzd,
            "tva": RevenueJournal.tva,
            "chiffre_aff_exe_dzd_ttc": RevenueJournal.chiffre_aff_exe_dzd_ttc,
            "taux_realisation_ca": RevenueJournal.taux_realisation_ca,
            "account_description_id": RevenueJournal.account_description_id,
            "revenue_objective_id": RevenueJournal.revenue_objective_id,
            "is_anomaly": RevenueJournal.is_anomaly,
            "anomaly_reason": RevenueJournal.anomaly_reason,
            "created_at": RevenueJournal.created_at,
            "updated_at": RevenueJournal.updated_at,
        }
        
        if column not in column_map:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{column}' not found. Available columns: {list(column_map.keys())}"
            )
        
        # Get unique values
        values = db.query(column_map[column]) \
            .filter(column_map[column].isnot(None)) \
            .distinct() \
            .order_by(column_map[column].asc()) \
            .limit(limit) \
            .all()
        
        # Convert to list of strings, filtering out None
        unique_values = []
        for v in values:
            if v[0] is not None:
                # Format based on type
                if isinstance(v[0], (datetime, date)):
                    unique_values.append(v[0].isoformat())
                elif isinstance(v[0], bool):
                    unique_values.append("Oui" if v[0] else "Non")
                else:
                    unique_values.append(str(v[0]))
        
        return {
            "column": column,
            "values": unique_values,
            "count": len(unique_values)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting column values for {column}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview-objectives")
async def get_revenue_objectives_preview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of records to preview"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    dot_name: Optional[str] = Query(None, description="Filter by DOT name")
):
    """
    Get sample revenue objectives for dashboard preview
    
    Returns up to `limit` revenue objective records.
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")
    
    try:
        query = db.query(RevenueObjective)
        
        if dot_name:
            query = query.filter(RevenueObjective.dot_name.ilike(f"%{dot_name}%"))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        records = query.order_by(RevenueObjective.dot_name.asc()) \
            .offset(offset) \
            .limit(limit) \
            .all()
        
        # Convert to dict format
        records_data = []
        for record in records:
            records_data.append({
                "id": record.id,
                "dot_name": record.dot_name,
                "objectif_ca": float(record.objectif_ca) if record.objectif_ca else 0.0,
                "dot_id": record.dot_id,
                "file_upload_id": record.file_upload_id,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return {
            "records": records_data,
            "total_available": total_count,
            "preview_limit": limit,
            "preview_offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error getting revenue objectives preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview-account-descriptions")
async def get_account_descriptions_preview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of records to preview"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    search: Optional[str] = Query(None, description="Search in account code or description")
):
    """
    Get sample account descriptions for dashboard preview
    
    Returns up to `limit` account description records.
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")
    
    try:
        query = db.query(AccountDescription)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    AccountDescription.cpt_comptable.ilike(search_term),
                    AccountDescription.description_cpt_comptable.ilike(search_term)
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        records = query.order_by(AccountDescription.cpt_comptable.asc()) \
            .offset(offset) \
            .limit(limit) \
            .all()
        
        # Convert to dict format
        records_data = []
        for record in records:
            records_data.append({
                "id": record.id,
                "cpt_comptable": record.cpt_comptable,
                "description_cpt_comptable": record.description_cpt_comptable,
                "aut_bdg": record.aut_bdg,
                "aut_imp": record.aut_imp,
                "type_cpte": record.type_cpte,
                "auxil": record.auxil,
                "let": record.let,
                "file_upload_id": record.file_upload_id,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })
        
        return {
            "records": records_data,
            "total_available": total_count,
            "preview_limit": limit,
            "preview_offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error getting account descriptions preview: {e}")
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
            # Use normalized dot_name for consistent matching
            from services.revenue_processing_helpers import RevenueProcessingHelpers
            normalized_dot_name = RevenueProcessingHelpers.clean_org_name_for_matching(obj.dot_name)
            objectives_dict[normalized_dot_name] = float(obj.objectif_ca or 0)

        response = []
        for row in results:
            # Normalize org_name for consistent objective lookup
            from services.revenue_processing_helpers import RevenueProcessingHelpers
            normalized_org_name = RevenueProcessingHelpers.clean_org_name_for_matching(row.org_name or "")
            
            response.append(RevenueByOrgResponse(
                org_name=row.org_name or "Unknown",
                total_revenue=float(row.total_revenue or 0),
                achievement_rate=float(row.avg_achievement or 0),
                objective=objectives_dict.get(normalized_org_name),
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


@router.get("/by-month", response_model=List[RevenueByMonthResponse])
async def get_revenue_by_month(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get revenue data grouped by month with achievement rates

    Returns monthly aggregations with total revenue, achievement rates, objectives,
    and record counts. Data is sorted chronologically.

    Parameters:
    - org_name: Optional list of organization names to filter by
    - start_date: Optional start date filter (YYYY-MM-DD)
    - end_date: Optional end date filter (YYYY-MM-DD)

    Response: List of monthly revenue summaries ordered by month (ascending)

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build base query
        query = db.query(
            func.to_char(RevenueJournal.date_gl, 'YYYY-MM').label('month'),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label('total_revenue'),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label('total_revenue_ttc'),
            func.avg(RevenueJournal.taux_realisation_ca).label('achievement_rate'),
            func.count(RevenueJournal.id).label('record_count')
        )

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Filter out null dates
        query = query.filter(RevenueJournal.date_gl.isnot(None))

        # Group and sort
        results = query.group_by(
            func.to_char(RevenueJournal.date_gl, 'YYYY-MM')
        ).order_by('month').all()

        # Get all objectives to match by month
        # Since objectives are typically annual, we'll try to distribute them
        all_objectives = db.query(RevenueObjective).all()
        total_objective = sum(float(obj.objectif_ca or 0) for obj in all_objectives)
        monthly_objective = total_objective / 12.0 if total_objective else None

        response = []
        for row in results:
            if row.month:  # Only include valid months
                response.append(RevenueByMonthResponse(
                    month=row.month,
                    total_revenue=float(row.total_revenue or 0),
                    total_revenue_ttc=float(row.total_revenue_ttc or 0),
                    achievement_rate=float(row.achievement_rate or 0),
                    objective=monthly_objective,
                    record_count=int(row.record_count or 0)
                ))

        logger.info(f"Retrieved {len(response)} monthly revenue summaries")

        return response

    except Exception as e:
        logger.error(f"Error getting revenue by month: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve monthly revenue: {str(e)}")


@router.get("/by-type-fact", response_model=List[RevenueByTypeFactResponse])
async def get_revenue_by_type_fact(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get revenue data grouped by Type Fact (Invoice Type)

    Returns aggregations with total revenue, achievement rates, and record counts.

    Parameters:
    - org_name: Optional list of organization names to filter by
    - start_date: Optional start date filter (YYYY-MM-DD)
    - end_date: Optional end date filter (YYYY-MM-DD)

    Response: List of Type Fact summaries ordered by total revenue (descending)

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build base query
        query = db.query(
            RevenueJournal.typ_fact,
            func.sum(RevenueJournal.chiffre_aff_exe_dzd).label('total_revenue'),
            func.sum(RevenueJournal.chiffre_aff_exe_dzd_ttc).label('total_revenue_ttc'),
            func.avg(RevenueJournal.taux_realisation_ca).label('achievement_rate'),
            func.count(RevenueJournal.id).label('record_count')
        )

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Filter out null typ_fact
        query = query.filter(RevenueJournal.typ_fact.isnot(None))

        # Group and sort
        results = query.group_by(
            RevenueJournal.typ_fact
        ).order_by(func.sum(RevenueJournal.chiffre_aff_exe_dzd).desc()).all()

        response = []
        for row in results:
            response.append(RevenueByTypeFactResponse(
                typ_fact=row.typ_fact or "Unknown",
                total_revenue=float(row.total_revenue or 0),
                total_revenue_ttc=float(row.total_revenue_ttc or 0),
                achievement_rate=float(row.achievement_rate or 0),
                record_count=int(row.record_count or 0)
            ))

        logger.info(f"Retrieved {len(response)} Type Fact summaries")

        return response

    except Exception as e:
        logger.error(f"Error getting revenue by type fact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Type Fact revenue: {str(e)}")


@router.get("/by-taux-ca", response_model=List[RevenueByTauxCAResponse])
async def get_revenue_by_taux_ca(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get revenue data grouped by Taux de réalisation C.A ranges

    Returns aggregations by achievement rate ranges (0-25%, 25-50%, etc.)

    Parameters:
    - org_name: Optional list of organization names to filter by
    - start_date: Optional start date filter (YYYY-MM-DD)
    - end_date: Optional end date filter (YYYY-MM-DD)

    Response: List of Taux CA range summaries

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build base query
        query = db.query(RevenueJournal)

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Filter out null taux_realisation_ca
        query = query.filter(RevenueJournal.taux_realisation_ca.isnot(None))

        # Fetch all records
        records = query.all()

        # Define achievement rate ranges
        ranges = [
            {"label": "0-25%", "min": 0, "max": 25},
            {"label": "25-50%", "min": 25, "max": 50},
            {"label": "50-75%", "min": 50, "max": 75},
            {"label": "75-100%", "min": 75, "max": 100},
            {"label": "100%+", "min": 100, "max": 999999}
        ]

        response = []
        for range_def in ranges:
            # Filter records in this range
            range_records = [
                r for r in records
                if r.taux_realisation_ca is not None
                and range_def["min"] <= float(r.taux_realisation_ca) < range_def["max"]
            ]

            if range_records:
                total_revenue = sum(float(r.chiffre_aff_exe_dzd or 0) for r in range_records)
                avg_achievement = sum(float(r.taux_realisation_ca or 0) for r in range_records) / len(range_records)

                response.append(RevenueByTauxCAResponse(
                    taux_range=range_def["label"],
                    total_revenue=total_revenue,
                    record_count=len(range_records),
                    avg_achievement_rate=avg_achievement
                ))
            else:
                # Include empty ranges
                response.append(RevenueByTauxCAResponse(
                    taux_range=range_def["label"],
                    total_revenue=0.0,
                    record_count=0,
                    avg_achievement_rate=0.0
                ))

        logger.info(f"Retrieved {len(response)} Taux CA range summaries")

        return response

    except Exception as e:
        logger.error(f"Error getting revenue by taux CA: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Taux CA revenue: {str(e)}")


# ============================================================================
# List and Filter Endpoints
# ============================================================================

@router.get("/filters", response_model=RevenueFiltersResponse)
async def get_revenue_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available filter values for revenue analytics UI

    Returns unique organization names, months, and predefined achievement rate ranges
    that can be used to populate dropdown filters and sliders.

    Requires: can_view_analytics permission

    Response:
    - org_names: List of unique organization/DOT names (sorted)
    - months: List of distinct months in YYYY-MM format (sorted chronologically)
    - achievement_rate_ranges: Predefined achievement rate range buckets for filtering
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Get unique org_names
        org_names_result = db.query(
            RevenueJournal.org_name
        ).distinct().filter(
            RevenueJournal.org_name.isnot(None)
        ).order_by(RevenueJournal.org_name).all()

        org_names = [row.org_name for row in org_names_result]

        # Get distinct months from Date GL (YYYY-MM format)
        months_result = db.query(
            func.to_char(RevenueJournal.date_gl, 'YYYY-MM').label('month')
        ).distinct().filter(
            RevenueJournal.date_gl.isnot(None)
        ).order_by('month').all()

        months = sorted([row.month for row in months_result if row.month])

        # Get distinct months from Date Fact (YYYY-MM format)
        date_fact_months_result = db.query(
            func.to_char(RevenueJournal.date_fact, 'YYYY-MM').label('month')
        ).distinct().filter(
            RevenueJournal.date_fact.isnot(None)
        ).order_by('month').all()

        date_fact_months = sorted([row.month for row in date_fact_months_result if row.month])

        # Get unique Type Fact values
        typ_fact_result = db.query(
            RevenueJournal.typ_fact
        ).distinct().filter(
            RevenueJournal.typ_fact.isnot(None)
        ).order_by(RevenueJournal.typ_fact).all()

        typ_fact_list = [row.typ_fact for row in typ_fact_result]

        # Get Cpt Comptable with descriptions
        from models.revenue import AccountDescription
        cpt_comptable_result = db.query(
            AccountDescription.cpt_comptable,
            AccountDescription.description_cpt_comptable
        ).order_by(AccountDescription.cpt_comptable).all()

        cpt_comptable_list = [
            {
                "code": row.cpt_comptable,
                "description": row.description_cpt_comptable or "Sans description"
            }
            for row in cpt_comptable_result
        ]

        # Predefined achievement rate ranges for UI filter buckets
        achievement_rate_ranges = [
            {"label": "0-25%", "min": 0, "max": 25},
            {"label": "25-50%", "min": 25, "max": 50},
            {"label": "50-75%", "min": 50, "max": 75},
            {"label": "75-100%", "min": 75, "max": 100},
            {"label": "100%+", "min": 100, "max": 200}
        ]

        logger.info(f"Retrieved filters: {len(org_names)} orgs, {len(months)} date_gl months, {len(date_fact_months)} date_fact months, {len(typ_fact_list)} type facts, {len(cpt_comptable_list)} accounts")

        return {
            "org_names": org_names,
            "months": months,
            "date_fact_months": date_fact_months,
            "typ_fact_list": typ_fact_list,
            "cpt_comptable_list": cpt_comptable_list,
            "achievement_rate_ranges": achievement_rate_ranges
        }

    except Exception as e:
        logger.error(f"Error getting revenue filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filters: {str(e)}")


@router.get("/list", response_model=RevenueListResponse)
async def list_revenue_journals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    org_name: Optional[List[str]] = Query(None),
    typ_fact: Optional[List[str]] = Query(None),
    cpt_comptable: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    start_date_fact: Optional[date] = None,
    end_date_fact: Optional[date] = None,
    taux_ca_min: Optional[float] = None,
    taux_ca_max: Optional[float] = None,
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

        if typ_fact:
            query = query.filter(RevenueJournal.typ_fact.in_(typ_fact))

        if cpt_comptable:
            query = query.filter(
                RevenueJournal.cpt_comptable.ilike(f"%{cpt_comptable}%"))

        # Date GL filters
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)

        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Date Fact filters
        if start_date_fact:
            query = query.filter(RevenueJournal.date_fact >= start_date_fact)

        if end_date_fact:
            query = query.filter(RevenueJournal.date_fact <= end_date_fact)

        # Taux CA filters
        if taux_ca_min is not None:
            query = query.filter(RevenueJournal.taux_realisation_ca >= taux_ca_min)

        if taux_ca_max is not None:
            query = query.filter(RevenueJournal.taux_realisation_ca <= taux_ca_max)

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
# Pivot Table / Aggregation Endpoints
# ============================================================================

@router.get("/pivot", response_model=RevenuePivotResponse)
async def get_revenue_pivot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    group_by: str = Query("org_name", regex="^(org_name|month|cpt_comptable|org_month)$"),
    metric: str = Query("revenue", regex="^(revenue|count|achievement_rate)$"),
    org_name: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get revenue data as a pivot table with dynamic grouping

    Supports pivot operations on revenue data with flexible grouping dimensions.

    Parameters:
    - group_by: Grouping dimension (org_name, month, cpt_comptable, org_month)
    - metric: Metric to aggregate (revenue, count, achievement_rate)
    - org_name: Optional list of orgs to filter
    - start_date: Optional start date
    - end_date: Optional end date

    Response: Pivot table data with dimensions, aggregations, and summary totals

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build base query
        query = db.query(RevenueJournal)

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.in_(org_name))
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        records = query.all()

        # Initialize pivot data structure
        pivot_data = {}
        summary = {}

        # Metric definitions
        metric_config = {
            "revenue": ("chiffre_aff_exe_dzd", lambda x: sum(float(r.chiffre_aff_exe_dzd or 0) for r in x)),
            "count": ("record_count", lambda x: len(x)),
            "achievement_rate": ("taux_realisation_ca", lambda x: sum(float(r.taux_realisation_ca or 0) for r in x) / len(x) if x else 0)
        }

        metric_field, metric_func = metric_config[metric]

        # Group by org_name
        if group_by == "org_name":
            dimensions = ["org_name"]
            grouped = {}
            for record in records:
                key = record.org_name or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys()):
                value = metric_func(grouped[key])
                pivot_data[key] = value

            # Summary
            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values) if metric != "achievement_rate" else (sum(all_values) / len(all_values) if all_values else 0)

        # Group by month
        elif group_by == "month":
            from collections import defaultdict
            dimensions = ["month"]
            grouped = defaultdict(list)

            for record in records:
                if record.date_gl:
                    month_key = record.date_gl.strftime("%Y-%m")
                    grouped[month_key].append(record)

            for month in sorted(grouped.keys()):
                value = metric_func(grouped[month])
                pivot_data[month] = value

            # Summary
            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values) if metric != "achievement_rate" else (sum(all_values) / len(all_values) if all_values else 0)

        # Group by account (cpt_comptable)
        elif group_by == "cpt_comptable":
            dimensions = ["cpt_comptable"]
            grouped = {}
            for record in records:
                key = record.cpt_comptable or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys()):
                value = metric_func(grouped[key])
                pivot_data[key] = value

            # Summary
            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values) if metric != "achievement_rate" else (sum(all_values) / len(all_values) if all_values else 0)

        # Group by org_name AND month (two-dimensional pivot)
        elif group_by == "org_month":
            from collections import defaultdict
            dimensions = ["org_name", "month"]
            grouped = defaultdict(lambda: defaultdict(list))

            for record in records:
                org = record.org_name or "Unknown"
                if record.date_gl:
                    month = record.date_gl.strftime("%Y-%m")
                    grouped[org][month].append(record)

            # Build nested structure
            for org in sorted(grouped.keys()):
                pivot_data[org] = {}
                for month in sorted(grouped[org].keys()):
                    value = metric_func(grouped[org][month])
                    pivot_data[org][month] = value

            # Summary
            all_values = []
            for org_data in pivot_data.values():
                if isinstance(org_data, dict):
                    all_values.extend(org_data.values())

            summary[metric] = sum(all_values) if metric != "achievement_rate" else (sum(all_values) / len(all_values) if all_values else 0)

        logger.info(f"Generated pivot table: group_by={group_by}, metric={metric}, dimensions={dimensions}")

        return {
            "dimensions": dimensions,
            "aggregations": [metric],
            "data": pivot_data,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error generating pivot table: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate pivot: {str(e)}")


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
