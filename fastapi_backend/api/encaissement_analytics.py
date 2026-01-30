"""
Encaissement AR DOT Analytics API Endpoints
Handles data retrieval, filtering, and aggregations for encaissement (collection) data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, String, extract, Integer
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.encaissement import EncaissementARDot
from models.dot import MODULE_ENCAISSEMENT_AR_DOT
from services.permission_service import PermissionService
from services.dot_service import DOTService
from core.security import get_current_user
from pydantic import BaseModel
from datetime import date, datetime
import logging
import pandas as pd
import io
import uuid
import threading
import tempfile
import os
import asyncio
from services.processing_websocket import processing_ws_manager

logger = logging.getLogger(__name__)

encaissement_analytics_router = APIRouter(tags=["Encaissement Analytics"])

# Store active export tasks
export_tasks = {}


# ============================================================================
# Helper function to apply filters to query
# ============================================================================

def apply_encaissement_filters(
    query,
    organisation: Optional[List[str]] = None,
    date_fact_start: Optional[str] = None,
    date_fact_end: Optional[str] = None,
    taux_encaissement_min: Optional[float] = None,
    taux_encaissement_max: Optional[float] = None,
    search: Optional[str] = None,
    year: Optional[str] = None,
    typ_fact: Optional[List[str]] = None,
    date_rglt_start: Optional[str] = None,
    date_rglt_end: Optional[str] = None
):
    """
    Apply common filters to encaissement query
    
    Args:
        query: SQLAlchemy query object
        organisation: List of organization names to filter
        date_fact_start: Start date as month string (YYYY-MM) or date string
        date_fact_end: End date as month string (YYYY-MM) or date string
        taux_encaissement_min: Minimum collection rate
        taux_encaissement_max: Maximum collection rate
        search: Search term for client, n_fact, or organisation
    
    Returns:
        Filtered query
    """
    from datetime import datetime
    
    # Log received filters
    logger.info(
        f"🔍 [BACKEND] apply_encaissement_filters received filters: "
        f"organisation={organisation}, "
        f"date_fact_start={date_fact_start}, "
        f"date_fact_end={date_fact_end}, "
        f"search={search}, "
        f"year={year} (type: {type(year)}), "
        f"typ_fact={typ_fact}, "
        f"date_rglt_start={date_rglt_start}, "
        f"date_rglt_end={date_rglt_end}, "
        f"taux_encaissement_min={taux_encaissement_min}, "
        f"taux_encaissement_max={taux_encaissement_max}"
    )
    
    # Filter by organisation
    if organisation:
        query = query.filter(EncaissementARDot.organisation.in_(organisation))
    
    # Filter by date range (handle month strings like "2024-01")
    if date_fact_start:
        try:
            # Try parsing as month string first (YYYY-MM)
            if len(date_fact_start) == 7 and date_fact_start[4] == '-':
                start_date = datetime.strptime(date_fact_start, "%Y-%m").date()
            else:
                # Try parsing as full date
                start_date = datetime.strptime(date_fact_start, "%Y-%m-%d").date()
            query = query.filter(EncaissementARDot.date_fact >= start_date)
        except ValueError:
            logger.warning(f"Invalid date_fact_start format: {date_fact_start}")
    
    if date_fact_end:
        try:
            # Try parsing as month string first (YYYY-MM)
            if len(date_fact_end) == 7 and date_fact_end[4] == '-':
                # For month strings, use last day of month
                from calendar import monthrange
                year, month = map(int, date_fact_end.split('-'))
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
            else:
                # Try parsing as full date
                end_date = datetime.strptime(date_fact_end, "%Y-%m-%d").date()
            query = query.filter(EncaissementARDot.date_fact <= end_date)
        except ValueError:
            logger.warning(f"Invalid date_fact_end format: {date_fact_end}")
    
    # Filter by taux_encaissement range
    if taux_encaissement_min is not None:
        query = query.filter(EncaissementARDot.taux_encaissement >= taux_encaissement_min)
    if taux_encaissement_max is not None:
        query = query.filter(EncaissementARDot.taux_encaissement <= taux_encaissement_max)
    
    # Search filter (client name, n_fact, or organisation)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                EncaissementARDot.client.ilike(search_term),
                EncaissementARDot.n_fact.cast(String).ilike(search_term),
                EncaissementARDot.organisation.ilike(search_term)
            )
        )
    
    # Filter by year - extract year from date_fact or mois
    if year and year != "all":
        try:
            # Handle both string and int types
            if isinstance(year, str):
                year_str_clean = year.strip()
                if year_str_clean:
                    year_int = int(year_str_clean)
                else:
                    year_int = None
            elif isinstance(year, (int, float)):
                year_int = int(year)
            else:
                year_int = None
            
            if year_int:
                year_str = str(year_int)
                query = query.filter(
                    or_(
                        extract('year', EncaissementARDot.date_fact) == year_int,
                        func.substring(EncaissementARDot.mois, 1, 4) == year_str
                    )
                )
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid year format: {year}, error: {e}")
    
    # Filter by typ_fact
    if typ_fact:
        query = query.filter(EncaissementARDot.typ_fact.in_(typ_fact))
    
    # Filter by date_rglt range (handle month strings like "2024-01")
    if date_rglt_start:
        try:
            # Try parsing as month string first (YYYY-MM)
            if len(date_rglt_start) == 7 and date_rglt_start[4] == '-':
                start_date = datetime.strptime(date_rglt_start, "%Y-%m").date()
            else:
                # Try parsing as full date
                start_date = datetime.strptime(date_rglt_start, "%Y-%m-%d").date()
            query = query.filter(EncaissementARDot.date_rglt >= start_date)
        except ValueError:
            logger.warning(f"Invalid date_rglt_start format: {date_rglt_start}")
    
    if date_rglt_end:
        try:
            # Try parsing as month string first (YYYY-MM)
            if len(date_rglt_end) == 7 and date_rglt_end[4] == '-':
                # For month strings, use last day of month
                from calendar import monthrange
                year, month = map(int, date_rglt_end.split('-'))
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
            else:
                # Try parsing as full date
                end_date = datetime.strptime(date_rglt_end, "%Y-%m-%d").date()
            query = query.filter(EncaissementARDot.date_rglt <= end_date)
        except ValueError:
            logger.warning(f"Invalid date_rglt_end format: {date_rglt_end}")
    
    return query


# ============================================================================
# Pydantic Schemas
# ============================================================================

class EncaissementRecordResponse(BaseModel):
    """Response schema for individual encaissement records"""
    id: int
    organisation: Optional[str]
    n_fact: Optional[int]
    typ_fact: Optional[str]
    date_fact: Optional[date]
    client: Optional[str]
    montant_ttc: Optional[float]
    encaissement: Optional[float]
    taux_encaissement: Optional[float]
    montant_restant: Optional[float]

    class Config:
        from_attributes = True


class EncaissementByOrgResponse(BaseModel):
    """Response schema for organization-level aggregations"""
    organisation: str
    nombre_factures: int
    total_montant_ttc: float
    total_encaissement: float
    taux_encaissement_moyen: Optional[float]
    total_montant_restant: float


class EncaissementByMonthResponse(BaseModel):
    """Response schema for monthly aggregations"""
    mois: str  # YYYY-MM format
    nombre_factures: int
    total_montant_ttc: float
    total_encaissement: float
    taux_encaissement_moyen: Optional[float]
    total_montant_restant: float


class EncaissementYearlyData(BaseModel):
    """Yearly breakdown data"""
    year: str
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_encaissement: float
    nombre_factures: int
    nombre_organisations: int
    by_organisation: Dict[str, float]
    by_month: Dict[str, float]


class EncaissementOverviewResponse(BaseModel):
    """Response schema for overview analytics - now returns yearly breakdown"""
    yearly_data: List[EncaissementYearlyData]
    users: List[str]  # Unique users from creer_par field
    # Keep totals for backward compatibility (sum of all years)
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_encaissement: float
    nombre_factures: int
    nombre_organisations: int
    by_organisation: Dict[str, float]
    by_month: Dict[str, float]


class EncaissementFiltersResponse(BaseModel):
    """Response schema for available filter values"""
    organisations: List[str]
    mois: List[str]
    types_facture: List[str]
    taux_ranges: List[Dict[str, Any]]


class EncaissementPivotResponse(BaseModel):
    """Response schema for pivot table aggregations"""
    dimensions: List[str]
    aggregations: List[str]
    data: Dict[str, Any]
    summary: Dict[str, float]


class EncaissementByRateResponse(BaseModel):
    """Response schema for rate bucket aggregations"""
    taux_range: str
    range: str  # Alias for taux_range
    count: int
    total_montant_ttc: float
    total_encaissement: float


class EncaissementByTypFactResponse(BaseModel):
    """Response schema for Type Fact aggregations"""
    typ_fact: str
    nombre_factures: int
    total_montant_ttc: float
    total_encaissement: float
    taux_encaissement_moyen: Optional[float]
    total_montant_restant: float


class EncaissementByTauxCreanceResponse(BaseModel):
    """Response schema for Taux de Créance (Receivable Rate) aggregations by organization"""
    organisation: str
    nombre_factures: int
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_creance: Optional[float]  # Taux de créance = (montant_restant / montant_ttc) * 100


class EncaissementByDateRgltResponse(BaseModel):
    """Response schema for Date Règlement aggregations"""
    date_rglt: str  # YYYY-MM format
    nombre_factures: int
    total_montant_ttc: float
    total_encaissement: float
    taux_encaissement_moyen: Optional[float]
    total_montant_restant: float


# ============================================================================
# Overview Endpoint
# ============================================================================

@encaissement_analytics_router.get("/overview", response_model=EncaissementOverviewResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get overview analytics for encaissement data

    Returns key metrics including total amounts, collection rate, and distributions
    by organization and month.

    Parameters:
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    # Log received parameters
    logger.info(
        f"📥 [BACKEND /overview] Received request with params: "
        f"organisation={organisation}, "
        f"date_fact_start={date_fact_start}, "
        f"date_fact_end={date_fact_end}, "
        f"date_rglt_start={date_rglt_start}, "
        f"date_rglt_end={date_rglt_end}, "
        f"search={search}, "
        f"year={year} (type: {type(year)}), "
        f"typ_fact={typ_fact}, "
        f"taux_min={taux_encaissement_min}, "
        f"taux_max={taux_encaissement_max}"
    )

    try:
        # Build query with module-specific DOT filtering
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))
        
        # Apply common filters
        query = apply_encaissement_filters(
            query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Extract unique users from creer_par field
        users_query = query.with_entities(
            EncaissementARDot.creer_par
        ).filter(
            EncaissementARDot.creer_par.isnot(None),
            EncaissementARDot.creer_par != ""
        ).distinct().all()
        
        users = sorted([row.creer_par for row in users_query if row.creer_par])

        # Use SQL aggregation for accurate totals (more efficient and precise than Python sum)
        # First, get totals using SQL SUM for accuracy
        total_result = query.with_entities(
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.count(EncaissementARDot.id).label('total_count')
        ).first()
        
        sql_total_ttc = float(total_result.total_montant_ttc or 0) if total_result else 0.0
        sql_total_enc = float(total_result.total_encaissement or 0) if total_result else 0.0
        
        # Group by year - extract year from date_fact or mois
        # Get all records for year grouping (needed for yearly breakdown)
        all_records = query.all()
        
        # Build yearly data dictionary
        yearly_data_dict = {}
        
        # If year filter is applied, we should only process records from that year
        # But we still group by year in case there are edge cases
        filter_year_str = None
        if year and year != "all" and year.strip():
            try:
                filter_year_int = int(year.strip())
                filter_year_str = str(filter_year_int)
            except (ValueError, TypeError):
                pass
        
        for record in all_records:
            # Extract year from date_fact or mois
            year_str = None
            if record.date_fact:
                year_str = str(record.date_fact.year)
            elif record.mois and len(record.mois) >= 4:
                # Extract year from YYYY-MM format
                year_str = record.mois[:4]
            
            if not year_str:
                continue
            
            # If year filter is applied, skip records that don't match
            if filter_year_str and year_str != filter_year_str:
                continue
                
            if year_str not in yearly_data_dict:
                yearly_data_dict[year_str] = {
                    'montant_ttc': 0.0,
                    'encaissement': 0.0,
                    'factures': set(),
                    'organisations': set(),
                    'by_organisation': {},
                    'by_month': {}
                }
            
            montant_ttc = float(record.montant_ttc or 0)
            encaissement = float(record.encaissement or 0)
            
            yearly_data_dict[year_str]['montant_ttc'] += montant_ttc
            yearly_data_dict[year_str]['encaissement'] += encaissement
            yearly_data_dict[year_str]['factures'].add(record.id)
            
            if record.organisation:
                yearly_data_dict[year_str]['organisations'].add(record.organisation)
                if record.organisation not in yearly_data_dict[year_str]['by_organisation']:
                    yearly_data_dict[year_str]['by_organisation'][record.organisation] = 0.0
                yearly_data_dict[year_str]['by_organisation'][record.organisation] += montant_ttc
            
            if record.mois:
                if record.mois not in yearly_data_dict[year_str]['by_month']:
                    yearly_data_dict[year_str]['by_month'][record.mois] = 0.0
                yearly_data_dict[year_str]['by_month'][record.mois] += montant_ttc

        # Build yearly response
        yearly_data = []
        for year_str in sorted(yearly_data_dict.keys(), reverse=True):
            year_info = yearly_data_dict[year_str]
            total_ttc = year_info['montant_ttc']
            total_enc = year_info['encaissement']
            total_restant = total_ttc - total_enc
            taux = (total_enc / total_ttc * 100) if total_ttc > 0 else 0.0
            
            yearly_data.append(EncaissementYearlyData(
                year=year_str,
                total_montant_ttc=total_ttc,
                total_encaissement=total_enc,
                total_montant_restant=total_restant,
                taux_encaissement=float(taux),
                nombre_factures=len(year_info['factures']),
                nombre_organisations=len(year_info['organisations']),
                by_organisation=year_info['by_organisation'],
                by_month=year_info['by_month']
            ))

        # Calculate totals across all years (for backward compatibility)
        # ALWAYS use SQL SUM for accurate totals (more precise than Python sum)
        # The SQL SUM already has all filters applied (including year filter if present)
        # This ensures database-level precision and consistency
        total_montant_ttc = sql_total_ttc
        total_encaissement = sql_total_enc
        total_montant_restant = total_montant_ttc - total_encaissement
        taux_global = (total_encaissement / total_montant_ttc * 100) if total_montant_ttc > 0 else 0.0
        
        # For nombre_factures, use count from SQL or sum from yearly_data
        if year and year != "all" and year.strip():
            # Year filter applied - get count from selected year
            year_str = str(year).strip()
            selected_year_data = next(
                (y for y in yearly_data if str(y.year).strip() == year_str), None
            )
            nombre_factures = selected_year_data.nombre_factures if selected_year_data else 0
        else:
            # No year filter - sum counts from all years
            nombre_factures = sum(y.nombre_factures for y in yearly_data)
        
        # Aggregate by_organisation across all years
        # BUT: If year filter is applied, only include organisations from that year
        all_orgs = set()
        by_organisation = {}
        if year and year != "all" and year.strip():
            # Year filter is applied - only include organisations from the selected year
            # Normalize year to string for comparison
            year_str = str(year).strip()
            selected_year_data = next(
                (y for y in yearly_data if str(y.year).strip() == year_str), None
            )
            if selected_year_data:
                by_organisation = selected_year_data.by_organisation.copy()
                all_orgs = set(selected_year_data.by_organisation.keys())
        else:
            # No year filter - aggregate across all years
            for year_data in yearly_data:
                all_orgs.update(year_data.by_organisation.keys())
                for org, value in year_data.by_organisation.items():
                    by_organisation[org] = by_organisation.get(org, 0.0) + value
        
        # Aggregate by_month across all years
        # BUT: If year filter is applied, only include months from that year
        by_month = {}
        if year and year != "all" and year.strip():
            # Year filter is applied - only include months from the selected year
            # Normalize year to string for comparison
            year_str = str(year).strip()
            selected_year_data = next(
                (y for y in yearly_data if str(y.year).strip() == year_str), None
            )
            if selected_year_data:
                by_month = selected_year_data.by_month.copy()
        else:
            # No year filter - aggregate across all years
            for year_data in yearly_data:
                for month, value in year_data.by_month.items():
                    by_month[month] = by_month.get(month, 0.0) + value

        logger.info(f"Overview retrieved: {len(yearly_data)} years, {len(users)} users, Total TTC={total_montant_ttc}, Collection Rate={taux_global:.2f}%")

        return {
            "yearly_data": yearly_data,
            "users": users,
            "total_montant_ttc": float(total_montant_ttc),
            "total_encaissement": float(total_encaissement),
            "total_montant_restant": float(total_montant_restant),
            "taux_encaissement": float(taux_global),
            "nombre_factures": nombre_factures,
            "nombre_organisations": len(all_orgs),
            "by_organisation": by_organisation,
            "by_month": by_month
        }

    except Exception as e:
        logger.error(f"Error getting encaissement overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve overview: {str(e)}")


# ============================================================================
# By Organization Endpoint
# ============================================================================

@encaissement_analytics_router.get("/by-organisation", response_model=List[EncaissementByOrgResponse])
async def get_by_organisation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    sort_by: str = Query("montant_ttc", regex="^(organisation|factures|montant_ttc|encaissement|taux)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    limit: Optional[int] = Query(None, ge=1, le=100),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get encaissement data grouped by organization

    Returns organization-level aggregations with collection rates and outstanding amounts.

    Parameters:
    - sort_by: Sort field (organisation, factures, montant_ttc, encaissement, taux)
    - order: Sort order (asc, desc)
    - limit: Maximum number of results
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term for client, n_fact, or organisation

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    # Log received parameters
    logger.info(
        f"📥 [BACKEND /by-organisation] Received request with params: "
        f"organisation={organisation}, "
        f"date_fact_start={date_fact_start}, "
        f"date_fact_end={date_fact_end}, "
        f"date_rglt_start={date_rglt_start}, "
        f"date_rglt_end={date_rglt_end}, "
        f"search={search}, "
        f"year={year} (type: {type(year)}), "
        f"typ_fact={typ_fact}, "
        f"taux_min={taux_encaissement_min}, "
        f"taux_max={taux_encaissement_max}, "
        f"sort_by={sort_by}, order={order}"
    )

    try:
        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )

        # Build base query for filtering (before aggregation)
        base_query = db.query(EncaissementARDot)
        
        if accessible_dot_ids:
            base_query = base_query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))
        
        # Apply common filters
        base_query = apply_encaissement_filters(
            base_query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Build aggregation query with filters applied
        query = base_query.with_entities(
            EncaissementARDot.organisation,
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.avg(EncaissementARDot.taux_encaissement).label('taux_moyen')
        ).filter(
            EncaissementARDot.organisation.isnot(None)
        )

        results = query.group_by(
            EncaissementARDot.organisation
        ).all()

        # Calculate remaining amounts and build response
        response = []
        for row in results:
            total_ttc = float(row.total_montant_ttc or 0)
            total_encaissement = float(row.total_encaissement or 0)
            remaining = total_ttc - total_encaissement

            # Calculate taux as Encaissement / Montant TTC * 100 for each DOT
            taux_encaissement = 0.0
            if total_ttc > 0:
                taux_encaissement = (total_encaissement / total_ttc) * 100

            response.append(EncaissementByOrgResponse(
                organisation=row.organisation or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                taux_encaissement_moyen=round(taux_encaissement, 2),
                total_montant_restant=remaining
            ))

        # Apply sorting
        sort_map = {
            "organisation": lambda x: x.organisation,
            "factures": lambda x: x.nombre_factures,
            "montant_ttc": lambda x: x.total_montant_ttc,
            "encaissement": lambda x: x.total_encaissement,
            "taux": lambda x: x.taux_encaissement_moyen or 0
        }

        if sort_by in sort_map:
            response.sort(key=sort_map[sort_by], reverse=(order == "desc"))

        # Apply limit
        if limit:
            response = response[:limit]

        logger.info(f"By organisation retrieved: {len(response)} organisations")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by organisation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by organisation: {str(e)}")


# ============================================================================
# By Month Endpoint
# ============================================================================

@encaissement_analytics_router.get("/by-month", response_model=List[EncaissementByMonthResponse])
async def get_by_month(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get encaissement data grouped by month

    Returns monthly aggregations of collection data with rates and outstanding amounts.

    Parameters:
    - organisation: Optional list of organizations to filter
    - start_date: Optional start date
    - end_date: Optional end date

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply filters
        if organisation:
            query = query.filter(EncaissementARDot.organisation.in_(organisation))
        if start_date:
            query = query.filter(EncaissementARDot.date_fact >= start_date)
        if end_date:
            query = query.filter(EncaissementARDot.date_fact <= end_date)

        # Group by month
        results = query.with_entities(
            EncaissementARDot.mois,
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.avg(EncaissementARDot.taux_encaissement).label('taux_moyen')
        ).filter(
            EncaissementARDot.mois.isnot(None)
        ).group_by(
            EncaissementARDot.mois
        ).order_by(
            EncaissementARDot.mois
        ).all()

        # Build response
        response = []
        for row in results:
            total_ttc = float(row.total_montant_ttc or 0)
            total_encaissement = float(row.total_encaissement or 0)
            remaining = total_ttc - total_encaissement

            response.append(EncaissementByMonthResponse(
                mois=row.mois or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                taux_encaissement_moyen=float(row.taux_moyen or 0),
                total_montant_restant=remaining
            ))

        logger.info(f"By month retrieved: {len(response)} months")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by month: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by month: {str(e)}")


# ============================================================================
# By Date Endpoint (Alias for by-month)
# ============================================================================

@encaissement_analytics_router.get("/by-date", response_model=List[EncaissementByMonthResponse])
async def get_by_date(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get encaissement data grouped by date (month)

    Returns monthly aggregations of collection data with rates and outstanding amounts.

    Parameters:
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term for client, n_fact, or organisation

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))
        
        # Apply common filters
        query = apply_encaissement_filters(
            query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Group by month
        results = query.with_entities(
            EncaissementARDot.mois,
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.avg(EncaissementARDot.taux_encaissement).label('taux_moyen')
        ).filter(
            EncaissementARDot.mois.isnot(None)
        ).group_by(
            EncaissementARDot.mois
        ).order_by(
            EncaissementARDot.mois
        ).all()

        # Build response
        response = []
        for row in results:
            total_ttc = float(row.total_montant_ttc or 0)
            total_encaissement = float(row.total_encaissement or 0)
            remaining = total_ttc - total_encaissement

            response.append(EncaissementByMonthResponse(
                mois=row.mois or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                taux_encaissement_moyen=float(row.taux_moyen or 0),
                total_montant_restant=remaining
            ))

        logger.info(f"By date retrieved: {len(response)} months")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by date: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by date: {str(e)}")


# ============================================================================
# By Encaisse Rate Endpoint
# ============================================================================

@encaissement_analytics_router.get("/by-encaisse-rate", response_model=List[EncaissementByRateResponse])
async def get_by_encaisse_rate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get encaissement data grouped by collection rate buckets

    Returns aggregations by collection rate ranges (0-25%, 25-50%, 50-75%, 75-100%, 100%+)

    Parameters:
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term for client, n_fact, or organisation

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply common filters
        query = apply_encaissement_filters(
            query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Get all records
        records = query.all()

        # Define rate buckets (including negative rates for edge cases)
        # Negative rates can occur when encaissement is negative but montant_ttc is positive
        buckets = {
            "Negative": {"min": -999999, "max": 0, "count": 0, "montant_ttc": 0, "encaissement": 0},
            "0-25%": {"min": 0, "max": 25, "count": 0, "montant_ttc": 0, "encaissement": 0},
            "25-50%": {"min": 25, "max": 50, "count": 0, "montant_ttc": 0, "encaissement": 0},
            "50-75%": {"min": 50, "max": 75, "count": 0, "montant_ttc": 0, "encaissement": 0},
            "75-100%": {"min": 75, "max": 100, "count": 0, "montant_ttc": 0, "encaissement": 0},
            "100%+": {"min": 100, "max": 999999, "count": 0, "montant_ttc": 0, "encaissement": 0},
        }

        # Categorize records into buckets
        for record in records:
            taux = record.taux_encaissement or 0
            montant_ttc = record.montant_ttc or 0
            encaissement = record.encaissement or 0

            for bucket_name, bucket_data in buckets.items():
                if bucket_data["min"] <= taux < bucket_data["max"]:
                    bucket_data["count"] += 1
                    bucket_data["montant_ttc"] += montant_ttc
                    bucket_data["encaissement"] += encaissement
                    break

        # Build response
        response = []
        for bucket_name, bucket_data in buckets.items():
            response.append(EncaissementByRateResponse(
                taux_range=bucket_name,
                range=bucket_name,
                count=bucket_data["count"],
                total_montant_ttc=float(bucket_data["montant_ttc"]),
                total_encaissement=float(bucket_data["encaissement"])
            ))

        logger.info(f"By encaisse rate retrieved: {len(response)} rate buckets")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by rate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by rate: {str(e)}")


# ============================================================================
# By Taux de Créance Endpoint (By Organization)
# ============================================================================

@encaissement_analytics_router.get("/by-taux-creance", response_model=List[EncaissementByTauxCreanceResponse])
async def get_by_taux_creance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get encaissement data grouped by organization with taux de créance (receivable rate)
    
    Taux de créance = (montant_restant / montant_ttc) * 100
    This represents the percentage of outstanding receivables/debt.
    
    Returns aggregations by organization with calculated receivable rates.

    Parameters:
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term for client, n_fact, or organisation
    - year: Optional year filter
    - typ_fact: Optional Type Fact filter
    - date_rglt_start: Optional Date Règlement start
    - date_rglt_end: Optional Date Règlement end

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply common filters
        query = apply_encaissement_filters(
            query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Group by organisation
        results = query.with_entities(
            EncaissementARDot.organisation,
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.sum(EncaissementARDot.montant_restant).label('total_montant_restant')
        ).filter(
            EncaissementARDot.organisation.isnot(None)
        ).group_by(
            EncaissementARDot.organisation
        ).all()

        # Build response with taux de créance calculation
        response = []
        for row in results:
            total_ttc = float(row.total_montant_ttc or 0)
            total_encaissement = float(row.total_encaissement or 0)
            total_restant = float(row.total_montant_restant or 0)
            
            # Calculate taux de créance: (montant_restant / montant_ttc) * 100
            taux_creance = None
            if total_ttc > 0:
                taux_creance = (total_restant / total_ttc) * 100

            response.append(EncaissementByTauxCreanceResponse(
                organisation=row.organisation or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                total_montant_restant=total_restant,
                taux_creance=round(taux_creance, 2) if taux_creance is not None else None
            ))

        # Sort by taux de créance descending (highest receivable rate first)
        response.sort(key=lambda x: x.taux_creance if x.taux_creance is not None else 0, reverse=True)

        logger.info(f"By taux créance retrieved: {len(response)} organisations")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by taux créance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by taux créance: {str(e)}")


# ============================================================================
# By Type Fact Endpoint
# ============================================================================

@encaissement_analytics_router.get("/by-typ-fact", response_model=List[EncaissementByTypFactResponse])
async def get_by_typ_fact(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get encaissement data grouped by Type Fact

    Returns aggregations by invoice type with collection rates and outstanding amounts.

    Parameters:
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term for client, n_fact, or organisation
    - year: Optional year filter (YYYY)
    - typ_fact: Optional list of Type Fact values to filter
    - date_rglt_start: Optional Date Règlement start (YYYY-MM or YYYY-MM-DD)
    - date_rglt_end: Optional Date Règlement end (YYYY-MM or YYYY-MM-DD)

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply common filters
        query = apply_encaissement_filters(
            query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Group by typ_fact
        results = query.with_entities(
            EncaissementARDot.typ_fact,
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.avg(EncaissementARDot.taux_encaissement).label('taux_moyen')
        ).filter(
            EncaissementARDot.typ_fact.isnot(None)
        ).group_by(
            EncaissementARDot.typ_fact
        ).order_by(
            EncaissementARDot.typ_fact
        ).all()

        # Build response
        response = []
        for row in results:
            total_ttc = float(row.total_montant_ttc or 0)
            total_encaissement = float(row.total_encaissement or 0)
            remaining = total_ttc - total_encaissement

            response.append(EncaissementByTypFactResponse(
                typ_fact=row.typ_fact or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                taux_encaissement_moyen=float(row.taux_moyen or 0),
                total_montant_restant=remaining
            ))

        logger.info(f"By typ_fact retrieved: {len(response)} types")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by typ_fact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by typ_fact: {str(e)}")


# ============================================================================
# By Date Règlement Endpoint
# ============================================================================

@encaissement_analytics_router.get("/by-date-rglt", response_model=List[EncaissementByDateRgltResponse])
async def get_by_date_rglt(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisation: Optional[List[str]] = Query(None),
    date_fact_start: Optional[str] = Query(None, description="Start date as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="End date as YYYY-MM or YYYY-MM-DD"),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    typ_fact: Optional[List[str]] = Query(None, description="Filter by Type Fact"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD")
):
    """
    Get encaissement data grouped by Date Règlement (month)

    Returns monthly aggregations by payment date with collection rates and outstanding amounts.

    Parameters:
    - organisation: Optional list of organizations to filter
    - date_fact_start: Optional start date (YYYY-MM or YYYY-MM-DD)
    - date_fact_end: Optional end date (YYYY-MM or YYYY-MM-DD)
    - taux_encaissement_min: Optional minimum collection rate
    - taux_encaissement_max: Optional maximum collection rate
    - search: Optional search term for client, n_fact, or organisation
    - year: Optional year filter (YYYY)
    - typ_fact: Optional list of Type Fact values to filter
    - date_rglt_start: Optional Date Règlement start (YYYY-MM or YYYY-MM-DD)
    - date_rglt_end: Optional Date Règlement end (YYYY-MM or YYYY-MM-DD)

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply common filters
        query = apply_encaissement_filters(
            query,
            organisation=organisation,
            date_fact_start=date_fact_start,
            date_fact_end=date_fact_end,
            taux_encaissement_min=taux_encaissement_min,
            taux_encaissement_max=taux_encaissement_max,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )

        # Extract month from date_rglt and group by it
        # Use database-agnostic approach: check database type
        from core.config import settings
        
        # For PostgreSQL: use to_char, for SQLite: use strftime
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite approach
            mois_expr = func.strftime('%Y-%m', EncaissementARDot.date_rglt)
        else:
            # PostgreSQL approach
            mois_expr = func.to_char(EncaissementARDot.date_rglt, 'YYYY-MM')
        
        results = query.with_entities(
            mois_expr.label('mois'),
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.avg(EncaissementARDot.taux_encaissement).label('taux_moyen')
        ).filter(
            EncaissementARDot.date_rglt.isnot(None)
        ).group_by(
            mois_expr
        ).order_by(
            mois_expr
        ).all()

        # Build response
        response = []
        for row in results:
            total_ttc = float(row.total_montant_ttc or 0)
            total_encaissement = float(row.total_encaissement or 0)
            remaining = total_ttc - total_encaissement

            response.append(EncaissementByDateRgltResponse(
                date_rglt=row.mois or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                taux_encaissement_moyen=float(row.taux_moyen or 0),
                total_montant_restant=remaining
            ))

        logger.info(f"By date_rglt retrieved: {len(response)} months")

        return response

    except Exception as e:
        logger.error(f"Error getting encaissement by date_rglt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by date_rglt: {str(e)}")


