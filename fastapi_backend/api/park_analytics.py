"""
Park Analytics API - Real data endpoints for dashboard visualizations
Based on Parc Corporate NGBSS data with DOT-based permissions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import pandas as pd
import io

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


def apply_filters_to_query(
    query,
    dot_ids: Optional[str] = None,
    actel_codes: Optional[str] = None,
    subscriber_statuses: Optional[str] = None,
    telecom_types: Optional[str] = None,
    offer_names: Optional[str] = None,
    offer_types: Optional[str] = None,
    customer_l2_codes: Optional[str] = None,
    customer_l3_codes: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Helper function to apply filters to a query"""
    
    # Log all filter parameters
    filters_dict = {
        "dot_ids": dot_ids,
        "actel_codes": actel_codes,
        "subscriber_statuses": subscriber_statuses,
        "telecom_types": telecom_types,
        "offer_names": offer_names,
        "offer_types": offer_types,
        "customer_l2_codes": customer_l2_codes,
        "customer_l3_codes": customer_l3_codes,
        "search": search,
        "date_from": date_from,
        "date_to": date_to
    }
    # Only log non-empty filters
    active_filters = {k: v for k, v in filters_dict.items() if v}
    if active_filters:
        logger.info(f"🔍 Applying filters: {active_filters}")

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
            pass  # Ignore invalid date format

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Park.created_at <= to_date)
        except ValueError:
            pass  # Ignore invalid date format

    return query


@park_analytics_router.get("/overview")
async def get_park_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get overview analytics for Parc Corporate NGBSS with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /overview - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_overview_analytics(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {
            "total_active_subscribers": 0,
            "total_dots": 0,
            "recent_activity": 0,
            "last_updated": None,
            "total_subscribers": 0,
            "inactive_subscribers": 0,
            "suspended_subscribers": 0,
            "total_revenue": 0.0,
            "filters_applied": True
        }

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    )

    # Calculate metrics
    total_subscribers = query.count()

    # Check multiple possible active status values (like the cache service does)
    active_subscribers = query.filter(
        Park.subscriber_status.in_(
            ["Active", "ACTIVE", "active", "ACTIF", "actif"])
    ).count()

    inactive_subscribers = query.filter(
        Park.subscriber_status.in_(
            ["Inactive", "INACTIVE", "inactive", "INACTIF", "inactif"])
    ).count()

    suspended_subscribers = query.filter(
        Park.subscriber_status.in_(
            ["Suspended", "SUSPENDED", "suspended", "SUSPENDU", "suspendu"])
    ).count()

    # Calculate revenue
    revenue_result = query.with_entities(func.sum(Park.rental_fees)).scalar()
    total_revenue = float(revenue_result) if revenue_result else 0.0

    # Get last update
    last_record = query.order_by(Park.created_at.desc()).first()
    last_update = last_record.created_at.isoformat() if last_record else None

    # Get accessible DOTs count
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    total_dots = len(accessible_dots) if accessible_dots else 0

    # Get recent activity (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = query.filter(Park.created_at >= seven_days_ago).count()

    return {
        "total_active_subscribers": active_subscribers,  # ✅ Match frontend expectation
        "total_dots": total_dots,                        # ✅ Match frontend expectation
        "recent_activity": recent_activity,              # ✅ Match frontend expectation
        "last_updated": last_update,                     # ✅ Match frontend expectation
        "total_subscribers": total_subscribers,
        "inactive_subscribers": inactive_subscribers,
        "suspended_subscribers": suspended_subscribers,
        "total_revenue": round(total_revenue, 2),
        "filters_applied": True
    }


