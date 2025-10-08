"""
Park Analytics API - Real data endpoints for dashboard visualizations
Based on Parc Corporate NGBSS data with DOT-based permissions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.park import Park
from models.dot import DOT
from services.dot_service import DOTService
from services.permission_service import PermissionService
from services.kpi_cache_service import kpi_cache_service

logger = logging.getLogger(__name__)

park_analytics_router = APIRouter()


@park_analytics_router.get("/overview")
async def get_park_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """✅ OPTIMIZED: Get cached overview analytics for Parc Corporate NGBSS"""

    # Use cached service for 10× faster response
    return kpi_cache_service.get_overview_analytics(db, current_user.id)


@park_analytics_router.get("/by-telecom-type")
async def get_by_telecom_type(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get distribution by Telecom Type"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Get telecom type distribution
    telecom_distribution = query.filter(
        Park.telecom_type.isnot(None)
    ).with_entities(
        Park.telecom_type,
        func.count(Park.id).label('count')
    ).group_by(Park.telecom_type).order_by(func.count(Park.id).desc()).all()

    total_count = sum([item.count for item in telecom_distribution])

    distribution = []
    for item in telecom_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "type": item.telecom_type or "UNKNOWN",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-subscriber-status")
async def get_by_subscriber_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """✅ OPTIMIZED: Get cached subscriber status distribution"""

    # Use cached service for 10× faster response
    return kpi_cache_service.get_subscriber_status_distribution(db, current_user.id)


@park_analytics_router.post("/cache/invalidate")
async def invalidate_kpi_cache(
    current_user: User = Depends(get_current_user),
    user_only: bool = Query(
        False, description="Invalidate only current user's cache")
):
    """Invalidate KPI cache for faster data refresh"""

    if user_only:
        kpi_cache_service.invalidate_user_cache(current_user.id)
        return {"message": f"Cache invalidated for user {current_user.id}"}
    else:
        kpi_cache_service.invalidate_all_cache()
        return {"message": "All KPI cache invalidated"}


@park_analytics_router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """Get KPI cache statistics"""
    return kpi_cache_service.get_cache_stats()


@park_analytics_router.get("/by-customer-l2")
async def get_by_customer_l2(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """✅ OPTIMIZED: Get cached customer L2 distribution"""

    # Use cached service for 10× faster response
    return kpi_cache_service.get_customer_l2_distribution(db, current_user.id)


@park_analytics_router.get("/by-customer-l3")
async def get_by_customer_l3(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """✅ OPTIMIZED: Get cached customer L3 distribution"""

    # Use cached service for 10× faster response
    return kpi_cache_service.get_customer_l3_distribution(db, current_user.id)


@park_analytics_router.get("/by-dot")
async def get_by_dot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get distribution by DOT"""

    # Apply DOT-based permission filtering
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if not accessible_dots:
        return {"distribution": [], "total": 0}

    # Get DOT distribution
    dot_distribution = db.query(
        DOT.name,
        DOT.id,
        func.count(Park.id).label('count')
    ).outerjoin(
        Park, DOT.id == Park.dot_id
    ).filter(
        DOT.id.in_(accessible_dots)
    ).group_by(
        DOT.id, DOT.name
    ).order_by(func.count(Park.id).desc()).all()

    total_count = sum([item.count for item in dot_distribution])

    distribution = []
    for item in dot_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "dot_name": item.name,
            "dot_id": item.id,
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/filters")
async def get_available_filters(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available filter values for dropdowns"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {
            "dots": [],
            "actel_codes": [],
            "subscriber_statuses": [],
            "telecom_types": [],
            "offer_names": [],
            "customer_l2_codes": [],
            "customer_l3_codes": []
        }

    # Get DOTs
    dots = db.query(DOT).filter(DOT.id.in_(accessible_dots)).all()

    # Get unique values for filters
    actel_codes = query.filter(Park.actel_code.isnot(None)).with_entities(
        Park.actel_code).distinct().limit(50).all()
    subscriber_statuses = query.filter(Park.subscriber_status.isnot(
        None)).with_entities(Park.subscriber_status).distinct().all()
    telecom_types = query.filter(Park.telecom_type.isnot(
        None)).with_entities(Park.telecom_type).distinct().all()
    offer_names = query.filter(Park.offer_name.isnot(None)).with_entities(
        Park.offer_name).distinct().limit(100).all()
    customer_l2_codes = query.filter(Park.customer_l2_code.isnot(None)).with_entities(
        Park.customer_l2_code, Park.customer_l2_description).distinct().limit(50).all()
    customer_l3_codes = query.filter(Park.customer_l3_code.isnot(None)).with_entities(
        Park.customer_l3_code, Park.customer_l3_description).distinct().limit(50).all()

    return {
        "dots": [{"id": dot.id, "name": dot.name} for dot in dots],
        "actel_codes": [code[0] for code in actel_codes if code[0]],
        "subscriber_statuses": [status[0] for status in subscriber_statuses if status[0]],
        "telecom_types": [type[0] for type in telecom_types if type[0]],
        "offer_names": [name[0] for name in offer_names if name[0]],
        "customer_l2_codes": [{"code": item[0], "description": item[1]} for item in customer_l2_codes if item[0]],
        "customer_l3_codes": [{"code": item[0], "description": item[1]} for item in customer_l3_codes if item[0]]
    }


