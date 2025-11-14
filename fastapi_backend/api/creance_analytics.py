"""
Créance Périodique DOT Analytics API Endpoints
Handles data retrieval, filtering, and aggregations for créance (periodic debt) data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.creance import CreancePeriodiqueDot
from services.permission_service import PermissionService
from core.security import get_current_user
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

creance_analytics_router = APIRouter(prefix="/api/creance", tags=["Créance Analytics"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class CreanceRecordResponse(BaseModel):
    """Response schema for individual créance records"""
    id: int
    dot: Optional[str]
    period_key: Optional[str]
    produit: Optional[str]
    creance_net: Optional[float]
    creance_brut: Optional[float]
    open_amt: Optional[float]
    invoice_amt: Optional[float]

    class Config:
        from_attributes = True


class CreanceByDotResponse(BaseModel):
    """Response schema for DOT-level aggregations"""
    dot: str
    nombre_lignes: int
    total_creance_brut: float
    total_creance_net: float
    total_open_amt: float
    taux_creance: Optional[float]


class CreanceByYearResponse(BaseModel):
    """Response schema for year-level aggregations"""
    annee: str
    nombre_lignes: int
    total_creance_brut: float
    total_creance_net: float
    total_open_amt: float


class CreanceByProductResponse(BaseModel):
    """Response schema for product-level aggregations"""
    produit: str
    nombre_lignes: int
    total_creance_brut: float
    total_creance_net: float
    taux_creance: Optional[float]


class CreanceByCustLevelResponse(BaseModel):
    """Response schema for customer level (CUST_LEV2) aggregations"""
    cust_lev2: str
    nombre_lignes: int
    total_creance_brut: float
    total_creance_net: float
    total_invoice_amt: float
    taux_creance: Optional[float]


class CreanceOverviewResponse(BaseModel):
    """Response schema for overview analytics"""
    total_creance_brut: float
    total_creance_net: float
    total_open_amt: float
    total_invoice_amt: float
    nombre_lignes_total: int
    nombre_dots: int
    taux_creance_moyen: float
    by_dot: Dict[str, float]
    by_year: Dict[str, float]


class CreanceFiltersResponse(BaseModel):
    """Response schema for available filter values"""
    dots: List[str]
    years: List[str]
    products: List[str]
    cust_levels: List[str]


class CreancePivotResponse(BaseModel):
    """Response schema for pivot table aggregations"""
    dimensions: List[str]
    aggregations: List[str]
    data: Dict[str, Any]
    summary: Dict[str, float]


# ============================================================================
# Overview Endpoint
# ============================================================================

@creance_analytics_router.get("/overview", response_model=CreanceOverviewResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get overview analytics for créance data

    Returns key debt metrics including total créance amounts, aging analysis,
    and distributions by DOT and year.

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(CreancePeriodiqueDot)

        # Get totals
        total_creance_brut = query.with_entities(
            func.sum(CreancePeriodiqueDot.creance_brut)
        ).scalar() or 0.0

        total_creance_net = query.with_entities(
            func.sum(CreancePeriodiqueDot.creance_net)
        ).scalar() or 0.0

        total_open_amt = query.with_entities(
            func.sum(CreancePeriodiqueDot.open_amt)
        ).scalar() or 0.0

        total_invoice_amt = query.with_entities(
            func.sum(CreancePeriodiqueDot.invoice_amt)
        ).scalar() or 0.0

        # Number of records
        nombre_lignes = query.count()

        # Number of unique DOTs
        nombre_dots = query.with_entities(
            func.count(func.distinct(CreancePeriodiqueDot.dot))
        ).scalar() or 0

        # Average créance rate
        taux_moyen = (total_creance_net / total_invoice_amt * 100) if total_invoice_amt > 0 else 0.0

        # By DOT
        dot_data = db.query(
            CreancePeriodiqueDot.dot,
            func.sum(CreancePeriodiqueDot.creance_net).label('total')
        ).filter(CreancePeriodiqueDot.dot.isnot(None)).group_by(
            CreancePeriodiqueDot.dot
        ).order_by(func.sum(CreancePeriodiqueDot.creance_net).desc()).all()

        by_dot = {row.dot: float(row.total or 0) for row in dot_data}

        # By year
        year_data = db.query(
            CreancePeriodiqueDot.annee,
            func.sum(CreancePeriodiqueDot.creance_net).label('total')
        ).filter(CreancePeriodiqueDot.annee.isnot(None)).group_by(
            CreancePeriodiqueDot.annee
        ).order_by(CreancePeriodiqueDot.annee.desc()).all()

        by_year = {row.annee: float(row.total or 0) for row in year_data}

        logger.info(f"Overview retrieved: Total Créance Net={total_creance_net}, Rate={taux_moyen:.2f}%")

        return {
            "total_creance_brut": float(total_creance_brut),
            "total_creance_net": float(total_creance_net),
            "total_open_amt": float(total_open_amt),
            "total_invoice_amt": float(total_invoice_amt),
            "nombre_lignes_total": nombre_lignes,
            "nombre_dots": nombre_dots,
            "taux_creance_moyen": float(taux_moyen),
            "by_dot": by_dot,
            "by_year": by_year
        }

    except Exception as e:
        logger.error(f"Error getting créance overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve overview: {str(e)}")


# ============================================================================
# By DOT Endpoint
# ============================================================================

@creance_analytics_router.get("/by-dot", response_model=List[CreanceByDotResponse])
async def get_by_dot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    sort_by: str = Query("creance_net", regex="^(dot|lignes|creance_brut|creance_net|open_amt|taux)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    limit: Optional[int] = Query(None, ge=1, le=100)
):
    """
    Get créance data grouped by DOT (Digital Operations Telecommunication)

    Returns DOT-level aggregations with créance amounts and rates.

    Parameters:
    - sort_by: Sort field (dot, lignes, creance_brut, creance_net, open_amt, taux)
    - order: Sort order (asc, desc)
    - limit: Maximum number of results

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        results = db.query(
            CreancePeriodiqueDot.dot,
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt'),
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt')
        ).filter(
            CreancePeriodiqueDot.dot.isnot(None)
        ).group_by(
            CreancePeriodiqueDot.dot
        ).all()

        # Build response
        response = []
        for row in results:
            total_invoice = float(row.total_invoice_amt or 1)  # Avoid division by zero
            taux = (float(row.total_creance_net or 0) / total_invoice * 100) if total_invoice > 0 else 0

            response.append(CreanceByDotResponse(
                dot=row.dot or "Unknown",
                nombre_lignes=int(row.nombre_lignes),
                total_creance_brut=float(row.total_creance_brut or 0),
                total_creance_net=float(row.total_creance_net or 0),
                total_open_amt=float(row.total_open_amt or 0),
                taux_creance=float(taux)
            ))

        # Apply sorting
        sort_map = {
            "dot": lambda x: x.dot,
            "lignes": lambda x: x.nombre_lignes,
            "creance_brut": lambda x: x.total_creance_brut,
            "creance_net": lambda x: x.total_creance_net,
            "open_amt": lambda x: x.total_open_amt,
            "taux": lambda x: x.taux_creance or 0
        }

        if sort_by in sort_map:
            response.sort(key=sort_map[sort_by], reverse=(order == "desc"))

        # Apply limit
        if limit:
            response = response[:limit]

        logger.info(f"By DOT retrieved: {len(response)} DOTs")

        return response

    except Exception as e:
        logger.error(f"Error getting créance by DOT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by DOT: {str(e)}")