@park_analytics_router.get("/by-telecom-type")
async def get_by_telecom_type(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get distribution by Telecom Type with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-telecom-type - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    )

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
    db: Session = Depends(get_db),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get subscriber status distribution with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-subscriber-status - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_subscriber_status_distribution(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    )

    # Get subscriber status distribution
    status_distribution = query.filter(
        Park.subscriber_status.isnot(None)
    ).with_entities(
        Park.subscriber_status,
        func.count(Park.id).label('count')
    ).group_by(Park.subscriber_status).order_by(func.count(Park.id).desc()).all()

    total_count = sum([item.count for item in status_distribution])

    distribution = []
    for item in status_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "status": item.subscriber_status or "UNKNOWN",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


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
    db: Session = Depends(get_db),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get customer L2 distribution with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-customer-l2 - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_customer_l2_distribution(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    )

    # Get customer L2 distribution
    l2_distribution = query.filter(
        Park.customer_l2_code.isnot(None)
    ).with_entities(
        Park.customer_l2_code,
        Park.customer_l2_description,
        func.count(Park.id).label('count')
    ).group_by(Park.customer_l2_code, Park.customer_l2_description).order_by(func.count(Park.id).desc()).limit(50).all()

    total_count = sum([item.count for item in l2_distribution])

    distribution = []
    for item in l2_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            # ✅ Match cached service format
            "code": item.customer_l2_code or "UNKNOWN",
            # ✅ Match cached service format
            "description": item.customer_l2_description or "N/A",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-customer-l3")