# ============================================================================
# Filters Endpoint
# ============================================================================

@encaissement_analytics_router.get("/filters", response_model=EncaissementFiltersResponse)
async def get_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available filter values for encaissement analytics UI

    Returns unique organizations, months, invoice types, and predefined collection rate ranges.

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )

        # Build base query with DOT filter
        base_query = db.query(EncaissementARDot)
        if accessible_dot_ids:
            base_query = base_query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Get unique organisations
        org_results = base_query.with_entities(
            EncaissementARDot.organisation
        ).distinct().filter(
            EncaissementARDot.organisation.isnot(None)
        ).order_by(EncaissementARDot.organisation).all()

        organisations = [row.organisation for row in org_results]

        # Get unique months
        month_results = base_query.with_entities(
            EncaissementARDot.mois
        ).distinct().filter(
            EncaissementARDot.mois.isnot(None)
        ).order_by(EncaissementARDot.mois).all()

        mois = [row.mois for row in month_results if row.mois]

        # Get unique invoice types
        type_results = base_query.with_entities(
            EncaissementARDot.typ_fact
        ).distinct().filter(
            EncaissementARDot.typ_fact.isnot(None)
        ).order_by(EncaissementARDot.typ_fact).all()

        types_facture = [row.typ_fact for row in type_results]

        # Predefined collection rate ranges
        taux_ranges = [
            {"label": "0-25%", "min": 0, "max": 25},
            {"label": "25-50%", "min": 25, "max": 50},
            {"label": "50-75%", "min": 50, "max": 75},
            {"label": "75-100%", "min": 75, "max": 100},
            {"label": "100%+", "min": 100, "max": 200}
        ]

        logger.info(f"Filters retrieved: {len(organisations)} orgs, {len(mois)} months, {len(types_facture)} types")

        return {
            "organisations": organisations,
            "mois": mois,
            "types_facture": types_facture,
            "taux_ranges": taux_ranges
        }

    except Exception as e:
        logger.error(f"Error getting encaissement filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filters: {str(e)}")


