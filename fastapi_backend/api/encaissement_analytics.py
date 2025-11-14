"""
Encaissement AR DOT Analytics API Endpoints
Handles data retrieval, filtering, and aggregations for encaissement (collection) data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.encaissement import EncaissementARDot
from services.permission_service import PermissionService
from core.security import get_current_user
from pydantic import BaseModel
from datetime import date
import logging

logger = logging.getLogger(__name__)

encaissement_analytics_router = APIRouter(prefix="/api/encaissement", tags=["Encaissement Analytics"])


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


class EncaissementOverviewResponse(BaseModel):
    """Response schema for overview analytics"""
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_encaissement_global: float
    nombre_factures_total: int
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


# ============================================================================
# Overview Endpoint
# ============================================================================

@encaissement_analytics_router.get("/overview", response_model=EncaissementOverviewResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get overview analytics for encaissement data

    Returns key metrics including total amounts, collection rate, and distributions
    by organization and month.

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(EncaissementARDot)

        # Get totals
        total_montant_ttc = query.with_entities(
            func.sum(EncaissementARDot.montant_ttc)
        ).scalar() or 0.0

        total_encaissement = query.with_entities(
            func.sum(EncaissementARDot.encaissement)
        ).scalar() or 0.0

        total_montant_restant = total_montant_ttc - total_encaissement

        # Global collection rate
        taux_global = (total_encaissement / total_montant_ttc * 100) if total_montant_ttc > 0 else 0.0

        # Number of records
        nombre_factures = query.count()

        # Number of unique organizations
        nombre_organisations = query.with_entities(
            func.count(func.distinct(EncaissementARDot.organisation))
        ).scalar() or 0

        # By organization
        org_data = db.query(
            EncaissementARDot.organisation,
            func.sum(EncaissementARDot.montant_ttc).label('total')
        ).filter(EncaissementARDot.organisation.isnot(None)).group_by(
            EncaissementARDot.organisation
        ).order_by(func.sum(EncaissementARDot.montant_ttc).desc()).all()

        by_organisation = {row.organisation: float(row.total or 0) for row in org_data}

        # By month
        month_data = db.query(
            EncaissementARDot.mois,
            func.sum(EncaissementARDot.montant_ttc).label('total')
        ).filter(EncaissementARDot.mois.isnot(None)).group_by(
            EncaissementARDot.mois
        ).order_by(EncaissementARDot.mois).all()

        by_month = {row.mois: float(row.total or 0) for row in month_data}

        logger.info(f"Overview retrieved: Total TTC={total_montant_ttc}, Collection Rate={taux_global:.2f}%")

        return {
            "total_montant_ttc": float(total_montant_ttc),
            "total_encaissement": float(total_encaissement),
            "total_montant_restant": float(total_montant_restant),
            "taux_encaissement_global": float(taux_global),
            "nombre_factures_total": nombre_factures,
            "nombre_organisations": nombre_organisations,
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
    limit: Optional[int] = Query(None, ge=1, le=100)
):
    """
    Get encaissement data grouped by organization

    Returns organization-level aggregations with collection rates and outstanding amounts.

    Parameters:
    - sort_by: Sort field (organisation, factures, montant_ttc, encaissement, taux)
    - order: Sort order (asc, desc)
    - limit: Maximum number of results

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        results = db.query(
            EncaissementARDot.organisation,
            func.count(EncaissementARDot.id).label('nombre_factures'),
            func.sum(EncaissementARDot.montant_ttc).label('total_montant_ttc'),
            func.sum(EncaissementARDot.encaissement).label('total_encaissement'),
            func.avg(EncaissementARDot.taux_encaissement).label('taux_moyen')
        ).filter(
            EncaissementARDot.organisation.isnot(None)
        ).group_by(
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
        # Get unique organisations
        org_results = db.query(
            EncaissementARDot.organisation
        ).distinct().filter(
            EncaissementARDot.organisation.isnot(None)
        ).order_by(EncaissementARDot.organisation).all()

        organisations = [row.organisation for row in org_results]

        # Get unique months
        month_results = db.query(
            EncaissementARDot.mois
        ).distinct().filter(
            EncaissementARDot.mois.isnot(None)
        ).order_by(EncaissementARDot.mois).all()

        mois = [row.mois for row in month_results if row.mois]

        # Get unique invoice types
        type_results = db.query(
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