# ============================================================================
# By Year Endpoint
# ============================================================================

@creance_analytics_router.get("/by-year", response_model=List[CreanceByYearResponse])
async def get_by_year(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    dot: Optional[List[str]] = Query(None)
):
    """
    Get créance data grouped by year

    Returns year-level aggregations of debt amounts and record counts.

    Parameters:
    - dot: Optional list of DOTs to filter

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(CreancePeriodiqueDot)

        # Apply filters
        if dot:
            query = query.filter(CreancePeriodiqueDot.dot.in_(dot))

        # Group by year
        results = query.with_entities(
            CreancePeriodiqueDot.annee,
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.open_amt).label('total_open_amt')
        ).filter(
            CreancePeriodiqueDot.annee.isnot(None)
        ).group_by(
            CreancePeriodiqueDot.annee
        ).order_by(
            CreancePeriodiqueDot.annee.desc()
        ).all()

        # Build response
        response = []
        for row in results:
            response.append(CreanceByYearResponse(
                annee=row.annee or "Unknown",
                nombre_lignes=int(row.nombre_lignes),
                total_creance_brut=float(row.total_creance_brut or 0),
                total_creance_net=float(row.total_creance_net or 0),
                total_open_amt=float(row.total_open_amt or 0)
            ))

        logger.info(f"By year retrieved: {len(response)} years")

        return response

    except Exception as e:
        logger.error(f"Error getting créance by year: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by year: {str(e)}")


# ============================================================================
# By Product Endpoint
# ============================================================================

@creance_analytics_router.get("/by-product", response_model=List[CreanceByProductResponse])
async def get_by_product(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    dot: Optional[List[str]] = Query(None),
    year: Optional[str] = None
):
    """
    Get créance data grouped by product type

    Returns product-level aggregations with créance amounts and rates.

    Parameters:
    - dot: Optional list of DOTs to filter
    - year: Optional year to filter

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(CreancePeriodiqueDot)

        # Apply filters
        if dot:
            query = query.filter(CreancePeriodiqueDot.dot.in_(dot))
        if year:
            query = query.filter(CreancePeriodiqueDot.annee == year)

        # Group by product
        results = query.with_entities(
            CreancePeriodiqueDot.produit,
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt')
        ).filter(
            CreancePeriodiqueDot.produit.isnot(None)
        ).group_by(
            CreancePeriodiqueDot.produit
        ).order_by(
            func.sum(CreancePeriodiqueDot.creance_net).desc()
        ).all()

        # Build response
        response = []
        for row in results:
            total_invoice = float(row.total_invoice_amt or 1)
            taux = (float(row.total_creance_net or 0) / total_invoice * 100) if total_invoice > 0 else 0

            response.append(CreanceByProductResponse(
                produit=row.produit or "Unknown",
                nombre_lignes=int(row.nombre_lignes),
                total_creance_brut=float(row.total_creance_brut or 0),
                total_creance_net=float(row.total_creance_net or 0),
                taux_creance=float(taux)
            ))

        logger.info(f"By product retrieved: {len(response)} products")

        return response

    except Exception as e:
        logger.error(f"Error getting créance by product: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by product: {str(e)}")