async def get_by_customer_l3(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get customer L3 distribution with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-customer-l3 - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Check if any filters are applied
    has_filters = any([
        dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    ])

    # If no filters, use cached service for 10× faster response
    if not has_filters:
        return kpi_cache_service.get_customer_l3_distribution(db, current_user.id)

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Apply filters
    query = apply_filters_to_query(
        query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    )

    # Get customer L3 distribution
    l3_distribution = query.filter(
        Park.customer_l3_code.isnot(None)
    ).with_entities(
        Park.customer_l3_code,
        Park.customer_l3_description,
        func.count(Park.id).label('count')
    ).group_by(Park.customer_l3_code, Park.customer_l3_description).order_by(func.count(Park.id).desc()).limit(100).all()

    total_count = sum([item.count for item in l3_distribution])

    distribution = []
    for item in l3_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            # ✅ Match cached service format
            "code": item.customer_l3_code or "UNKNOWN",
            # ✅ Match cached service format
            "description": item.customer_l3_description or "N/A",
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-dot")
async def get_by_dot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """Get distribution by DOT with filtering support"""
    
    # Log received filter parameters
    logger.info(
        f"📊 GET /by-dot - User {current_user.id} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Apply DOT-based permission filtering
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if not accessible_dots:
        return {"distribution": [], "total": 0}

    # Build base query for filtering
    park_query = db.query(Park).filter(Park.dot_id.in_(accessible_dots))

    # Apply filters to park query
    park_query = apply_filters_to_query(
        park_query, dot_ids, actel_codes, subscriber_statuses, telecom_types,
        offer_names, offer_types, customer_l2_codes, customer_l3_codes,
        search, date_from, date_to
    )

    # Get DOT distribution with filtered parks
    dot_distribution = db.query(
        DOT.name,
        DOT.id,
        func.count(Park.id).label('count')
    ).outerjoin(
        Park, and_(DOT.id == Park.dot_id, Park.id.in_(
            park_query.with_entities(Park.id)))
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
            "offer_types": [],
            "customer_l2_codes": [],
            "customer_l3_codes": []
        }

    # Get DOTs
    dots = db.query(DOT).filter(DOT.id.in_(accessible_dots)).all()

    # Get unique values for filters
    # Get Actel Codes with their associated DOT IDs
    actel_codes_with_dots = query.filter(
        Park.actel_code.isnot(None),
        Park.dot_id.isnot(None)
    ).with_entities(
        Park.actel_code, Park.dot_id
    ).distinct().limit(200).all()
    
    # Build mapping of DOT ID to Actel Codes
    dot_actel_mapping = {}
    all_actel_codes = set()
    for actel_code, dot_id in actel_codes_with_dots:
        if actel_code and dot_id:
            all_actel_codes.add(actel_code)
            if dot_id not in dot_actel_mapping:
                dot_actel_mapping[dot_id] = []
            if actel_code not in dot_actel_mapping[dot_id]:
                dot_actel_mapping[dot_id].append(actel_code)
    
    subscriber_statuses = query.filter(Park.subscriber_status.isnot(
        None)).with_entities(Park.subscriber_status).distinct().all()
    telecom_types = query.filter(Park.telecom_type.isnot(
        None)).with_entities(Park.telecom_type).distinct().all()
    offer_names = query.filter(Park.offer_name.isnot(None)).with_entities(
        Park.offer_name).distinct().limit(100).all()
    offer_types = query.filter(Park.offer_type.isnot(None)).with_entities(
        Park.offer_type).distinct().all()
    
    # Get relationships between Subscriber Status, Telecom Type, and Offer Name
    status_telecom_offer_relationships = query.filter(
        Park.subscriber_status.isnot(None),
        Park.telecom_type.isnot(None),
        Park.offer_name.isnot(None)
    ).with_entities(
        Park.subscriber_status, Park.telecom_type, Park.offer_name
    ).distinct().limit(500).all()
    
    # Build mappings for filtering
    # Map: subscriber_status -> set of telecom_types
    status_to_telecom = {}
    # Map: subscriber_status -> set of offer_names
    status_to_offers = {}
    # Map: telecom_type -> set of subscriber_statuses
    telecom_to_status = {}
    # Map: telecom_type -> set of offer_names
    telecom_to_offers = {}
    # Map: offer_name -> set of subscriber_statuses
    offer_to_status = {}
    # Map: offer_name -> set of telecom_types
    offer_to_telecom = {}
    
    for status, telecom, offer in status_telecom_offer_relationships:
        if status and telecom and offer:
            # Status -> Telecom
            if status not in status_to_telecom:
                status_to_telecom[status] = set()
            status_to_telecom[status].add(telecom)
            
            # Status -> Offer
            if status not in status_to_offers:
                status_to_offers[status] = set()
            status_to_offers[status].add(offer)
            
            # Telecom -> Status
            if telecom not in telecom_to_status:
                telecom_to_status[telecom] = set()
            telecom_to_status[telecom].add(status)
            
            # Telecom -> Offer
            if telecom not in telecom_to_offers:
                telecom_to_offers[telecom] = set()
            telecom_to_offers[telecom].add(offer)
            
            # Offer -> Status
            if offer not in offer_to_status:
                offer_to_status[offer] = set()
            offer_to_status[offer].add(status)
            
            # Offer -> Telecom
            if offer not in offer_to_telecom:
                offer_to_telecom[offer] = set()
            offer_to_telecom[offer].add(telecom)
    customer_l2_codes = query.filter(Park.customer_l2_code.isnot(None)).with_entities(
        Park.customer_l2_code, Park.customer_l2_description).distinct().limit(50).all()
    
    # Get Customer L2 and L3 codes with their relationships
    l2_l3_relationships = query.filter(
        Park.customer_l2_code.isnot(None),
        Park.customer_l3_code.isnot(None)
    ).with_entities(
        Park.customer_l2_code, Park.customer_l3_code, Park.customer_l3_description
    ).distinct().limit(200).all()
    
    # Build mapping of L2 Code to L3 Codes
    l2_l3_mapping = {}
    all_l3_codes = set()
    for l2_code, l3_code, l3_description in l2_l3_relationships:
        if l2_code and l3_code:
            all_l3_codes.add((l3_code, l3_description))
            if l2_code not in l2_l3_mapping:
                l2_l3_mapping[l2_code] = []
            # Check if this L3 code is already in the list for this L2 code
            if not any(item["code"] == l3_code for item in l2_l3_mapping[l2_code]):
                l2_l3_mapping[l2_code].append({
                    "code": l3_code,
                    "description": l3_description or "N/A"
                })
    
    # Get all unique L3 codes (for when no L2 is selected)
    customer_l3_codes = query.filter(Park.customer_l3_code.isnot(None)).with_entities(
        Park.customer_l3_code, Park.customer_l3_description).distinct().limit(50).all()

    return {
        "dots": [{"id": dot.id, "name": dot.name} for dot in dots],
        "actel_codes": sorted(list(all_actel_codes)),
        "dot_actel_mapping": {str(dot_id): codes for dot_id, codes in dot_actel_mapping.items()},
        "subscriber_statuses": [status[0] for status in subscriber_statuses if status[0]],
        "telecom_types": [type[0] for type in telecom_types if type[0]],
        "offer_names": [name[0] for name in offer_names if name[0]],
        "offer_types": [type[0] for type in offer_types if type[0]],
        "customer_l2_codes": [{"code": item[0], "description": item[1]} for item in customer_l2_codes if item[0]],
        "customer_l3_codes": [{"code": item[0], "description": item[1]} for item in customer_l3_codes if item[0]],
        "l2_l3_mapping": {str(l2_code): l3_list for l2_code, l3_list in l2_l3_mapping.items()},
        "status_telecom_mapping": {status: list(telecoms) for status, telecoms in status_to_telecom.items()},
        "status_offer_mapping": {status: list(offers) for status, offers in status_to_offers.items()},
        "telecom_status_mapping": {telecom: list(statuses) for telecom, statuses in telecom_to_status.items()},
        "telecom_offer_mapping": {telecom: list(offers) for telecom, offers in telecom_to_offers.items()},
        "offer_status_mapping": {offer: list(statuses) for offer, statuses in offer_to_status.items()},
        "offer_telecom_mapping": {offer: list(telecoms) for offer, telecoms in offer_to_telecom.items()}
    }


@park_analytics_router.get("/preview-data")
async def get_preview_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of records to preview"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
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
        None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Get sample park records for dashboard preview with filtering support

    Returns up to `limit` park records from accessible DOTs with full details.
    All filters are applied to the preview data.

    Parameters:
        limit: Number of records to return (1-100, default 10)
        offset: Number of records to skip for pagination (default 0)
        All filter parameters are supported

    Returns:
        Dictionary with:
        - records: List of park records with key fields
        - total_available: Total records accessible to user (after filters)
        - preview_limit: Actual limit applied
        - preview_offset: Offset applied

    Example:
        GET /api/park-analytics/preview-data?limit=20&offset=0&dot_ids=1,2
    """
    
    # Log received filter parameters
    logger.info(
        f"📋 GET /preview-data - User {current_user.id} - Limit: {limit}, Offset: {offset} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    try:
        # Apply DOT-based permission filtering
        query = db.query(Park)
        accessible_dots = DOTService.get_user_accessible_dots(
            db=db, user_id=current_user.id)

        if not accessible_dots:
            logger.warning(f"User {current_user.id} has no accessible DOTs")
            return {
                "records": [],
                "total_available": 0,
                "preview_limit": limit,
                "preview_offset": offset,
                "message": "No accessible data"
            }

        query = query.filter(Park.dot_id.in_(accessible_dots))

        # Apply all filters using the shared helper function
        query = apply_filters_to_query(
            query=query,
            dot_ids=dot_ids,
            actel_codes=actel_codes,
            subscriber_statuses=subscriber_statuses,
            telecom_types=telecom_types,
            offer_names=offer_names,
            offer_types=offer_types,
            customer_l2_codes=customer_l2_codes,
            customer_l3_codes=customer_l3_codes,
            search=search,
            date_from=date_from,
            date_to=date_to
        )

        # Get total count for pagination info (after filters)
        total_count = query.count()

        # Apply pagination
        records = query.order_by(Park.created_at.desc()) \
            .offset(offset) \
            .limit(limit) \
            .all()

        # Format response with all fields
        preview_records = []
        for record in records:
            preview_records.append({
                "id": record.id,
                "file_upload_id": record.file_upload_id,
                "extraction_date": record.extraction_date.isoformat() if record.extraction_date else None,
                "dot_id": record.dot_id,
                "dot_name": record.dot.name if record.dot else "",
                "actel_code": record.actel_code or "",
                "customer_l1_code": record.customer_l1_code or "",
                "customer_l1_description": record.customer_l1_description or "",
                "customer_l2_code": record.customer_l2_code or "",
                "customer_l2_description": record.customer_l2_description or "",
                "customer_l3_code": record.customer_l3_code or "",
                "customer_l3_description": record.customer_l3_description or "",
                "telecom_type": record.telecom_type or "",
                "offer_type": record.offer_type or "",
                "offer_name": record.offer_name or "",
                "rental_fees": float(record.rental_fees) if record.rental_fees else 0.0,
                "customer_code": record.customer_code or "",
                "service_number": record.service_number or "",
                "related_service_number": record.related_service_number or "",
                "username": record.username or "",
                "subscriber_status": record.subscriber_status or "",
                "status_date": record.status_date.isoformat() if record.status_date else None,
                "creation_date": record.creation_date.isoformat() if record.creation_date else None,
                "active_date": record.active_date.isoformat() if record.active_date else None,
                "csr_name": record.csr_name or "",
                "department_name": record.department_name or "",
                "state": record.state or "",
                "area": record.area or "",
                "town": record.town or "",
                "grid": record.grid or "",
                "street": record.street or "",
                "street_number": record.street_number or "",
                "building_no": record.building_no or "",
                "unit": record.unit or "",
                "floor": record.floor or "",
                "house_no": record.house_no or "",
                "additional_address_info": record.additional_address_info or "",
                "customer_full_name": record.customer_full_name or "",
                "province": record.province or "",
                "district": record.district or "",
                "city": record.city or "",
                "postal_code": record.postal_code or "",
                "expiry_date": record.expiry_date.isoformat() if record.expiry_date else None,
                "iccid": record.iccid or "",
                "imsi": record.imsi or "",
                "contact_number": record.contact_number or "",
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })

        logger.info(
            f"User {current_user.id} retrieved {len(preview_records)} preview records "
            f"(offset={offset}, limit={limit}, total={total_count})"
        )

        return {
            "records": preview_records,
            "total_available": total_count,
            "preview_limit": limit,
            "preview_offset": offset,
            "records_returned": len(preview_records)
        }

    except Exception as e:
        logger.error(f"Error retrieving preview data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving preview data: {str(e)}"
        )


@park_analytics_router.get("/export")
async def export_data(
    format: str = Query("csv", regex="^(csv|excel)$"),
    export_type: str = Query("normal", regex="^(normal|anomalies)$", description="Export type: normal or anomalies"),
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
    """Export Parc Corporate NGBSS or Anomalie Parc NGBSS with filtering - returns Excel/CSV file"""

    # Log received filter parameters
    logger.info(
        f"📤 GET /export - User {current_user.id} - Type: {export_type} - Format: {format} - Filters: "
        f"dot_ids={dot_ids}, actel_codes={actel_codes}, "
        f"subscriber_statuses={subscriber_statuses}, telecom_types={telecom_types}, "
        f"offer_names={offer_names}, offer_types={offer_types}, "
        f"customer_l2_codes={customer_l2_codes}, customer_l3_codes={customer_l3_codes}, "
        f"search={search}, date_from={date_from}, date_to={date_to}"
    )

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        raise HTTPException(status_code=403, detail="No accessible data")

    # Apply single value filters (backward compatibility) - merge into dot_ids if needed
    if dot_filter:
        if dot_ids:
            # Merge with existing dot_ids
            dot_id_list = [int(id.strip()) for id in dot_ids.split(',') if id.strip()]
            if int(dot_filter) not in dot_id_list:
                dot_id_list.append(int(dot_filter))
            dot_ids = ','.join(map(str, dot_id_list))
        else:
            dot_ids = dot_filter

    # Apply all filters using the shared helper function for consistency
    query = apply_filters_to_query(
        query=query,
        dot_ids=dot_ids,
        actel_codes=actel_codes,
        subscriber_statuses=subscriber_statuses,
        telecom_types=telecom_types,
        offer_names=offer_names,
        offer_types=offer_types,
        customer_l2_codes=customer_l2_codes,
        customer_l3_codes=customer_l3_codes,
        search=search,
        date_from=date_from,
        date_to=date_to
    )

    # Apply backward compatibility single value filters (if not already handled)
    if actel_code_filter and not actel_codes:
        query = query.filter(Park.actel_code.ilike(f"%{actel_code_filter}%"))
    if subscriber_status_filter and not subscriber_statuses:
        query = query.filter(Park.subscriber_status == subscriber_status_filter)
    if telecom_type_filter and not telecom_types:
        query = query.filter(Park.telecom_type == telecom_type_filter)

    # If exporting anomalies, filter for anomaly criteria
    if export_type == "anomalies":
        anomaly_offer_names = ["Moohtarif", "Solutions Hébergements"]
        anomaly_l3_categories = [5, 57]
        anomaly_telecom_types = ["WIFI", "WIMAX", "X25"]

        anomaly_conditions = []

        # Offer names containing Moohtarif or Solutions Hébergements
        for offer in anomaly_offer_names:
            anomaly_conditions.append(Park.offer_name.ilike(f"%{offer}%"))

        # Customer L3 codes 5 or 57
        anomaly_conditions.append(Park.customer_l3_code.in_(anomaly_l3_categories))

        # Telecom types: WIFI, WIMAX, X25
        anomaly_conditions.append(Park.telecom_type.in_(anomaly_telecom_types))

        # Apply OR condition for anomalies
        query = query.filter(or_(*anomaly_conditions))

    # Get total count first for better error handling
    total_count = query.count()

    if total_count == 0:
        # Return empty file for consistency
        raise HTTPException(status_code=404, detail="No data found with applied filters")

    # Get ALL data - no limit
    parks = query.all()

    logger.info(
        f"Exporting {total_count:,} records for user {current_user.id} (type: {export_type}, format: {format})"
    )

    # Convert to records for DataFrame
    records = []
    for park in parks:
        try:
            records.append({
                # Core identifiers
                "DOT ID": park.dot_id or "",
                "DOT Name": park.dot.name if park.dot else "",
                "Customer Code": park.customer_code or "",
                "Service Number": park.service_number or "",
                "Related Service Number": park.related_service_number or "",
                "Customer Name": park.customer_full_name or "",
                "Username": park.username or "",
                "Actel Code": park.actel_code or "",

                # Subscriber and telecom info
                "Subscriber Status": park.subscriber_status or "",
                "Telecom Type": park.telecom_type or "",
                "Offer Name": park.offer_name or "",
                "Offer Type": park.offer_type or "",
                "Rental Fees": float(park.rental_fees) if park.rental_fees else 0.0,

                # Customer hierarchy
                "Customer L1 Code": park.customer_l1_code or "",
                "Customer L1 Description": park.customer_l1_description or "",
                "Customer L2 Code": park.customer_l2_code or "",
                "Customer L2 Description": park.customer_l2_description or "",
                "Customer L3 Code": park.customer_l3_code or "",
                "Customer L3 Description": park.customer_l3_description or "",

                # CSR and department
                "CSR Name": park.csr_name or "",
                "Department Name": park.department_name or "",

                # Address information
                "State": park.state or "",
                "Province": park.province or "",
                "Area": park.area or "",
                "District": park.district or "",
                "City": park.city or "",
                "Town": park.town or "",
                "Postal Code": park.postal_code or "",
                "Street": park.street or "",
                "Street Number": park.street_number or "",
                "Building No": park.building_no or "",
                "Unit": park.unit or "",
                "Floor": park.floor or "",
                "House No": park.house_no or "",
                "Grid": park.grid or "",
                "Additional Address Info": park.additional_address_info or "",

                # Contact and technical info
                "Contact Number": park.contact_number or "",
                "ICCID": park.iccid or "",
                "IMSI": park.imsi or "",

                # Dates
                "Status Date": park.status_date.isoformat() if park.status_date else "",
                "Creation Date": park.creation_date.isoformat() if park.creation_date else "",
                "Active Date": park.active_date.isoformat() if park.active_date else "",
                "Expiry Date": park.expiry_date.isoformat() if park.expiry_date else "",
                "Extraction Date": park.extraction_date.isoformat() if park.extraction_date else "",

                # Metadata
                "Created At": park.created_at.isoformat() if park.created_at else "",
                "Updated At": park.updated_at.isoformat() if park.updated_at else ""
            })
        except Exception as e:
            logger.error(f"Error processing park record {park.id}: {e}")
            continue

    # Create DataFrame
    df = pd.DataFrame(records)

    # Generate file
    output = io.BytesIO()

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    if export_type == "anomalies":
        base_filename = f"Anomalie_Parc_NGBSS_{timestamp}"
    else:
        base_filename = f"Parc_Corporate_NGBSS_{timestamp}"

    if format == "excel":
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Parc Data')
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_filename}.xlsx"
    else:  # csv
        df.to_csv(output, index=False, encoding='utf-8-sig')
        media_type = "text/csv"
        filename = f"{base_filename}.csv"

    output.seek(0)

    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
