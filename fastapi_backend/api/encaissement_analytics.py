"""
Encaissement AR DOT Analytics API Endpoints
Handles data retrieval, filtering, and aggregations for encaissement (collection) data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
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
from datetime import date
import logging

logger = logging.getLogger(__name__)

encaissement_analytics_router = APIRouter(tags=["Encaissement Analytics"])


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
    if year and year != "all" and year.strip():
        try:
            year_int = int(year)
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
    - search: Optional search term for client, n_fact, or organisation

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

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

            response.append(EncaissementByOrgResponse(
                organisation=row.organisation or "Unknown",
                nombre_factures=int(row.nombre_factures),
                total_montant_ttc=total_ttc,
                total_encaissement=total_encaissement,
                taux_encaissement_moyen=float(row.taux_moyen or 0),
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
    # Rate filters
    taux_encaissement_min: Optional[float] = Query(None, description="Minimum collection rate"),
    taux_encaissement_max: Optional[float] = Query(None, description="Maximum collection rate"),
    taux_min: Optional[float] = Query(None, description="Minimum collection rate (legacy)"),
    taux_max: Optional[float] = Query(None, description="Maximum collection rate (legacy)"),
    # Search filter
    search: Optional[str] = Query(None, description="Search in client, n_fact, or organisation"),
    # Year filter
    year: Optional[str] = Query(None, description="Filter by year (YYYY)"),
    # Other filters
    include_duplicates: bool = Query(True, description="Include duplicate records"),
    include_anomalies: bool = Query(True, description="Include anomaly records"),
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
        
        # Apply filters using helper function
        query = apply_encaissement_filters(
            query,
            organisation=org_list,
            date_fact_start=start_date,
            date_fact_end=end_date,
            taux_encaissement_min=taux_min_val,
            taux_encaissement_max=taux_max_val,
            search=search,
            year=year
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
                
                # Apply number formatting to numeric columns
                for col_idx, col_name in enumerate(df.columns, start=1):
                    if col_name in numeric_cols:
                        # Apply number format with 2 decimals and French locale (comma for decimal)
                        # Use Excel's built-in number format
                        for row_idx in range(2, len(df) + 2):  # Start from row 2 (row 1 is header)
                            cell = worksheet.cell(row=row_idx, column=col_idx)
                            if cell.value is not None and cell.value != "":
                                # Set as number format with 2 decimals
                                cell.number_format = '#,##0.00'  # Excel format: thousands separator, 2 decimals
            output.seek(0)

            filename = f"encaissement_ar_dot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:  # CSV
            # For CSV: Keep raw numeric values as numbers (not strings)
            # Use semicolon separator and period for decimal (standard CSV numeric format)
            output = io.StringIO()
            # Ensure numeric columns remain as numbers in CSV
            for col in numeric_cols:
                if col in df.columns:
                    # Convert to numeric, handling any errors
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Export CSV with semicolon separator and period for decimal (standard numeric format)
            df.to_csv(output, index=False, sep=";", encoding="utf-8-sig", float_format='%.2f')
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