@creance_analytics_router.get("/by-cust-level", response_model=List[CreanceByCustLevelResponse])
async def get_by_cust_level(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    dot: Optional[List[str]] = Query(None),
    year: Optional[str] = None
):
    """
    Get créance data grouped by customer level (CUST_LEV2)

    Returns customer-level aggregations with créance amounts and rates.

    Parameters:
    - dot: Optional list of DOTs to filter
    - year: Optional year to filter

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build query
        query = db.query(CreancePeriodiqueDot)

        # Apply filters
        if dot:
            query = query.filter(CreancePeriodiqueDot.dot.in_(dot))
        if year:
            query = query.filter(CreancePeriodiqueDot.annee == year)

        # Group by customer level 2
        results = query.with_entities(
            CreancePeriodiqueDot.cust_lev2,
            func.count(CreancePeriodiqueDot.id).label('nombre_lignes'),
            func.sum(CreancePeriodiqueDot.creance_brut).label('total_creance_brut'),
            func.sum(CreancePeriodiqueDot.creance_net).label('total_creance_net'),
            func.sum(CreancePeriodiqueDot.invoice_amt).label('total_invoice_amt')
        ).filter(
            CreancePeriodiqueDot.cust_lev2.isnot(None)
        ).group_by(
            CreancePeriodiqueDot.cust_lev2
        ).order_by(
            func.sum(CreancePeriodiqueDot.creance_net).desc()
        ).all()

        # Build response
        response = []
        for row in results:
            total_invoice = float(row.total_invoice_amt or 1)
            taux = (float(row.total_creance_net or 0) / total_invoice * 100) if total_invoice > 0 else 0

            response.append(CreanceByCustLevelResponse(
                cust_lev2=row.cust_lev2 or "Unknown",
                nombre_lignes=int(row.nombre_lignes),
                total_creance_brut=float(row.total_creance_brut or 0),
                total_creance_net=float(row.total_creance_net or 0),
                total_invoice_amt=float(row.total_invoice_amt or 0),
                taux_creance=float(taux)
            ))

        logger.info(f"By customer level retrieved: {len(response)} customer levels")

        return response

    except Exception as e:
        logger.error(f"Error getting créance by customer level: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve by customer level: {str(e)}")


# ============================================================================
# Filters Endpoint
# ============================================================================

@creance_analytics_router.get("/filters", response_model=CreanceFiltersResponse)
async def get_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available filter values for créance analytics UI

    Returns unique DOTs, years, products, and customer classification levels.

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Get unique DOTs
        dot_results = db.query(
            CreancePeriodiqueDot.dot
        ).distinct().filter(
            CreancePeriodiqueDot.dot.isnot(None)
        ).order_by(CreancePeriodiqueDot.dot).all()

        dots = [row.dot for row in dot_results]

        # Get unique years
        year_results = db.query(
            CreancePeriodiqueDot.annee
        ).distinct().filter(
            CreancePeriodiqueDot.annee.isnot(None)
        ).order_by(CreancePeriodiqueDot.annee.desc()).all()

        years = [row.annee for row in year_results]

        # Get unique products
        product_results = db.query(
            CreancePeriodiqueDot.produit
        ).distinct().filter(
            CreancePeriodiqueDot.produit.isnot(None)
        ).order_by(CreancePeriodiqueDot.produit).all()

        products = [row.produit for row in product_results]

        # Get unique customer levels
        cust_results = db.query(
            CreancePeriodiqueDot.cust_lev2
        ).distinct().filter(
            CreancePeriodiqueDot.cust_lev2.isnot(None)
        ).order_by(CreancePeriodiqueDot.cust_lev2).all()

        cust_levels = [row.cust_lev2 for row in cust_results]

        logger.info(f"Filters retrieved: {len(dots)} DOTs, {len(years)} years, {len(products)} products")

        return {
            "dots": dots,
            "years": years,
            "products": products,
            "cust_levels": cust_levels
        }

    except Exception as e:
        logger.error(f"Error getting créance filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filters: {str(e)}")


# ============================================================================
# Pivot Table Endpoint
# ============================================================================

@creance_analytics_router.get("/pivot", response_model=CreancePivotResponse)
async def get_pivot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    group_by: str = Query("dot", regex="^(dot|year|product|dot_year)$"),
    metric: str = Query("creance_net", regex="^(creance_net|creance_brut|open_amt|count)$"),
    dot: Optional[List[str]] = Query(None),
    year: Optional[str] = None
):
    """
    Get créance data as a pivot table with dynamic grouping

    Supports pivot operations on créance data with flexible grouping dimensions.

    Parameters:
    - group_by: Grouping dimension (dot, year, product, dot_year)
    - metric: Metric to aggregate (creance_net, creance_brut, open_amt, count)
    - dot: Optional list of DOTs to filter
    - year: Optional year to filter

    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(current_user, db, "can_view_analytics")

    try:
        # Build base query
        query = db.query(CreancePeriodiqueDot)

        # Apply filters
        if dot:
            query = query.filter(CreancePeriodiqueDot.dot.in_(dot))
        if year:
            query = query.filter(CreancePeriodiqueDot.annee == year)

        records = query.all()

        # Initialize pivot data structure
        pivot_data = {}
        summary = {}

        # Metric definitions
        metric_config = {
            "creance_net": lambda x: sum(float(r.creance_net or 0) for r in x),
            "creance_brut": lambda x: sum(float(r.creance_brut or 0) for r in x),
            "open_amt": lambda x: sum(float(r.open_amt or 0) for r in x),
            "count": lambda x: len(x)
        }

        metric_func = metric_config[metric]

        # Group by DOT
        if group_by == "dot":
            dimensions = ["dot"]
            grouped = {}
            for record in records:
                key = record.dot or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys()):
                value = metric_func(grouped[key])
                pivot_data[key] = float(value) if not isinstance(value, float) else value

            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values)

        # Group by year
        elif group_by == "year":
            dimensions = ["year"]
            grouped = {}
            for record in records:
                key = record.annee or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys(), reverse=True):
                value = metric_func(grouped[key])
                pivot_data[key] = float(value) if not isinstance(value, float) else value

            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values)

        # Group by product
        elif group_by == "product":
            dimensions = ["product"]
            grouped = {}
            for record in records:
                key = record.produit or "Unknown"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            for key in sorted(grouped.keys()):
                value = metric_func(grouped[key])
                pivot_data[key] = float(value) if not isinstance(value, float) else value

            all_values = [metric_func(v) for v in grouped.values()]
            summary[metric] = sum(all_values)

        # Group by DOT AND year (two-dimensional pivot)
        elif group_by == "dot_year":
            from collections import defaultdict
            dimensions = ["dot", "year"]
            grouped = defaultdict(lambda: defaultdict(list))

            for record in records:
                d = record.dot or "Unknown"
                y = record.annee or "Unknown"
                grouped[d][y].append(record)

            for d in sorted(grouped.keys()):
                pivot_data[d] = {}
                for y in sorted(grouped[d].keys(), reverse=True):
                    value = metric_func(grouped[d][y])
                    pivot_data[d][y] = float(value) if not isinstance(value, float) else value

            all_values = []
            for d_data in pivot_data.values():
                if isinstance(d_data, dict):
                    all_values.extend(d_data.values())

            summary[metric] = sum(all_values)

        logger.info(f"Generated pivot: group_by={group_by}, metric={metric}")

        return {
            "dimensions": dimensions,
            "aggregations": [metric],
            "data": pivot_data,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error generating créance pivot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate pivot: {str(e)}")