# ============================================================================
# Preview Data Endpoint (Separate filters for preview tab)
# ============================================================================

@encaissement_analytics_router.get("/preview-data")
async def get_encaissement_preview_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=1000, description="Items per page"),
    # Column filters - all columns from ENCAISSEMENT_COLUMNS
    id: Optional[List[str]] = Query(None),
    file_upload_id: Optional[List[str]] = Query(None),
    dot_id: Optional[List[str]] = Query(None),
    organisation: Optional[List[str]] = Query(None),
    source: Optional[List[str]] = Query(None),
    n_fact: Optional[List[str]] = Query(None),
    typ_fact: Optional[List[str]] = Query(None),
    client: Optional[List[str]] = Query(None),
    n_client: Optional[List[str]] = Query(None),
    # Date filters
    date_fact_start: Optional[str] = Query(None, description="Date Fact start as YYYY-MM or YYYY-MM-DD"),
    date_fact_end: Optional[str] = Query(None, description="Date Fact end as YYYY-MM or YYYY-MM-DD"),
    date_rglt_start: Optional[str] = Query(None, description="Date Règlement start as YYYY-MM or YYYY-MM-DD"),
    date_rglt_end: Optional[str] = Query(None, description="Date Règlement end as YYYY-MM or YYYY-MM-DD"),
    mois: Optional[List[str]] = Query(None, description="Month filter (YYYY-MM)"),
    # Numeric range filters
    montant_ht_min: Optional[float] = Query(None),
    montant_ht_max: Optional[float] = Query(None),
    montant_taxe_min: Optional[float] = Query(None),
    montant_taxe_max: Optional[float] = Query(None),
    montant_ttc_min: Optional[float] = Query(None),
    montant_ttc_max: Optional[float] = Query(None),
    encaissement_min: Optional[float] = Query(None),
    encaissement_max: Optional[float] = Query(None),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    montant_restant_min: Optional[float] = Query(None),
    montant_restant_max: Optional[float] = Query(None),
    # Other filters
    composite_key: Optional[List[str]] = Query(None),
    is_duplicate: Optional[str] = Query(None, description="Filter duplicates: 'true', 'false'"),
    is_anomaly: Optional[str] = Query(None, description="Filter anomalies: 'true', 'false'"),
    anomaly_reason: Optional[List[str]] = Query(None),
    termine_flag: Optional[List[str]] = Query(None),
    creer_par: Optional[List[str]] = Query(None),
    obj_fact: Optional[List[str]] = Query(None),
    periode: Optional[List[str]] = Query(None),
    ref: Optional[List[str]] = Query(None),
    # Search
    search: Optional[str] = Query(None, description="Global search across multiple fields"),
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    # Ordering
    sort_by: Optional[str] = Query(None, description="Column name to order by"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Order direction")
):
    """
    Get encaissement records for preview tab with independent filtering support
    
    Returns paginated encaissement records with full details.
    All filters are independent from the overview filters.
    
    Parameters:
        page: Page number (default 1)
        page_size: Items per page (default 10, max 1000)
        All filter parameters are supported independently
    
    Returns:
        Dictionary with:
        - items: List of encaissement records
        - total: Total records matching filters
        - page: Current page number
        - page_size: Items per page
        - total_pages: Total number of pages
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")
    
    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))
        else:
            # User has no access, return empty result
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # Apply integer ID column filters
        if id:
            try:
                int_ids = [int(v) for v in id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if file_upload_id:
            try:
                int_ids = [int(v) for v in file_upload_id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.file_upload_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if dot_id:
            try:
                int_ids = [int(v) for v in dot_id if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.dot_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if n_fact:
            try:
                int_ids = [int(v) for v in n_fact if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.n_fact.in_(int_ids))
            except (ValueError, TypeError):
                pass

        # Apply string column filters
        if organisation:
            query = query.filter(EncaissementARDot.organisation.in_(organisation))
        if source:
            query = query.filter(EncaissementARDot.source.in_(source))
        if typ_fact:
            query = query.filter(EncaissementARDot.typ_fact.in_(typ_fact))
        if client:
            query = query.filter(EncaissementARDot.client.in_(client))
        if n_client:
            query = query.filter(EncaissementARDot.n_client.in_(n_client))
        if composite_key:
            query = query.filter(EncaissementARDot.composite_key.in_(composite_key))
        if anomaly_reason:
            query = query.filter(EncaissementARDot.anomaly_reason.in_(anomaly_reason))
        if termine_flag:
            query = query.filter(EncaissementARDot.termine_flag.in_(termine_flag))
        if creer_par:
            query = query.filter(EncaissementARDot.creer_par.in_(creer_par))
        if obj_fact:
            query = query.filter(EncaissementARDot.obj_fact.in_(obj_fact))
        if periode:
            query = query.filter(EncaissementARDot.periode.in_(periode))
        if ref:
            query = query.filter(EncaissementARDot.ref.in_(ref))

        # Apply date filters
        if date_fact_start:
            try:
                if len(date_fact_start) == 7:  # YYYY-MM format
                    start_date = datetime.strptime(date_fact_start, "%Y-%m").date()
                else:
                    start_date = datetime.strptime(date_fact_start, "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_fact >= start_date)
            except ValueError:
                logger.warning(f"Invalid date_fact_start format: {date_fact_start}")
        if date_fact_end:
            try:
                if len(date_fact_end) == 7:  # YYYY-MM format
                    from calendar import monthrange
                    year, month = map(int, date_fact_end.split('-'))
                    last_day = monthrange(year, month)[1]
                    end_date = datetime(year, month, last_day).date()
                else:
                    end_date = datetime.strptime(date_fact_end, "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_fact <= end_date)
            except ValueError:
                logger.warning(f"Invalid date_fact_end format: {date_fact_end}")
        if date_rglt_start:
            try:
                if len(date_rglt_start) == 7:  # YYYY-MM format
                    start_date = datetime.strptime(date_rglt_start, "%Y-%m").date()
                else:
                    start_date = datetime.strptime(date_rglt_start, "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_rglt >= start_date)
            except ValueError:
                logger.warning(f"Invalid date_rglt_start format: {date_rglt_start}")
        if date_rglt_end:
            try:
                if len(date_rglt_end) == 7:  # YYYY-MM format
                    from calendar import monthrange
                    year, month = map(int, date_rglt_end.split('-'))
                    last_day = monthrange(year, month)[1]
                    end_date = datetime(year, month, last_day).date()
                else:
                    end_date = datetime.strptime(date_rglt_end, "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_rglt <= end_date)
            except ValueError:
                logger.warning(f"Invalid date_rglt_end format: {date_rglt_end}")
        if mois:
            query = query.filter(EncaissementARDot.mois.in_(mois))

        # Apply numeric range filters
        if montant_ht_min is not None:
            query = query.filter(EncaissementARDot.montant_ht >= montant_ht_min)
        if montant_ht_max is not None:
            query = query.filter(EncaissementARDot.montant_ht <= montant_ht_max)
        if montant_taxe_min is not None:
            query = query.filter(EncaissementARDot.montant_taxe >= montant_taxe_min)
        if montant_taxe_max is not None:
            query = query.filter(EncaissementARDot.montant_taxe <= montant_taxe_max)
        if montant_ttc_min is not None:
            query = query.filter(EncaissementARDot.montant_ttc >= montant_ttc_min)
        if montant_ttc_max is not None:
            query = query.filter(EncaissementARDot.montant_ttc <= montant_ttc_max)
        if encaissement_min is not None:
            query = query.filter(EncaissementARDot.encaissement >= encaissement_min)
        if encaissement_max is not None:
            query = query.filter(EncaissementARDot.encaissement <= encaissement_max)
        if taux_encaissement_min is not None:
            query = query.filter(EncaissementARDot.taux_encaissement >= taux_encaissement_min)
        if taux_encaissement_max is not None:
            query = query.filter(EncaissementARDot.taux_encaissement <= taux_encaissement_max)
        if montant_restant_min is not None:
            query = query.filter(EncaissementARDot.montant_restant >= montant_restant_min)
        if montant_restant_max is not None:
            query = query.filter(EncaissementARDot.montant_restant <= montant_restant_max)

        # Apply boolean filters
        if is_duplicate is not None:
            bool_val = is_duplicate.lower() in ["true", "oui", "yes", "1"] if isinstance(is_duplicate, str) else bool(is_duplicate)
            query = query.filter(EncaissementARDot.is_duplicate == bool_val)
        if is_anomaly is not None:
            bool_val = is_anomaly.lower() in ["true", "oui", "yes", "1"] if isinstance(is_anomaly, str) else bool(is_anomaly)
            query = query.filter(EncaissementARDot.is_anomaly == bool_val)

        # Apply year filter
        if year and year != "all":
            try:
                if isinstance(year, str):
                    year_str_clean = year.strip()
                    if year_str_clean:
                        year_int = int(year_str_clean)
                    else:
                        year_int = None
                elif isinstance(year, (int, float)):
                    year_int = int(year)
                else:
                    year_int = None
                
                if year_int:
                    year_str = str(year_int)
                    query = query.filter(
                        or_(
                            extract('year', EncaissementARDot.date_fact) == year_int,
                            func.substring(EncaissementARDot.mois, 1, 4) == year_str
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid year format: {year}, error: {e}")

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    EncaissementARDot.client.ilike(search_term),
                    EncaissementARDot.n_fact.cast(String).ilike(search_term),
                    EncaissementARDot.organisation.ilike(search_term),
                    EncaissementARDot.n_client.ilike(search_term),
                    EncaissementARDot.source.ilike(search_term),
                    EncaissementARDot.obj_fact.ilike(search_term),
                    EncaissementARDot.ref.ilike(search_term)
                )
            )

        # Get total count for pagination
        total = query.count()

        # Apply ordering
        order_column = None
        if sort_by:
            column_map = {
                "id": EncaissementARDot.id,
                "organisation": EncaissementARDot.organisation,
                "n_fact": EncaissementARDot.n_fact,
                "date_fact": EncaissementARDot.date_fact,
                "date_rglt": EncaissementARDot.date_rglt,
                "montant_ht": EncaissementARDot.montant_ht,
                "montant_taxe": EncaissementARDot.montant_taxe,
                "montant_ttc": EncaissementARDot.montant_ttc,
                "encaissement": EncaissementARDot.encaissement,
                "taux_encaissement": EncaissementARDot.taux_encaissement,
                "montant_restant": EncaissementARDot.montant_restant,
                "created_at": EncaissementARDot.created_at,
            }
            order_column = column_map.get(sort_by)

        # Calculate pagination
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size

        # Apply ordering and pagination
        if order_column:
            if sort_order == "asc":
                records = query.order_by(order_column.asc(), EncaissementARDot.id.asc()) \
                    .offset(skip) \
                    .limit(page_size) \
                    .all()
            else:
                records = query.order_by(order_column.desc(), EncaissementARDot.id.desc()) \
                    .offset(skip) \
                    .limit(page_size) \
                    .all()
        else:
            # Default ordering
            records = query.order_by(EncaissementARDot.date_fact.desc(), EncaissementARDot.id.desc()) \
                .offset(skip) \
                .limit(page_size) \
                .all()

        # Convert to dict format with all columns
        items = []
        for record in records:
            items.append({
                "id": record.id,
                "file_upload_id": record.file_upload_id,
                "dot_id": record.dot_id,
                "organisation": record.organisation,
                "source": record.source,
                "n_fact": record.n_fact,
                "typ_fact": record.typ_fact,
                "date_fact": record.date_fact.isoformat() if record.date_fact else None,
                "mois": record.mois,
                "client": record.client,
                "n_client": record.n_client,
                "obj_fact": record.obj_fact,
                "periode": record.periode,
                "ref": record.ref,
                "termine_flag": record.termine_flag,
                "creer_par": record.creer_par,
                "montant_ht": float(record.montant_ht) if record.montant_ht else None,
                "montant_taxe": float(record.montant_taxe) if record.montant_taxe else None,
                "montant_ttc": float(record.montant_ttc) if record.montant_ttc else None,
                "chiffre_aff_exe": float(record.chiffre_aff_exe) if record.chiffre_aff_exe else None,
                "encaissement": float(record.encaissement) if record.encaissement else None,
                "n_rglt": record.n_rglt,
                "date_rglt": record.date_rglt.isoformat() if record.date_rglt else None,
                "facture_avoir_annulation": record.facture_avoir_annulation,
                "taux_encaissement": float(record.taux_encaissement) if record.taux_encaissement else None,
                "montant_restant": float(record.montant_restant) if record.montant_restant else None,
                "composite_key": record.composite_key,
                "is_duplicate": record.is_duplicate,
                "is_anomaly": record.is_anomaly,
                "anomaly_reason": record.anomaly_reason,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })

        logger.info(f"Preview data retrieved: {len(items)} items (page {page}/{total_pages}, total: {total})")

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    except Exception as e:
        logger.error(f"Error getting encaissement preview data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve preview data: {str(e)}")


# ============================================================================
# Enhanced Analytics Endpoints for Visualizations
# ============================================================================

@encaissement_analytics_router.get("/monthly-chart-data")
async def get_monthly_chart_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisations: Optional[str] = Query(None),
    mois: Optional[str] = Query(None),
    taux_min: Optional[float] = Query(None),
    taux_max: Optional[float] = Query(None)
):
    """
    Get monthly data for combined histogram (Encaissement & Montant TTC by month)

    Returns monthly aggregations for visualization with both encaissement and montant_ttc
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        query = db.query(EncaissementARDot)

        # Apply DOT filtering
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply filters
        if organisations:
            org_list = [o.strip() for o in organisations.split(',') if o.strip()]
            query = query.filter(EncaissementARDot.organisation.in_(org_list))

        if mois:
            mois_list = [m.strip() for m in mois.split(',') if m.strip()]
            query = query.filter(EncaissementARDot.mois.in_(mois_list))

        if taux_min is not None:
            query = query.filter(EncaissementARDot.taux_encaissement >= taux_min)
        if taux_max is not None:
            query = query.filter(EncaissementARDot.taux_encaissement <= taux_max)

        # Group by month
        results = query.with_entities(
            EncaissementARDot.mois,
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement')
        ).filter(
            EncaissementARDot.mois.isnot(None)
        ).group_by(
            EncaissementARDot.mois
        ).order_by(
            EncaissementARDot.mois
        ).all()

        data = []
        for row in results:
            data.append({
                "month": row.mois,
                "montant_ttc": float(row.total_montant_ttc or 0),
                "encaissement": float(row.total_encaissement or 0)
            })

        return {"data": data}

    except Exception as e:
        logger.error(f"Error getting monthly chart data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get monthly chart data: {str(e)}")


