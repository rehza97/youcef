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

logger = logging.getLogger(__name__)

park_analytics_router = APIRouter()


@park_analytics_router.get("/overview")
async def get_park_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overview analytics for Parc Corporate NGBSS with DOT-based permissions"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        # User has no DOT access, return zero stats
        return {
            "total_active_subscribers": 0,
            "total_dots": 0,
            "recent_activity": 0,
            "last_updated": datetime.utcnow().isoformat()
        }

    # Total active subscribers
    total_active = query.filter(
        Park.subscriber_status.in_(["Active", "ACTIVE", "active"])
    ).count()

    # Total accessible DOTs
    total_dots = len(accessible_dots) if accessible_dots else 0

    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = query.filter(Park.created_at >= seven_days_ago).count()

    return {
        "total_active_subscribers": total_active,
        "total_dots": total_dots,
        "recent_activity": recent_activity,
        "last_updated": datetime.utcnow().isoformat()
    }


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
    """Get distribution by Subscriber Status"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

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
            "status": item.subscriber_status,
            "count": item.count,
            "percentage": round(percentage, 2)
        })

    return {
        "distribution": distribution,
        "total": total_count
    }


@park_analytics_router.get("/by-customer-l2")
async def get_by_customer_l2(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get distribution by Code Customer L2"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Get customer L2 distribution
    l2_distribution = query.filter(
        and_(
            Park.customer_l2_code.isnot(None),
            Park.customer_l2_description.isnot(None)
        )
    ).with_entities(
        Park.customer_l2_code,
        Park.customer_l2_description,
        func.count(Park.id).label('count')
    ).group_by(
        Park.customer_l2_code,
        Park.customer_l2_description
    ).order_by(func.count(Park.id).desc()).limit(20).all()

    total_count = sum([item.count for item in l2_distribution])

    distribution = []
    for item in l2_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "code": item.customer_l2_code,
            "description": item.customer_l2_description or f"Category {item.customer_l2_code}",
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
    db: Session = Depends(get_db)
):
    """Get distribution by Code Customer L3"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        return {"distribution": [], "total": 0}

    # Get customer L3 distribution
    l3_distribution = query.filter(
        and_(
            Park.customer_l3_code.isnot(None),
            Park.customer_l3_description.isnot(None)
        )
    ).with_entities(
        Park.customer_l3_code,
        Park.customer_l3_description,
        func.count(Park.id).label('count')
    ).group_by(
        Park.customer_l3_code,
        Park.customer_l3_description
    ).order_by(func.count(Park.id).desc()).limit(20).all()

    total_count = sum([item.count for item in l3_distribution])

    distribution = []
    for item in l3_distribution:
        percentage = (item.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            "code": item.customer_l3_code,
            "description": item.customer_l3_description or f"Category {item.customer_l3_code}",
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
    dot_filter: Optional[str] = Query(None),
    actel_code_filter: Optional[str] = Query(None),
    subscriber_status_filter: Optional[str] = Query(None),
    telecom_type_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export park data with applied filters"""

    # Apply DOT-based permission filtering
    query = db.query(Park)
    accessible_dots = DOTService.get_user_accessible_dots(
        db=db, user_id=current_user.id)
    if accessible_dots:
        query = query.filter(Park.dot_id.in_(accessible_dots))
    else:
        raise HTTPException(status_code=403, detail="No accessible data")

    # Apply filters
    if dot_filter:
        query = query.filter(Park.dot_id == int(dot_filter))
    if actel_code_filter:
        query = query.filter(Park.actel_code.ilike(f"%{actel_code_filter}%"))
    if subscriber_status_filter:
        query = query.filter(Park.subscriber_status ==
                             subscriber_status_filter)
    if telecom_type_filter:
        query = query.filter(Park.telecom_type == telecom_type_filter)

    # Get data (limit to prevent memory issues)
    parks = query.limit(10000).all()

    if not parks:
        raise HTTPException(
            status_code=404, detail="No data found with applied filters")

    # Convert to dict for export
    export_data = []
    for park in parks:
        export_data.append({
            "Customer Code": park.customer_code,
            "Service Number": park.service_number,
            "Customer Name": park.customer_full_name,
            "Subscriber Status": park.subscriber_status,
            "Telecom Type": park.telecom_type,
            "Offer Name": park.offer_name,
            "Offer Type": park.offer_type,
            "Rental Fees": park.rental_fees,
            "State": park.state,
            "City": park.city,
            "Created At": park.created_at.isoformat() if park.created_at else None
        })

    return {
        "data": export_data,
        "total_records": len(export_data),
        "filters_applied": {
            "dot_filter": dot_filter,
            "actel_code_filter": actel_code_filter,
            "subscriber_status_filter": subscriber_status_filter,
            "telecom_type_filter": telecom_type_filter
        },
        "export_format": format,
        "generated_at": datetime.utcnow().isoformat()
    }

