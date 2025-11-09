"""
Créance Périodique DOT API Endpoints
Handles data retrieval and analytics for Créance Périodique DOT data with RBAC
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.creance import CreancePeriodiqueDot, CreanceAggregateView
from services.creance_service import CreanceService
from services.permission_service import PermissionService
from core.security import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creance", tags=["Créance Périodique DOT"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class CreanceRecordResponse(BaseModel):
    """Response schema for single créance record"""
    id: int
    file_upload_id: Optional[int]
    dot_id: Optional[int]
    dot: Optional[str]
    actel: Optional[str]
    mois: Optional[str]
    annee: Optional[str]
    period_key: Optional[str]
    produit: Optional[str]
    cust_lev1: Optional[str]
    cust_lev2: Optional[str]
    cust_lev3: Optional[str]
    invoice_amt_ht: Optional[float]
    invoice_amt: Optional[float]
    open_amt: Optional[float]
    creance_ht: Optional[float]
    creance_net: Optional[float]
    creance_brut: Optional[float]
    avoir_amt: Optional[float]
    avoir_amt_ht: Optional[float]
    exigible_mt: Optional[float]
    creance_120_mt: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CreanceListResponse(BaseModel):
    """Response schema for paginated list of créance records"""
    items: List[CreanceRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OverviewStatsResponse(BaseModel):
    """Response schema for overview statistics"""
    total_invoice_amt_ht: float
    total_invoice_amt: float
    total_open_amt: float
    total_creance_ht: float
    total_creance_net: float
    total_creance_brut: float
    total_avoir_amt: float
    nombre_lignes: int


class DOTAggregateResponse(BaseModel):
    """Response schema for DOT-level aggregate data"""
    dot: str
    total_invoice_amt_ht: float
    total_invoice_amt: float
    total_creance_net: float
    total_creance_brut: float
    total_open_amt: float
    nombre_lignes: int


class AnneeAggregateResponse(BaseModel):
    """Response schema for year-level aggregate data"""
    annee: str
    total_invoice_amt_ht: float
    total_invoice_amt: float
    total_creance_net: float
    total_creance_brut: float
    total_open_amt: float
    nombre_lignes: int


class ProduitAggregateResponse(BaseModel):
    """Response schema for product-level aggregate data"""
    produit: str
    total_invoice_amt_ht: float
    total_invoice_amt: float
    total_creance_net: float
    total_creance_brut: float
    total_open_amt: float
    nombre_lignes: int


class CustLev2AggregateResponse(BaseModel):
    """Response schema for customer level 2 aggregate data"""
    cust_lev2: str
    total_invoice_amt_ht: float
    total_invoice_amt: float
    total_creance_net: float
    total_creance_brut: float
    total_open_amt: float
    nombre_lignes: int


class StatisticsByDOTResponse(BaseModel):
    """Response schema for DOT statistics"""
    total_lignes: int
    total_invoice_amt_ht: float
    total_invoice_amt: float
    total_creance_net: float
    total_creance_brut: float
    total_open_amt: float


# ============================================================================
# Main Data Endpoints
# ============================================================================

@router.get("/records", response_model=CreanceListResponse)
async def get_creance_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Records per page"),
    dot: Optional[str] = Query(None, description="Filter by DOT"),
    actel: Optional[str] = Query(None, description="Filter by ACTEL"),
    annee: Optional[str] = Query(None, description="Filter by year"),
    mois: Optional[str] = Query(None, description="Filter by month"),
    period_key: Optional[str] = Query(None, description="Filter by period (YYYY-MM)"),
    produit: Optional[str] = Query(None, description="Filter by product"),
    cust_lev1: Optional[str] = Query(None, description="Filter by customer level 1"),
    cust_lev2: Optional[str] = Query(None, description="Filter by customer level 2"),
    cust_lev3: Optional[str] = Query(None, description="Filter by customer level 3"),
    file_upload_id: Optional[int] = Query(None, description="Filter by file upload"),
    sort_by: str = Query("created_at", description="Sort by column"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get créance records with pagination and filtering
    Requires: can_view_kpi_data permission (or RBAC access via DOT)
    """
    try:
        # Check permission
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        records, total = service.get_creance_records(
            current_user=current_user,
            page=page,
            page_size=page_size,
            dot=dot,
            actel=actel,
            annee=annee,
            mois=mois,
            period_key=period_key,
            produit=produit,
            cust_lev1=cust_lev1,
            cust_lev2=cust_lev2,
            cust_lev3=cust_lev3,
            file_upload_id=file_upload_id,
            sort_by=sort_by,
            sort_order=sort_order
        )

        total_pages = (total + page_size - 1) // page_size

        return CreanceListResponse(
            items=[CreanceRecordResponse.from_orm(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting créance records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records/{record_id}", response_model=CreanceRecordResponse)
async def get_creance_by_id(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single créance record by ID
    Requires: can_view_kpi_data permission and RBAC access
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        record = service.get_creance_by_id(record_id, current_user)

        if not record:
            raise HTTPException(status_code=404, detail="Record not found or access denied")

        return CreanceRecordResponse.from_orm(record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting créance record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Dashboard Aggregate Endpoints
# ============================================================================

@router.get("/dashboard/overview", response_model=OverviewStatsResponse)
async def get_overview_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get overview statistics for dashboard KPI cards
    Returns: Total Invoice Amounts, Total Créance, etc.
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        stats = service.get_overview_stats(current_user)

        return OverviewStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/by-dot", response_model=List[DOTAggregateResponse])
async def get_by_dot_aggregates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get DOT-level aggregate data for histogram
    Returns: Créance NET by DOT
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        aggregates = service.get_by_dot_aggregates(current_user)

        return [DOTAggregateResponse(**agg) for agg in aggregates]

    except Exception as e:
        logger.error(f"Error getting DOT aggregates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/by-annee", response_model=List[AnneeAggregateResponse])
async def get_by_annee_aggregates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get year-level aggregate data for histogram
    Returns: Créance NET by Year
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        aggregates = service.get_by_annee_aggregates(current_user)

        return [AnneeAggregateResponse(**agg) for agg in aggregates]

    except Exception as e:
        logger.error(f"Error getting year aggregates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/by-produit", response_model=List[ProduitAggregateResponse])
async def get_by_produit_aggregates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get product-level aggregate data for histogram
    Returns: Créance NET by Product
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        aggregates = service.get_by_produit_aggregates(current_user)

        return [ProduitAggregateResponse(**agg) for agg in aggregates]

    except Exception as e:
        logger.error(f"Error getting product aggregates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/by-cust-lev2", response_model=List[CustLev2AggregateResponse])
async def get_by_cust_lev2_aggregates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get customer level 2 aggregate data for histogram
    Returns: Créance NET by Customer Level 2
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        aggregates = service.get_by_cust_lev2_aggregates(current_user)

        return [CustLev2AggregateResponse(**agg) for agg in aggregates]

    except Exception as e:
        logger.error(f"Error getting customer level 2 aggregates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Statistics and Analytics Endpoints
# ============================================================================

@router.get("/statistics/by-dot", response_model=StatisticsByDOTResponse)
async def get_statistics_by_dot(
    dot: Optional[str] = Query(None, description="Filter by DOT"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics by DOT
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        stats = service.get_statistics_by_dot(current_user, dot)

        return StatisticsByDOTResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting DOT statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-periods", response_model=List[str])
async def get_available_periods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available periods (YYYY-MM) with data
    Useful for period filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        periods = service.get_available_periods(current_user)

        return periods

    except Exception as e:
        logger.error(f"Error getting available periods: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-years", response_model=List[str])
async def get_available_years(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available years with data
    Useful for year filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        years = service.get_available_years(current_user)

        return years

    except Exception as e:
        logger.error(f"Error getting available years: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-dots", response_model=List[str])
async def get_available_dots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available DOTs with data
    Useful for DOT filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        dots = service.get_available_dots(current_user)

        return dots

    except Exception as e:
        logger.error(f"Error getting available DOTs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-products", response_model=List[str])
async def get_available_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available products with data
    Useful for product filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        products = service.get_available_products(current_user)

        return products

    except Exception as e:
        logger.error(f"Error getting available products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-cust-lev2", response_model=List[str])
async def get_available_cust_lev2(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available customer level 2 values with data
    Useful for customer level 2 filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = CreanceService(db)
        cust_lev2 = service.get_available_cust_lev2(current_user)

        return cust_lev2

    except Exception as e:
        logger.error(f"Error getting available customer level 2 values: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Export Endpoint
# ============================================================================

@router.get("/export")
async def export_records(
    dot: Optional[str] = Query(None, description="Filter by DOT"),
    annee: Optional[str] = Query(None, description="Filter by year"),
    period_key: Optional[str] = Query(None, description="Filter by period (YYYY-MM)"),
    produit: Optional[str] = Query(None, description="Filter by product"),
    cust_lev2: Optional[str] = Query(None, description="Filter by customer level 2"),
    format: str = Query("json", description="Export format (json/csv)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export créance records for download
    Supports JSON and CSV formats
    Requires: can_export_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_export_data")

        service = CreanceService(db)
        records = service.get_records_for_export(
            current_user=current_user,
            dot=dot,
            annee=annee,
            period_key=period_key,
            produit=produit,
            cust_lev2=cust_lev2
        )

        if format.lower() == "csv":
            # Convert to CSV format
            from fastapi.responses import StreamingResponse
            import csv
            import io

            output = io.StringIO()
            if records:
                # Get column names from first record
                columns = [
                    'id', 'dot', 'actel', 'annee', 'mois', 'period_key',
                    'produit', 'cust_lev1', 'cust_lev2', 'cust_lev3',
                    'invoice_amt_ht', 'invoice_amt', 'open_amt',
                    'creance_ht', 'creance_net', 'creance_brut',
                    'avoir_amt', 'avoir_amt_ht', 'exigible_mt', 'creance_120_mt'
                ]

                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()

                for record in records:
                    row = {col: getattr(record, col, None) for col in columns}
                    writer.writerow(row)

            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=creance_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        else:
            # Return JSON format
            return {
                "success": True,
                "total_records": len(records),
                "data": [
                    {
                        "id": record.id,
                        "dot": record.dot,
                        "actel": record.actel,
                        "annee": record.annee,
                        "mois": record.mois,
                        "period_key": record.period_key,
                        "produit": record.produit,
                        "cust_lev1": record.cust_lev1,
                        "cust_lev2": record.cust_lev2,
                        "cust_lev3": record.cust_lev3,
                        "invoice_amt_ht": float(record.invoice_amt_ht) if record.invoice_amt_ht else None,
                        "invoice_amt": float(record.invoice_amt) if record.invoice_amt else None,
                        "open_amt": float(record.open_amt) if record.open_amt else None,
                        "creance_ht": float(record.creance_ht) if record.creance_ht else None,
                        "creance_net": float(record.creance_net) if record.creance_net else None,
                        "creance_brut": float(record.creance_brut) if record.creance_brut else None,
                        "avoir_amt": float(record.avoir_amt) if record.avoir_amt else None,
                        "avoir_amt_ht": float(record.avoir_amt_ht) if record.avoir_amt_ht else None,
                        "exigible_mt": float(record.exigible_mt) if record.exigible_mt else None,
                        "creance_120_mt": float(record.creance_120_mt) if record.creance_120_mt else None
                    }
                    for record in records
                ]
            }

    except Exception as e:
        logger.error(f"Error exporting records: {e}")
        raise HTTPException(status_code=500, detail=str(e))