@encaissement_analytics_router.get("/monthly-pie-data")
async def get_monthly_pie_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisations: Optional[str] = Query(None),
    mois: Optional[str] = Query(None),
    taux_min: Optional[float] = Query(None),
    taux_max: Optional[float] = Query(None)
):
    """
    Get encaissement by month for 3D pie chart

    Returns monthly encaissement distribution for pie chart visualization
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        query = db.query(EncaissementARDot)

        # Apply DOT filtering
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply filters
        if organisations:
            org_list = [o.strip() for o in organisations.split(',') if o.strip()]
            query = query.filter(EncaissementARDot.organisation.in_(org_list))

        if mois:
            mois_list = [m.strip() for m in mois.split(',') if m.strip()]
            query = query.filter(EncaissementARDot.mois.in_(mois_list))

        if taux_min is not None:
            query = query.filter(EncaissementARDot.taux_encaissement >= taux_min)
        if taux_max is not None:
            query = query.filter(EncaissementARDot.taux_encaissement <= taux_max)

        # Group by month
        results = query.with_entities(
            EncaissementARDot.mois,
            func.sum(EncaissementARDot.encaissement).label('total_encaissement')
        ).filter(
            EncaissementARDot.mois.isnot(None)
        ).group_by(
            EncaissementARDot.mois
        ).order_by(
            EncaissementARDot.mois
        ).all()

        data = []
        for row in results:
            data.append({
                "name": row.mois,
                "value": float(row.total_encaissement or 0)
            })

        return {"data": data}

    except Exception as e:
        logger.error(f"Error getting monthly pie data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get monthly pie data: {str(e)}")


@encaissement_analytics_router.get("/dot-taux-data")
async def get_dot_taux_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    organisations: Optional[str] = Query(None),
    mois: Optional[str] = Query(None),
    taux_min: Optional[float] = Query(None),
    taux_max: Optional[float] = Query(None)
):
    """
    Get DOT and Taux d'encaissement data for histogram

    Returns collection rate by organization for bar chart visualization
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        query = db.query(EncaissementARDot)

        # Apply DOT filtering
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply filters
        if organisations:
            org_list = [o.strip() for o in organisations.split(',') if o.strip()]
            query = query.filter(EncaissementARDot.organisation.in_(org_list))

        if mois:
            mois_list = [m.strip() for m in mois.split(',') if m.strip()]
            query = query.filter(EncaissementARDot.mois.in_(mois_list))

        if taux_min is not None:
            query = query.filter(EncaissementARDot.taux_encaissement >= taux_min)
        if taux_max is not None:
            query = query.filter(EncaissementARDot.taux_encaissement <= taux_max)

        # Group by organisation
        results = query.with_entities(
            EncaissementARDot.organisation,
            func.sum(EncaissementARDot.montant_ttc).label('total_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement')
        ).filter(
            EncaissementARDot.organisation.isnot(None)
        ).group_by(
            EncaissementARDot.organisation
        ).order_by(
            func.sum(EncaissementARDot.montant_ttc).desc()
        ).all()

        data = []
        for row in results:
            total_ttc = float(row.total_ttc or 0)
            total_enc = float(row.total_encaissement or 0)
            taux = (total_enc / total_ttc * 100) if total_ttc > 0 else 0

            data.append({
                "organisation": row.organisation,
                "taux_encaissement": round(taux, 2)
            })

        return {"data": data}

    except Exception as e:
        logger.error(f"Error getting DOT taux data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get DOT taux data: {str(e)}")


