"""
Encaissement AR DOT API Endpoints
Handles data retrieval and analytics for Encaissement AR DOT data with RBAC
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.encaissement import EncaissementARDot, EncaissementAnomaly, EncaissementAggregateView
from services.encaissement_service import EncaissementService
from services.permission_service import PermissionService
from core.security import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/encaissement", tags=["Encaissement AR DOT"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class EncaissementRecordResponse(BaseModel):
    """Response schema for single encaissement record"""
    id: int
    file_upload_id: Optional[int]
    dot_id: Optional[int]
    organisation: Optional[str]
    source: Optional[str]
    n_fact: Optional[int]
    typ_fact: Optional[str]
    date_fact: Optional[date]
    mois: Optional[str]
    client: Optional[str]
    n_client: Optional[str]
    obj_fact: Optional[str]
    periode: Optional[str]
    ref: Optional[str]
    termine_flag: Optional[str]
    creer_par: Optional[str]
    montant_ht: Optional[float]
    montant_taxe: Optional[float]
    montant_ttc: Optional[float]
    chiffre_aff_exe: Optional[float]
    encaissement: Optional[float]
    n_rglt: Optional[str]
    date_rglt: Optional[date]
    facture_avoir_annulation: Optional[str]
    taux_encaissement: Optional[float]
    montant_restant: Optional[float]
    composite_key: Optional[str]
    is_duplicate: bool
    is_anomaly: bool
    anomaly_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EncaissementListResponse(BaseModel):
    """Response schema for paginated list of encaissement records"""
    items: List[EncaissementRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EncaissementAnomalyResponse(BaseModel):
    """Response schema for anomaly record"""
    id: int
    file_upload_id: Optional[int]
    dot_id: Optional[int]
    organisation: Optional[str]
    n_fact: Optional[int]
    typ_fact: Optional[str]
    montant_ttc: Optional[float]
    encaissement: Optional[float]
    anomaly_type: Optional[str]
    anomaly_reason: Optional[str]
    original_data: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyListResponse(BaseModel):
    """Response schema for paginated list of anomalies"""
    items: List[EncaissementAnomalyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OverviewStatsResponse(BaseModel):
    """Response schema for overview statistics"""
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_encaissement: float
    nombre_factures: int


class MonthlyAggregateResponse(BaseModel):
    """Response schema for monthly aggregate data"""
    mois: str
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_encaissement: float
    nombre_factures: int


class MonthlyDistributionResponse(BaseModel):
    """Response schema for monthly distribution (pie chart)"""
    mois: str
    total_encaissement: float
    percentage: float


class DOTAggregateResponse(BaseModel):
    """Response schema for DOT-level aggregate data"""
    organisation: str
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    taux_encaissement: float
    nombre_factures: int


class StatisticsByOrganisationResponse(BaseModel):
    """Response schema for organisation statistics"""
    total_factures: int
    total_montant_ttc: float
    total_encaissement: float
    total_montant_restant: float
    average_taux_encaissement: float


class AnomalyStatisticsResponse(BaseModel):
    """Response schema for anomaly statistics"""
    total_anomalies: int
    by_type: Dict[str, int]


# ============================================================================
# Main Data Endpoints
# ============================================================================

@router.get("/records", response_model=EncaissementListResponse)
async def get_encaissement_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Records per page"),
    organisation: Optional[str] = Query(None, description="Filter by organisation"),
    mois: Optional[str] = Query(None, description="Filter by month (YYYY-MM)"),
    n_fact: Optional[int] = Query(None, description="Filter by invoice number"),
    typ_fact: Optional[str] = Query(None, description="Filter by invoice type"),
    date_fact_from: Optional[date] = Query(None, description="Filter by date from"),
    date_fact_to: Optional[date] = Query(None, description="Filter by date to"),
    is_duplicate: Optional[bool] = Query(None, description="Filter duplicates"),
    is_anomaly: Optional[bool] = Query(None, description="Filter anomalies"),
    file_upload_id: Optional[int] = Query(None, description="Filter by file upload"),
    sort_by: str = Query("created_at", description="Sort by column"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get encaissement records with pagination and filtering
    Requires: can_view_encaissement permission (or RBAC access via DOT)
    """
    try:
        # Check permission
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        records, total = service.get_encaissement_records(
            current_user=current_user,
            page=page,
            page_size=page_size,
            organisation=organisation,
            mois=mois,
            n_fact=n_fact,
            typ_fact=typ_fact,
            date_fact_from=date_fact_from,
            date_fact_to=date_fact_to,
            is_duplicate=is_duplicate,
            is_anomaly=is_anomaly,
            file_upload_id=file_upload_id,
            sort_by=sort_by,
            sort_order=sort_order
        )

        total_pages = (total + page_size - 1) // page_size

        return EncaissementListResponse(
            items=[EncaissementRecordResponse.from_orm(record) for record in records],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting encaissement records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records/{record_id}", response_model=EncaissementRecordResponse)
async def get_encaissement_by_id(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single encaissement record by ID
    Requires: can_view_kpi_data permission and RBAC access
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        record = service.get_encaissement_by_id(record_id, current_user)

        if not record:
            raise HTTPException(status_code=404, detail="Record not found or access denied")

        return EncaissementRecordResponse.from_orm(record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting encaissement record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Anomaly Endpoints
# ============================================================================

@router.get("/anomalies", response_model=AnomalyListResponse)
async def get_anomalies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Records per page"),
    organisation: Optional[str] = Query(None, description="Filter by organisation"),
    anomaly_type: Optional[str] = Query(None, description="Filter by anomaly type"),
    file_upload_id: Optional[int] = Query(None, description="Filter by file upload"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get encaissement anomalies with pagination and filtering
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        anomalies, total = service.get_anomalies(
            current_user=current_user,
            page=page,
            page_size=page_size,
            organisation=organisation,
            anomaly_type=anomaly_type,
            file_upload_id=file_upload_id
        )

        total_pages = (total + page_size - 1) // page_size

        return AnomalyListResponse(
            items=[EncaissementAnomalyResponse.from_orm(anomaly) for anomaly in anomalies],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error getting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies/statistics", response_model=AnomalyStatisticsResponse)
async def get_anomaly_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get anomaly statistics
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        stats = service.get_anomaly_statistics(current_user)

        return AnomalyStatisticsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting anomaly statistics: {e}")
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
    Returns: Total Montant TTC, Total Encaissement, Taux Encaissement, etc.
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        stats = service.get_overview_stats(current_user)

        return OverviewStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/monthly-aggregates", response_model=List[MonthlyAggregateResponse])
async def get_monthly_aggregates(
    year: Optional[int] = Query(None, description="Filter by year"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly aggregate data for combined bar chart
    Returns: Montant TTC and Encaissement by month
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        aggregates = service.get_monthly_aggregates(current_user, year)

        return [MonthlyAggregateResponse(**agg) for agg in aggregates]

    except Exception as e:
        logger.error(f"Error getting monthly aggregates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/monthly-distribution", response_model=List[MonthlyDistributionResponse])
async def get_monthly_distribution(
    year: Optional[int] = Query(None, description="Filter by year"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly distribution data for 3D pie chart
    Returns: Encaissement amount and percentage by month
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        distribution = service.get_monthly_distribution(current_user, year)

        return [MonthlyDistributionResponse(**dist) for dist in distribution]

    except Exception as e:
        logger.error(f"Error getting monthly distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/dot-aggregates", response_model=List[DOTAggregateResponse])
async def get_dot_aggregates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get DOT-level aggregate data for DOT and Taux bar chart
    Returns: Taux d'encaissement by DOT/Organisation
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        aggregates = service.get_dot_aggregates(current_user)

        return [DOTAggregateResponse(**agg) for agg in aggregates]

    except Exception as e:
        logger.error(f"Error getting DOT aggregates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Statistics and Analytics Endpoints
# ============================================================================

@router.get("/statistics/by-organisation", response_model=StatisticsByOrganisationResponse)
async def get_statistics_by_organisation(
    organisation: Optional[str] = Query(None, description="Filter by organisation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics by organisation
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        stats = service.get_statistics_by_organisation(current_user, organisation)

        return StatisticsByOrganisationResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting organisation statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-months", response_model=List[str])
async def get_available_months(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available months with data
    Useful for month filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        months = service.get_available_months(current_user)

        return months

    except Exception as e:
        logger.error(f"Error getting available months: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/available-organisations", response_model=List[str])
async def get_available_organisations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available organisations (DOTs) with data
    Useful for organisation filter dropdowns
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        organisations = service.get_available_organisations(current_user)

        return organisations

    except Exception as e:
        logger.error(f"Error getting available organisations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Export Endpoint
# ============================================================================

@router.get("/export")
async def export_records(
    organisation: Optional[str] = Query(None, description="Filter by organisation"),
    mois: Optional[str] = Query(None, description="Filter by month (YYYY-MM)"),
    date_fact_from: Optional[date] = Query(None, description="Filter by date from"),
    date_fact_to: Optional[date] = Query(None, description="Filter by date to"),
    include_duplicates: bool = Query(True, description="Include duplicate records"),
    include_anomalies: bool = Query(True, description="Include anomaly records"),
    format: str = Query("json", description="Export format (json/csv)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export encaissement records for download
    Supports JSON and CSV formats
    Requires: can_export_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_export_data")

        service = EncaissementService(db)
        records = service.get_records_for_export(
            current_user=current_user,
            organisation=organisation,
            mois=mois,
            date_fact_from=date_fact_from,
            date_fact_to=date_fact_to,
            include_duplicates=include_duplicates,
            include_anomalies=include_anomalies
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
                    'id', 'organisation', 'source', 'n_fact', 'typ_fact', 'date_fact',
                    'mois', 'client', 'n_client', 'montant_ht', 'montant_taxe',
                    'montant_ttc', 'encaissement', 'n_rglt', 'date_rglt',
                    'taux_encaissement', 'montant_restant', 'is_duplicate', 'is_anomaly'
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
                headers={"Content-Disposition": f"attachment; filename=encaissement_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        else:
            # Return JSON format
            return {
                "success": True,
                "total_records": len(records),
                "data": [
                    {
                        "id": record.id,
                        "organisation": record.organisation,
                        "source": record.source,
                        "n_fact": record.n_fact,
                        "typ_fact": record.typ_fact,
                        "date_fact": str(record.date_fact) if record.date_fact else None,
                        "mois": record.mois,
                        "client": record.client,
                        "n_client": record.n_client,
                        "montant_ht": float(record.montant_ht) if record.montant_ht else None,
                        "montant_taxe": float(record.montant_taxe) if record.montant_taxe else None,
                        "montant_ttc": float(record.montant_ttc) if record.montant_ttc else None,
                        "encaissement": float(record.encaissement) if record.encaissement else None,
                        "n_rglt": record.n_rglt,
                        "date_rglt": str(record.date_rglt) if record.date_rglt else None,
                        "taux_encaissement": float(record.taux_encaissement) if record.taux_encaissement else None,
                        "montant_restant": float(record.montant_restant) if record.montant_restant else None,
                        "is_duplicate": record.is_duplicate,
                        "is_anomaly": record.is_anomaly
                    }
                    for record in records
                ]
            }

    except Exception as e:
        logger.error(f"Error exporting records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Duplicate Management Endpoint
# ============================================================================

@router.get("/duplicates/groups")
async def get_duplicate_groups(
    composite_key: Optional[str] = Query(None, description="Filter by composite key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get groups of duplicate records
    Returns records grouped by composite_key
    Requires: can_view_kpi_data permission
    """
    try:
        PermissionService.require_permission(current_user, db, "can_view_kpi_data")

        service = EncaissementService(db)
        groups = service.get_duplicate_groups(current_user, composite_key)

        return {
            "success": True,
            "total_groups": len(groups),
            "groups": [
                {
                    "composite_key": group["composite_key"],
                    "count": group["count"],
                    "records": [
                        EncaissementRecordResponse.from_orm(record).dict()
                        for record in group["records"]
                    ]
                }
                for group in groups
            ]
        }

    except Exception as e:
        logger.error(f"Error getting duplicate groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))