@park_analytics_router.get("/export")
async def export_data(
    format: str = Query("csv", regex="^(csv|excel)$"),
    # Single value filters (for backward compatibility)
    dot_filter: Optional[str] = Query(None),
    actel_code_filter: Optional[str] = Query(None),
    subscriber_status_filter: Optional[str] = Query(None),
    telecom_type_filter: Optional[str] = Query(None),
    # Multiple value filters (comma-separated)
    dot_ids: Optional[str] = Query(
        None, description="Comma-separated DOT IDs"),
    actel_codes: Optional[str] = Query(
        None, description="Comma-separated Actel codes"),
    subscriber_statuses: Optional[str] = Query(
        None, description="Comma-separated subscriber statuses"),
    telecom_types: Optional[str] = Query(
        None, description="Comma-separated telecom types"),
    offer_names: Optional[str] = Query(
        None, description="Comma-separated offer names"),
    offer_types: Optional[str] = Query(
        None, description="Comma-separated offer types"),
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated Customer L3 codes"),
    # Search filter
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    # Date range filters
    date_from: Optional[str] = Query(
        None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export park data with comprehensive filtering support"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        raise HTTPException(status_code=403, detail="No accessible data")

    # Apply single value filters (backward compatibility)
    if dot_filter:
        query = query.filter(Park.dot_id == int(dot_filter))
    if actel_code_filter:
        query = query.filter(Park.actel_code.ilike(f"%{actel_code_filter}%"))
    if subscriber_status_filter:
        query = query.filter(Park.subscriber_status ==
                             subscriber_status_filter)
    if telecom_type_filter:
        query = query.filter(Park.telecom_type == telecom_type_filter)

    # Apply multiple value filters (comma-separated)
    if dot_ids:
        dot_id_list = [int(id.strip())
                       for id in dot_ids.split(',') if id.strip()]
        query = query.filter(Park.dot_id.in_(dot_id_list))

    if actel_codes:
        actel_list = [code.strip()
                      for code in actel_codes.split(',') if code.strip()]
        query = query.filter(Park.actel_code.in_(actel_list))

    if subscriber_statuses:
        status_list = [status.strip()
                       for status in subscriber_statuses.split(',') if status.strip()]
        query = query.filter(Park.subscriber_status.in_(status_list))

    if telecom_types:
        telecom_list = [ttype.strip()
                        for ttype in telecom_types.split(',') if ttype.strip()]
        query = query.filter(Park.telecom_type.in_(telecom_list))

    if offer_names:
        offer_list = [offer.strip()
                      for offer in offer_names.split(',') if offer.strip()]
        query = query.filter(Park.offer_name.in_(offer_list))

    if offer_types:
        offer_type_list = [otype.strip()
                           for otype in offer_types.split(',') if otype.strip()]
        query = query.filter(Park.offer_type.in_(offer_type_list))

    if customer_l2_codes:
        l2_list = [code.strip()
                   for code in customer_l2_codes.split(',') if code.strip()]
        query = query.filter(Park.customer_l2_code.in_(l2_list))

    if customer_l3_codes:
        l3_list = [code.strip()
                   for code in customer_l3_codes.split(',') if code.strip()]
        query = query.filter(Park.customer_l3_code.in_(l3_list))

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Park.customer_code.ilike(search_term),
                Park.service_number.ilike(search_term),
                Park.customer_full_name.ilike(search_term),
                Park.username.ilike(search_term)
            )
        )

    # Apply date range filters
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Park.created_at >= from_date)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Park.created_at <= to_date)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

    # Get total count first for better error handling
    total_count = query.count()

    if total_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No data found with applied filters. Please adjust your filter criteria."
        )

    # Get data (limit to prevent memory issues)
    parks = query.limit(10000).all()

    if total_count > 10000:
        logger.warning(
            f"Export limited to 10,000 records out of {total_count} total records")

    # Convert to dict for export with better error handling
    export_data = []
    for park in parks:
        try:
            export_data.append({
                "Customer Code": park.customer_code or "",
                "Service Number": park.service_number or "",
                "Customer Name": park.customer_full_name or "",
                "Username": park.username or "",
                "Subscriber Status": park.subscriber_status or "",
                "Telecom Type": park.telecom_type or "",
                "Offer Name": park.offer_name or "",
                "Offer Type": park.offer_type or "",
                "Rental Fees": float(park.rental_fees) if park.rental_fees else 0.0,
                "Customer L1 Code": park.customer_l1_code or "",
                "Customer L1 Description": park.customer_l1_description or "",
                "Customer L2 Code": park.customer_l2_code or "",
                "Customer L2 Description": park.customer_l2_description or "",
                "Customer L3 Code": park.customer_l3_code or "",
                "Customer L3 Description": park.customer_l3_description or "",
                "State": park.state or "",
                "Area": park.area or "",
                "City": park.city or "",
                "Town": park.town or "",
                "Street": park.street or "",
                "Contact Number": park.contact_number or "",
                "ICCID": park.iccid or "",
                "IMSI": park.imsi or "",
                "Status Date": park.status_date.isoformat() if park.status_date else "",
                "Creation Date": park.creation_date.isoformat() if park.creation_date else "",
                "Active Date": park.active_date.isoformat() if park.active_date else "",
                "Expiry Date": park.expiry_date.isoformat() if park.expiry_date else "",
                "Created At": park.created_at.isoformat() if park.created_at else ""
            })
        except Exception as e:
            logger.error(f"Error processing park record {park.id}: {e}")
            # Continue processing other records
            continue

    return {
        "data": export_data,
        "total_records": len(export_data),
        "total_available": total_count,
        "export_limited": total_count > 10000,
        "filters_applied": {
            # Single value filters (backward compatibility)
            "dot_filter": dot_filter,
            "actel_code_filter": actel_code_filter,
            "subscriber_status_filter": subscriber_status_filter,
            "telecom_type_filter": telecom_type_filter,
            # Multiple value filters
            "dot_ids": dot_ids,
            "actel_codes": actel_codes,
            "subscriber_statuses": subscriber_statuses,
            "telecom_types": telecom_types,
            "offer_names": offer_names,
            "offer_types": offer_types,
            "customer_l2_codes": customer_l2_codes,
            "customer_l3_codes": customer_l3_codes,
            # Search and date filters
            "search": search,
            "date_from": date_from,
            "date_to": date_to
        },
        "export_format": format,
        "generated_at": datetime.utcnow().isoformat()
    }