# ============================================================================
# Export Endpoint with French Formatting
# ============================================================================

@encaissement_analytics_router.get("/export")
async def export_encaissement_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Support both parameter name formats for compatibility
    organisation: Optional[List[str]] = Query(None, description="Filter by organisation(s)"),
    organisations: Optional[str] = Query(None, description="Filter by organisations (comma-separated)"),
    # Date filters - support multiple formats
    date_fact_start: Optional[str] = Query(None, description="Start date (YYYY-MM or YYYY-MM-DD)"),
    date_fact_end: Optional[str] = Query(None, description="End date (YYYY-MM or YYYY-MM-DD)"),
    date_fact_from: Optional[date] = Query(None, description="Filter by date from (legacy)"),
    date_fact_to: Optional[date] = Query(None, description="Filter by date to (legacy)"),
    mois: Optional[str] = Query(None, description="Filter by month(s) (comma-separated YYYY-MM)"),
    # Date Règlement filters
    date_rglt_start: Optional[str] = Query(None, description="Date règlement start (YYYY-MM or YYYY-MM-DD)"),
    date_rglt_end: Optional[str] = Query(None, description="Date règlement end (YYYY-MM or YYYY-MM-DD)"),
    # Rate filters
    taux_encaissement_min: Optional[float] = Query(None, description="Minimum collection rate"),
    taux_encaissement_max: Optional[float] = Query(None, description="Maximum collection rate"),
    taux_min: Optional[float] = Query(None, description="Minimum collection rate (legacy)"),
    taux_max: Optional[float] = Query(None, description="Maximum collection rate (legacy)"),
    # Search filter
    search: Optional[str] = Query(None, description="Search in client, n_fact, or organisation"),
    # Year filter
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    # Type Fact filter
    typ_fact: Optional[List[str]] = Query(None, description="Filter by type facture(s)"),
    # Other filters
    include_duplicates: bool = Query(True, description="Include duplicate records"),
    include_anomalies: bool = Query(False, description="Include anomaly records (default: exclude)"),
    format: str = Query("xlsx", regex="^(xlsx|csv)$")
):
    """
    Export encaissement data with proper French formatting
    - Numeric values formatted with comma as decimal separator
    - Thousand separators
    - 2 decimal places
    - Supports all filter parameters
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        import pandas as pd
        from fastapi.responses import StreamingResponse
        import io
        from datetime import datetime

        query = db.query(EncaissementARDot)

        # Apply DOT filtering
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Normalize organisation parameter (support both List and comma-separated string)
        org_list = None
        if organisation:
            org_list = organisation
        elif organisations:
            org_list = [o.strip() for o in organisations.split(',') if o.strip()]
        
        # Normalize date parameters (prefer date_fact_start/end, fallback to date_fact_from/to)
        start_date = date_fact_start
        end_date = date_fact_end
        if not start_date and date_fact_from:
            start_date = date_fact_from.strftime("%Y-%m-%d")
        if not end_date and date_fact_to:
            end_date = date_fact_to.strftime("%Y-%m-%d")
        
        # Normalize taux parameters
        taux_min_val = taux_encaissement_min if taux_encaissement_min is not None else taux_min
        taux_max_val = taux_encaissement_max if taux_encaissement_max is not None else taux_max
        
        # Log export filters received
        logger.info(
            f"📤 [BACKEND EXPORT] Received export request with filters: "
            f"organisation={org_list}, "
            f"date_fact_start={start_date}, "
            f"date_fact_end={end_date}, "
            f"date_rglt_start={date_rglt_start}, "
            f"date_rglt_end={date_rglt_end}, "
            f"search={search}, "
            f"year={year} (type: {type(year)}), "
            f"typ_fact={typ_fact}, "
            f"taux_min={taux_min_val}, "
            f"taux_max={taux_max_val}, "
            f"format={format}"
        )
        
        # Apply filters using helper function (includes all filters: organisation, dates, search, year, typ_fact, date_rglt)
        query = apply_encaissement_filters(
            query,
            organisation=org_list,
            date_fact_start=start_date,
            date_fact_end=end_date,
            taux_encaissement_min=taux_min_val,
            taux_encaissement_max=taux_max_val,
            search=search,
            year=year,
            typ_fact=typ_fact,
            date_rglt_start=date_rglt_start,
            date_rglt_end=date_rglt_end
        )
        
        # Apply mois filter if provided (separate from date range)
        if mois:
            mois_list = [m.strip() for m in mois.split(',') if m.strip()]
            query = query.filter(EncaissementARDot.mois.in_(mois_list))
        
        # Apply duplicate/anomaly filters
        if not include_duplicates:
            query = query.filter(EncaissementARDot.is_duplicate == False)
        if not include_anomalies:
            query = query.filter(EncaissementARDot.is_anomaly == False)

        # Get records
        records = query.all()

        # Convert to DataFrame - include ALL columns from the model
        data = []
        for record in records:
            data.append({
                "ID": record.id,
                "Organisation": record.organisation,
                "Source": record.source,
                "N° Facture": record.n_fact,
                "Type Facture": record.typ_fact,
                "Date Facture": record.date_fact.strftime("%d/%m/%Y") if record.date_fact else "",
                "Mois": record.mois,
                "Client": record.client,
                "N° Client": record.n_client,
                "Objet Facture": record.obj_fact,
                "Période": record.periode,
                "Référence": record.ref,
                "Terminé": record.termine_flag,
                "Créé Par": record.creer_par,
                "Montant HT": float(record.montant_ht or 0),
                "Montant Taxe": float(record.montant_taxe or 0),
                "Montant TTC": float(record.montant_ttc or 0),
                "Chiffre Aff Exe": float(record.chiffre_aff_exe or 0),
                "Encaissement": float(record.encaissement or 0),
                "N° Règlement": record.n_rglt,
                "Date Règlement": record.date_rglt.strftime("%d/%m/%Y") if record.date_rglt else "",
                "Facture Avoir/Annulation": record.facture_avoir_annulation,
                "Taux Encaissement (%)": float(record.taux_encaissement or 0),
                "Montant Restant": float(record.montant_restant or 0),
                "Clé Composite": record.composite_key,
                "Est Duplicata": "Oui" if record.is_duplicate else "Non",
                "Est Anomalie": "Oui" if record.is_anomaly else "Non",
                "Raison Anomalie": record.anomaly_reason,
                "Date Création": record.created_at.strftime("%d/%m/%Y %H:%M:%S") if record.created_at else "",
                "Date Modification": record.updated_at.strftime("%d/%m/%Y %H:%M:%S") if record.updated_at else "",
            })

        df = pd.DataFrame(data)

        # Numeric columns that should be formatted as numbers
        numeric_cols = ["Montant HT", "Montant Taxe", "Montant TTC", "Chiffre Aff Exe",
                       "Encaissement", "Taux Encaissement (%)", "Montant Restant"]

        # Export based on format
        if format == "xlsx":
            # For Excel: Keep numbers as numbers, apply Excel number formatting
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="Encaissement AR DOT")
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets["Encaissement AR DOT"]
                
                # Import openpyxl styles
                from openpyxl.styles import NamedStyle
                from openpyxl.styles.numbers import FORMAT_NUMBER_00
                
                # Apply French number formatting (space for thousands, comma for decimal)
                # French format: # ##0,00 (space thousands separator, comma decimal separator)
                french_number_format = '# ##0,00'
                
                for col_idx, col_name in enumerate(df.columns, start=1):
                    if col_name in numeric_cols:
                        for row_idx in range(2, len(df) + 2):  # Start from row 2 (row 1 is header)
                            cell = worksheet.cell(row=row_idx, column=col_idx)
                            if cell.value is not None and cell.value != "":
                                cell.number_format = french_number_format
            output.seek(0)

            filename = f"encaissement_ar_dot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:  # CSV
            # Format numbers with French formatting (space thousands, comma decimal) for CSV
            def format_french_number(x):
                """Format number with French formatting: space for thousands, comma for decimal"""
                if pd.isna(x) or not isinstance(x, (int, float)):
                    return x
                formatted = f"{x:,.2f}"
                if '.' in formatted:
                    int_part, dec_part = formatted.rsplit('.', 1)
                    int_part_clean = int_part.replace(',', '')
                    int_part_formatted = ''
                    for i, digit in enumerate(reversed(int_part_clean)):
                        if i > 0 and i % 3 == 0:
                            int_part_formatted = ' ' + int_part_formatted
                        int_part_formatted = digit + int_part_formatted
                    return int_part_formatted + ',' + dec_part
                else:
                    int_part_clean = formatted.replace(',', '')
                    int_part_formatted = ''
                    for i, digit in enumerate(reversed(int_part_clean)):
                        if i > 0 and i % 3 == 0:
                            int_part_formatted = ' ' + int_part_formatted
                        int_part_formatted = digit + int_part_formatted
                    return int_part_formatted + ',00'
            
            output = io.StringIO()
            df_formatted = df.copy()
            for col in numeric_cols:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(format_french_number)
            
            # Export CSV with semicolon separator and French number formatting
            df_formatted.to_csv(output, index=False, sep=";", encoding="utf-8-sig")
            output.seek(0)

            filename = f"encaissement_ar_dot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )

    except Exception as e:
        logger.error(f"Error exporting encaissement data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


# ============================================================================
# Async Export Endpoints (Background Processing)
# ============================================================================

def _run_encaissement_export_background(task_id: str, export_params: dict):
    """Background worker for encaissement export with progress updates"""
    from database.connection import SessionLocal

    db = SessionLocal()

    try:
        # Send initial progress
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "started",
            "progress": 0,
            "message": "Starting export..."
        }))

        export_tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "file_path": None,
            "filename": None,
            "error": None,
            "start_time": datetime.utcnow().isoformat()
        }

        # Extract parameters
        format = export_params["format"]
        user_id = export_params["user_id"]

        # Build query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, user_id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))
        else:
            # User has no access, return empty result
            export_tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "filename": f"encaissement_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}",
                "file_path": None,
                "record_count": 0
            })
            asyncio.run(processing_ws_manager.send_task_update(task_id, {
                "status": "completed",
                "progress": 100,
                "message": "Export completed (no data)",
                "filename": export_tasks[task_id]["filename"],
                "download_url": f"/api/encaissement/export-download/{task_id}"
            }))
            return

        # Apply filters using same logic as preview-data endpoint
        # Apply integer ID column filters
        if export_params.get("id"):
            try:
                int_ids = [int(v) for v in export_params["id"] if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if export_params.get("file_upload_id"):
            try:
                int_ids = [int(v) for v in export_params["file_upload_id"] if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.file_upload_id.in_(int_ids))
            except (ValueError, TypeError):
                pass
        if export_params.get("dot_id"):
            try:
                int_ids = [int(v) for v in export_params["dot_id"] if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.dot_id.in_(int_ids))
            except (ValueError, TypeError):
                pass

        # Apply string column filters
        if export_params.get("organisation"):
            query = query.filter(EncaissementARDot.organisation.in_(export_params["organisation"]))
        if export_params.get("source"):
            query = query.filter(EncaissementARDot.source.in_(export_params["source"]))
        if export_params.get("typ_fact"):
            query = query.filter(EncaissementARDot.typ_fact.in_(export_params["typ_fact"]))
        if export_params.get("client"):
            query = query.filter(EncaissementARDot.client.in_(export_params["client"]))
        if export_params.get("n_client"):
            query = query.filter(EncaissementARDot.n_client.in_(export_params["n_client"]))
        if export_params.get("n_fact"):
            try:
                int_ids = [int(v) for v in export_params["n_fact"] if v and str(v).isdigit()]
                if int_ids:
                    query = query.filter(EncaissementARDot.n_fact.in_(int_ids))
            except (ValueError, TypeError):
                pass

        # Apply date filters
        if export_params.get("date_fact_start"):
            try:
                if len(export_params["date_fact_start"]) == 7:  # YYYY-MM format
                    start_date = datetime.strptime(export_params["date_fact_start"], "%Y-%m").date()
                else:
                    start_date = datetime.strptime(export_params["date_fact_start"], "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_fact >= start_date)
            except ValueError:
                logger.warning(f"Invalid date_fact_start format: {export_params['date_fact_start']}")
        if export_params.get("date_fact_end"):
            try:
                if len(export_params["date_fact_end"]) == 7:  # YYYY-MM format
                    from calendar import monthrange
                    year, month = map(int, export_params["date_fact_end"].split('-'))
                    last_day = monthrange(year, month)[1]
                    end_date = datetime(year, month, last_day).date()
                else:
                    end_date = datetime.strptime(export_params["date_fact_end"], "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_fact <= end_date)
            except ValueError:
                logger.warning(f"Invalid date_fact_end format: {export_params['date_fact_end']}")
        if export_params.get("date_rglt_start"):
            try:
                if len(export_params["date_rglt_start"]) == 7:  # YYYY-MM format
                    start_date = datetime.strptime(export_params["date_rglt_start"], "%Y-%m").date()
                else:
                    start_date = datetime.strptime(export_params["date_rglt_start"], "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_rglt >= start_date)
            except ValueError:
                logger.warning(f"Invalid date_rglt_start format: {export_params['date_rglt_start']}")
        if export_params.get("date_rglt_end"):
            try:
                if len(export_params["date_rglt_end"]) == 7:  # YYYY-MM format
                    from calendar import monthrange
                    year, month = map(int, export_params["date_rglt_end"].split('-'))
                    last_day = monthrange(year, month)[1]
                    end_date = datetime(year, month, last_day).date()
                else:
                    end_date = datetime.strptime(export_params["date_rglt_end"], "%Y-%m-%d").date()
                query = query.filter(EncaissementARDot.date_rglt <= end_date)
            except ValueError:
                logger.warning(f"Invalid date_rglt_end format: {export_params['date_rglt_end']}")
        if export_params.get("mois"):
            query = query.filter(EncaissementARDot.mois.in_(export_params["mois"]))

        # Apply numeric range filters
        if export_params.get("montant_ht_min") is not None:
            query = query.filter(EncaissementARDot.montant_ht >= export_params["montant_ht_min"])
        if export_params.get("montant_ht_max") is not None:
            query = query.filter(EncaissementARDot.montant_ht <= export_params["montant_ht_max"])
        if export_params.get("montant_taxe_min") is not None:
            query = query.filter(EncaissementARDot.montant_taxe >= export_params["montant_taxe_min"])
        if export_params.get("montant_taxe_max") is not None:
            query = query.filter(EncaissementARDot.montant_taxe <= export_params["montant_taxe_max"])
        if export_params.get("montant_ttc_min") is not None:
            query = query.filter(EncaissementARDot.montant_ttc >= export_params["montant_ttc_min"])
        if export_params.get("montant_ttc_max") is not None:
            query = query.filter(EncaissementARDot.montant_ttc <= export_params["montant_ttc_max"])
        if export_params.get("encaissement_min") is not None:
            query = query.filter(EncaissementARDot.encaissement >= export_params["encaissement_min"])
        if export_params.get("encaissement_max") is not None:
            query = query.filter(EncaissementARDot.encaissement <= export_params["encaissement_max"])
        if export_params.get("taux_encaissement_min") is not None:
            query = query.filter(EncaissementARDot.taux_encaissement >= export_params["taux_encaissement_min"])
        if export_params.get("taux_encaissement_max") is not None:
            query = query.filter(EncaissementARDot.taux_encaissement <= export_params["taux_encaissement_max"])
        if export_params.get("montant_restant_min") is not None:
            query = query.filter(EncaissementARDot.montant_restant >= export_params["montant_restant_min"])
        if export_params.get("montant_restant_max") is not None:
            query = query.filter(EncaissementARDot.montant_restant <= export_params["montant_restant_max"])

        # Apply boolean filters
        if export_params.get("is_duplicate") is not None:
            bool_val = export_params["is_duplicate"].lower() in ["true", "oui", "yes", "1"] if isinstance(export_params["is_duplicate"], str) else bool(export_params["is_duplicate"])
            query = query.filter(EncaissementARDot.is_duplicate == bool_val)
        if export_params.get("is_anomaly") is not None:
            bool_val = export_params["is_anomaly"].lower() in ["true", "oui", "yes", "1"] if isinstance(export_params["is_anomaly"], str) else bool(export_params["is_anomaly"])
            query = query.filter(EncaissementARDot.is_anomaly == bool_val)
        elif not export_params.get("include_anomalies", False):
            # Default: exclude anomalies from export
            query = query.filter(EncaissementARDot.is_anomaly == False)

        # Apply year filter
        if export_params.get("year") and export_params.get("year") != "all":
            try:
                year = export_params["year"]
                if isinstance(year, str):
                    year_str_clean = year.strip()
                    if year_str_clean:
                        year_int = int(year_str_clean)
                    else:
                        year_int = None
                elif isinstance(year, (int, float)):
                    year_int = int(year)
                else:
                    year_int = None
                
                if year_int:
                    year_str = str(year_int)
                    query = query.filter(
                        or_(
                            extract('year', EncaissementARDot.date_fact) == year_int,
                            func.substring(EncaissementARDot.mois, 1, 4) == year_str
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid year format: {export_params.get('year')}, error: {e}")

        # Apply search filter
        if export_params.get("search"):
            search_term = f"%{export_params['search']}%"
            query = query.filter(
                or_(
                    EncaissementARDot.client.ilike(search_term),
                    EncaissementARDot.n_fact.cast(String).ilike(search_term),
                    EncaissementARDot.organisation.ilike(search_term),
                    EncaissementARDot.n_client.ilike(search_term),
                    EncaissementARDot.source.ilike(search_term),
                    EncaissementARDot.obj_fact.ilike(search_term),
                    EncaissementARDot.ref.ilike(search_term)
                )
            )

        # Get total count (10%)
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "processing",
            "progress": 10,
            "message": "Counting records..."
        }))

        total_count = query.count()
        if total_count == 0:
            raise Exception("No data found with applied filters")

        # Apply ordering if provided
        if export_params.get("sort_by"):
            sort_column = getattr(EncaissementARDot, export_params["sort_by"], None)
            if sort_column is not None:
                sort_direction = export_params.get("sort_order", "asc")
                if sort_direction == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

        # Fetch all records (20-70%)
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "processing",
            "progress": 20,
            "message": f"Fetching {total_count:,} records..."
        }))

        records = query.all()

        # Convert to DataFrame (70-85%)
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "processing",
            "progress": 70,
            "message": "Processing data..."
        }))

        data = []
        for idx, record in enumerate(records):
            if idx % 1000 == 0 and idx > 0:
                progress = 70 + int((idx / len(records)) * 10)
                asyncio.run(processing_ws_manager.send_task_update(task_id, {
                    "status": "processing",
                    "progress": progress,
                    "message": f"Processing record {idx:,} of {len(records):,}..."
                }))

            data.append({
                "ID": record.id,
                "Organisation": record.organisation,
                "Source": record.source,
                "N° Facture": record.n_fact,
                "Type Facture": record.typ_fact,
                "Date Facture": record.date_fact.strftime("%d/%m/%Y") if record.date_fact else "",
                "Mois": record.mois,
                "Client": record.client,
                "N° Client": record.n_client,
                "Objet Facture": record.obj_fact,
                "Période": record.periode,
                "Référence": record.ref,
                "Terminé": record.termine_flag,
                "Créé Par": record.creer_par,
                "Montant HT": float(record.montant_ht or 0),
                "Montant Taxe": float(record.montant_taxe or 0),
                "Montant TTC": float(record.montant_ttc or 0),
                "Chiffre Aff Exe": float(record.chiffre_aff_exe or 0),
                "Encaissement": float(record.encaissement or 0),
                "N° Règlement": record.n_rglt,
                "Date Règlement": record.date_rglt.strftime("%d/%m/%Y") if record.date_rglt else "",
                "Facture Avoir/Annulation": record.facture_avoir_annulation,
                "Taux Encaissement (%)": float(record.taux_encaissement or 0),
                "Montant Restant": float(record.montant_restant or 0),
                "Clé Composite": record.composite_key,
                "Est Duplicata": "Oui" if record.is_duplicate else "Non",
                "Est Anomalie": "Oui" if record.is_anomaly else "Non",
                "Raison Anomalie": record.anomaly_reason,
                "Date Création": record.created_at.strftime("%d/%m/%Y %H:%M:%S") if record.created_at else "",
                "Date Modification": record.updated_at.strftime("%d/%m/%Y %H:%M:%S") if record.updated_at else "",
            })

        df = pd.DataFrame(data)

        # Create file (85-95%)
        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "processing",
            "progress": 85,
            "message": "Creating export file..."
        }))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"encaissement_ar_dot_{timestamp}"

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format}')
        if format == "xlsx":
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Encaissement AR DOT')
                
                # Apply French number formatting (space for thousands, comma for decimal)
                workbook = writer.book
                worksheet = writer.sheets['Encaissement AR DOT']
                
                numeric_cols = ["Montant HT", "Montant Taxe", "Montant TTC", "Chiffre Aff Exe",
                               "Encaissement", "Taux Encaissement (%)", "Montant Restant"]
                
                # French format: # ##0,00 (space thousands separator, comma decimal separator)
                french_number_format = '# ##0,00'
                
                for col_idx, col_name in enumerate(df.columns, start=1):
                    if col_name in numeric_cols:
                        for row_idx in range(2, len(df) + 2):
                            cell = worksheet.cell(row=row_idx, column=col_idx)
                            if cell.value is not None and cell.value != "":
                                cell.number_format = french_number_format
            
            filename = f"{base_filename}.xlsx"
        else:
            # Format numbers with French formatting (space thousands, comma decimal) for CSV
            def format_french_number(x):
                """Format number with French formatting: space for thousands, comma for decimal"""
                if pd.isna(x) or not isinstance(x, (int, float)):
                    return x
                formatted = f"{x:,.2f}"
                if '.' in formatted:
                    int_part, dec_part = formatted.rsplit('.', 1)
                    int_part_clean = int_part.replace(',', '')
                    int_part_formatted = ''
                    for i, digit in enumerate(reversed(int_part_clean)):
                        if i > 0 and i % 3 == 0:
                            int_part_formatted = ' ' + int_part_formatted
                        int_part_formatted = digit + int_part_formatted
                    return int_part_formatted + ',' + dec_part
                else:
                    int_part_clean = formatted.replace(',', '')
                    int_part_formatted = ''
                    for i, digit in enumerate(reversed(int_part_clean)):
                        if i > 0 and i % 3 == 0:
                            int_part_formatted = ' ' + int_part_formatted
                        int_part_formatted = digit + int_part_formatted
                    return int_part_formatted + ',00'
            
            df_formatted = df.copy()
            numeric_cols = ["Montant HT", "Montant Taxe", "Montant TTC", "Chiffre Aff Exe",
                           "Encaissement", "Taux Encaissement (%)", "Montant Restant"]
            for col in numeric_cols:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(format_french_number)
            df_formatted.to_csv(temp_file.name, index=False, sep=";", encoding='utf-8-sig')
            filename = f"{base_filename}.csv"

        export_tasks[task_id].update({
            "file_path": temp_file.name,
            "filename": filename,
            "record_count": len(records)
        })

        # Completed
        export_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "end_time": datetime.utcnow().isoformat()
        })

        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "completed",
            "progress": 100,
            "message": "Export completed successfully!",
            "filename": filename,
            "download_url": f"/api/encaissement/export-download/{task_id}"
        }))

    except Exception as e:
        logger.error(f"Export error for task {task_id}: {e}", exc_info=True)
        export_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "end_time": datetime.utcnow().isoformat()
        })

        asyncio.run(processing_ws_manager.send_task_update(task_id, {
            "status": "failed",
            "progress": 0,
            "message": f"Export failed: {str(e)}"
        }))

    finally:
        db.close()


@encaissement_analytics_router.post("/export-async")
async def export_encaissement_data_async(
    format: str = Query("xlsx", regex="^(xlsx|csv)$"),
    # Column filters - all columns from ENCAISSEMENT_COLUMNS (same as preview-data)
    id: Optional[List[str]] = Query(None),
    file_upload_id: Optional[List[str]] = Query(None),
    dot_id: Optional[List[str]] = Query(None),
    organisation: Optional[List[str]] = Query(None),
    source: Optional[List[str]] = Query(None),
    n_fact: Optional[List[str]] = Query(None),
    typ_fact: Optional[List[str]] = Query(None),
    client: Optional[List[str]] = Query(None),
    n_client: Optional[List[str]] = Query(None),
    # Date filters
    date_fact_start: Optional[str] = Query(None),
    date_fact_end: Optional[str] = Query(None),
    date_rglt_start: Optional[str] = Query(None),
    date_rglt_end: Optional[str] = Query(None),
    mois: Optional[List[str]] = Query(None),
    # Numeric range filters
    montant_ht_min: Optional[float] = Query(None),
    montant_ht_max: Optional[float] = Query(None),
    montant_taxe_min: Optional[float] = Query(None),
    montant_taxe_max: Optional[float] = Query(None),
    montant_ttc_min: Optional[float] = Query(None),
    montant_ttc_max: Optional[float] = Query(None),
    encaissement_min: Optional[float] = Query(None),
    encaissement_max: Optional[float] = Query(None),
    taux_encaissement_min: Optional[float] = Query(None),
    taux_encaissement_max: Optional[float] = Query(None),
    montant_restant_min: Optional[float] = Query(None),
    montant_restant_max: Optional[float] = Query(None),
    # Boolean filters
    is_duplicate: Optional[str] = Query(None),
    is_anomaly: Optional[str] = Query(None),
    include_anomalies: bool = Query(False, description="Include anomaly records (default: exclude)"),
    # Search
    search: Optional[str] = Query(None),
    # Year filter
    year: Optional[str] = Query(None),
    # Sorting
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start async export with progress tracking - returns task_id for monitoring"""
    PermissionService.require_permission(
        current_user, db, "can_export_analytics")

    logger.info(f"🔍 [BACKEND /export-async] Received params: organisation={organisation}, format={format}")

    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Store export parameters (matching preview-data endpoint structure)
    export_params = {
        "format": format,
        "id": id,
        "file_upload_id": file_upload_id,
        "dot_id": dot_id,
        "organisation": organisation,
        "source": source,
        "n_fact": n_fact,
        "typ_fact": typ_fact,
        "client": client,
        "n_client": n_client,
        "date_fact_start": date_fact_start,
        "date_fact_end": date_fact_end,
        "date_rglt_start": date_rglt_start,
        "date_rglt_end": date_rglt_end,
        "mois": mois if mois else None,  # Already a list
        "montant_ht_min": montant_ht_min,
        "montant_ht_max": montant_ht_max,
        "montant_taxe_min": montant_taxe_min,
        "montant_taxe_max": montant_taxe_max,
        "montant_ttc_min": montant_ttc_min,
        "montant_ttc_max": montant_ttc_max,
        "encaissement_min": encaissement_min,
        "encaissement_max": encaissement_max,
        "taux_encaissement_min": taux_encaissement_min,
        "taux_encaissement_max": taux_encaissement_max,
        "montant_restant_min": montant_restant_min,
        "montant_restant_max": montant_restant_max,
        "is_duplicate": is_duplicate,
        "is_anomaly": is_anomaly,
        "include_anomalies": include_anomalies,
        "search": search,
        "year": year,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "user_id": current_user.id
    }

    # Start background export
    thread = threading.Thread(
        target=_run_encaissement_export_background,
        args=(task_id, export_params),
        daemon=True
    )
    thread.start()

    return {
        "success": True,
        "task_id": task_id,
        "message": "Export started in background"
    }


@encaissement_analytics_router.get("/export-status/{task_id}")
async def get_encaissement_export_status(task_id: str):
    """Get export task status"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = export_tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "filename": task.get("filename"),
        "error": task.get("error"),
        "start_time": task.get("start_time"),
        "end_time": task.get("end_time"),
        "record_count": task.get("record_count"),
        "download_url": f"/api/encaissement/export-download/{task_id}" if task["status"] == "completed" else None
    }


@encaissement_analytics_router.get("/export-download/{task_id}")
async def download_encaissement_export_file(task_id: str):
    """Download completed export file"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = export_tasks[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Export not completed yet")

    if not task.get("file_path") or not os.path.exists(task["file_path"]):
        raise HTTPException(status_code=404, detail="Export file not found")

    # Determine media type
    filename = task["filename"]
    if filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "text/csv"

    # Return file
    def iterfile():
        with open(task["file_path"], mode="rb") as file:
            yield from file

    return StreamingResponse(
        iterfile(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# Pivot Table Endpoint
# ============================================================================

@encaissement_analytics_router.get("/pivot", response_model=EncaissementPivotResponse)
async def get_pivot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    group_by: str = Query("organisation", regex="^(organisation|month|type|org_month)$"),
    metric: str = Query("montant_ttc", regex="^(montant_ttc|encaissement|taux|count)$"),
    organisation: Optional[List[str]] = Query(None),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    Get encaissement data as a pivot table with dynamic grouping

    Supports pivot operations on encaissement data with flexible grouping dimensions.

    Parameters:
    - group_by: Grouping dimension (organisation, month, type, org_month)
    - metric: Metric to aggregate (montant_ttc, encaissement, taux, count)
    - organisation: Optional list of organizations to filter
    - start_date: Optional start date
    - end_date: Optional end date

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build base query
        query = db.query(EncaissementARDot)

        # Apply DOT filtering based on module-specific access
        accessible_dot_ids = DOTService.get_user_accessible_dots(
            db, current_user.id, module=MODULE_ENCAISSEMENT_AR_DOT
        )
        if accessible_dot_ids:
            query = query.filter(EncaissementARDot.dot_id.in_(accessible_dot_ids))

        # Apply filters
        if organisation:
            query = query.filter(EncaissementARDot.organisation.in_(organisation))
        if start_date:
            query = query.filter(EncaissementARDot.date_fact >= start_date)
        if end_date:
            query = query.filter(EncaissementARDot.date_fact <= end_date)

        records = query.all()

        # Initialize pivot data structure
        pivot_data = {}
        summary = {}

        # Metric definitions
        metric_config = {
            "montant_ttc": lambda x: sum(float(r.montant_ttc or 0) for r in x),
            "encaissement": lambda x: sum(float(r.encaissement or 0) for r in x),
            "taux": lambda x: sum(float(r.taux_encaissement or 0) for r in x) / len(x) if x else 0,
            "count": lambda x: len(x)
        }

        metric_func = metric_config[metric]

        # Group by organisation
        if group_by == "organisation":
            dimensions = ["organisation"]
            grouped = {}
            for record in records:
                key = record.organisation or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys()):
                value = metric_func(grouped[key])
                pivot_data[key] = float(value) if not isinstance(value, float) else value

            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values) if metric != "taux" else (sum(all_values) / len(all_values) if all_values else 0)

        # Group by month
        elif group_by == "month":
            from collections import defaultdict
            dimensions = ["month"]
            grouped = defaultdict(list)

            for record in records:
                if record.mois:
                    grouped[record.mois].append(record)

            for month in sorted(grouped.keys()):
                value = metric_func(grouped[month])
                pivot_data[month] = float(value) if not isinstance(value, float) else value

            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values) if metric != "taux" else (sum(all_values) / len(all_values) if all_values else 0)

        # Group by type
        elif group_by == "type":
            dimensions = ["type"]
            grouped = {}
            for record in records:
                key = record.typ_fact or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys()):
                value = metric_func(grouped[key])
                pivot_data[key] = float(value) if not isinstance(value, float) else value

            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values) if metric != "taux" else (sum(all_values) / len(all_values) if all_values else 0)

        # Group by org AND month (two-dimensional pivot)
        elif group_by == "org_month":
            from collections import defaultdict
            dimensions = ["organisation", "month"]
            grouped = defaultdict(lambda: defaultdict(list))

            for record in records:
                org = record.organisation or "Unknown"
                if record.mois:
                    grouped[org][record.mois].append(record)

            for org in sorted(grouped.keys()):
                pivot_data[org] = {}
                for month in sorted(grouped[org].keys()):
                    value = metric_func(grouped[org][month])
                    pivot_data[org][month] = float(value) if not isinstance(value, float) else value

            all_values = []
            for org_data in pivot_data.values():
                if isinstance(org_data, dict):
                    all_values.extend(org_data.values())

            summary[metric] = sum(all_values) if metric != "taux" else (sum(all_values) / len(all_values) if all_values else 0)

        logger.info(f"Generated pivot: group_by={group_by}, metric={metric}")

        return {
            "dimensions": dimensions,
            "aggregations": [metric],
            "data": pivot_data,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error generating encaissement pivot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate pivot: {str(e)}")
