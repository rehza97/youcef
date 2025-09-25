from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from database.connection import get_db
from core.security import get_current_user
from models.park import Park
from models.dot import DOT
from models.user import User
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date
import pandas as pd
import io
from services.park_processing import ParkDataProcessor
from services.background_processor import background_processor, ProcessingStatus
from services.processing_websocket import processing_ws_manager

router = APIRouter(prefix="/api/parks", tags=["parks"])


@router.post("/set-max-rows-limit")
async def set_max_rows_limit(
    limit: int = Query(..., description="Maximum number of rows to process"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set the maximum number of rows to process (Admin only)"""
    # RBAC: Only ADMIN can set limits
    from services.permission_service import PermissionService
    PermissionService.check_admin_permissions(current_user, db)

    if limit < 1 or limit > 1000000:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 1,000,000"
        )

    background_processor.set_max_rows_limit(limit)

    return {
        "success": True,
        "message": f"Max rows limit set to {limit}",
        "limit": limit
    }


@router.post("/cancel-all-tasks")
async def cancel_all_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel all active processing tasks (Admin only)"""
    # RBAC: Only ADMIN can cancel tasks
    from services.permission_service import PermissionService
    PermissionService.check_admin_permissions(current_user, db)

    cancelled_count = 0
    for task_id in list(background_processor.active_tasks.keys()):
        if background_processor.cancel_task(task_id):
            cancelled_count += 1

    return {
        "success": True,
        "message": f"Cancelled {cancelled_count} tasks",
        "cancelled_count": cancelled_count
    }

# Pydantic models for request/response


class ParkDataResponse(BaseModel):
    id: int
    extraction_date: Optional[date] = None
    dot_id: Optional[int] = None
    actel_code: Optional[str] = None
    customer_l1_code: Optional[str] = None
    customer_l1_description: Optional[str] = None
    customer_l2_code: Optional[str] = None
    customer_l2_description: Optional[str] = None
    customer_l3_code: Optional[str] = None
    customer_l3_description: Optional[str] = None
    telecom_type: Optional[str] = None
    offer_type: Optional[str] = None
    offer_name: Optional[str] = None
    rental_fees: Optional[float] = None
    customer_code: Optional[str] = None
    service_number: Optional[str] = None
    related_service_number: Optional[str] = None
    username: Optional[str] = None
    subscriber_status: Optional[str] = None
    status_date: Optional[date] = None
    creation_date: Optional[date] = None
    active_date: Optional[date] = None
    csr_name: Optional[str] = None
    department_name: Optional[str] = None
    state: Optional[str] = None
    area: Optional[str] = None
    town: Optional[str] = None
    grid: Optional[str] = None
    street: Optional[str] = None
    street_number: Optional[str] = None
    building_no: Optional[str] = None
    unit: Optional[str] = None
    floor: Optional[str] = None
    house_no: Optional[str] = None
    additional_address_info: Optional[str] = None
    customer_full_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    expiry_date: Optional[date] = None
    iccid: Optional[str] = None
    imsi: Optional[str] = None
    contact_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ParkDataListResponse(BaseModel):
    data: List[ParkDataResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DOTCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DOTResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ParkCreate(BaseModel):
    extraction_date: Optional[date] = None
    dot_id: Optional[int] = None
    actel_code: Optional[str] = None
    customer_l1_code: Optional[str] = None
    customer_l1_description: Optional[str] = None
    customer_l2_code: Optional[str] = None
    customer_l2_description: Optional[str] = None
    customer_l3_code: Optional[str] = None
    customer_l3_description: Optional[str] = None
    telecom_type: Optional[str] = None
    offer_type: Optional[str] = None
    offer_name: Optional[str] = None
    rental_fees: Optional[float] = None
    customer_code: Optional[str] = None
    service_number: Optional[str] = None
    related_service_number: Optional[str] = None
    username: Optional[str] = None
    subscriber_status: Optional[str] = None
    status_date: Optional[date] = None
    creation_date: Optional[date] = None
    active_date: Optional[date] = None
    csr_name: Optional[str] = None
    department_name: Optional[str] = None
    state: Optional[str] = None
    area: Optional[str] = None
    town: Optional[str] = None
    grid: Optional[str] = None
    street: Optional[str] = None
    street_number: Optional[str] = None
    building_no: Optional[str] = None
    unit: Optional[str] = None
    floor: Optional[str] = None
    house_no: Optional[str] = None
    additional_address_info: Optional[str] = None
    customer_full_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    expiry_date: Optional[date] = None
    iccid: Optional[str] = None
    imsi: Optional[str] = None
    contact_number: Optional[str] = None


class ParkResponse(BaseModel):
    id: int
    extraction_date: Optional[date] = None
    dot_id: Optional[int] = None
    actel_code: Optional[str] = None
    customer_l1_code: Optional[str] = None
    customer_l1_description: Optional[str] = None
    customer_l2_code: Optional[str] = None
    customer_l2_description: Optional[str] = None
    customer_l3_code: Optional[str] = None
    customer_l3_description: Optional[str] = None
    telecom_type: Optional[str] = None
    offer_type: Optional[str] = None
    offer_name: Optional[str] = None
    rental_fees: Optional[float] = None
    customer_code: Optional[str] = None
    service_number: Optional[str] = None
    related_service_number: Optional[str] = None
    username: Optional[str] = None
    subscriber_status: Optional[str] = None
    status_date: Optional[date] = None
    creation_date: Optional[date] = None
    active_date: Optional[date] = None
    csr_name: Optional[str] = None
    department_name: Optional[str] = None
    state: Optional[str] = None
    area: Optional[str] = None
    town: Optional[str] = None
    grid: Optional[str] = None
    street: Optional[str] = None
    street_number: Optional[str] = None
    building_no: Optional[str] = None
    unit: Optional[str] = None
    floor: Optional[str] = None
    house_no: Optional[str] = None
    additional_address_info: Optional[str] = None
    customer_full_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    expiry_date: Optional[date] = None
    iccid: Optional[str] = None
    imsi: Optional[str] = None
    contact_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    dot: Optional[DOTResponse] = None

    class Config:
        from_attributes = True

# DOT endpoints


@router.post("/dots/", response_model=DOTResponse)
def create_dot(dot: DOTCreate, db: Session = Depends(get_db)):
    """Create a new DOT"""
    db_dot = DOT(
        name=dot.name,
        description=dot.description,
        created_at=datetime.utcnow()
    )
    db.add(db_dot)
    db.commit()
    db.refresh(db_dot)
    return db_dot


@router.get("/dots/", response_model=List[DOTResponse])
def get_dots(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all DOTs"""
    dots = db.query(DOT).offset(skip).limit(limit).all()
    return dots


@router.get("/dots/{dot_id}", response_model=DOTResponse)
def get_dot(dot_id: int, db: Session = Depends(get_db)):
    """Get a specific DOT by ID"""
    dot = db.query(DOT).filter(DOT.id == dot_id).first()
    if not dot:
        raise HTTPException(status_code=404, detail="DOT not found")
    return dot

# Park endpoints


@router.post("/", response_model=ParkResponse)
def create_park(park: ParkCreate, db: Session = Depends(get_db)):
    """Create a new Park record"""
    db_park = Park(
        **park.dict(),
        created_at=datetime.utcnow()
    )
    db.add(db_park)
    db.commit()
    db.refresh(db_park)
    return db_park


@router.get("/", response_model=List[ParkResponse])
def get_parks(
    skip: int = 0,
    limit: int = 100,
    customer_code: Optional[str] = None,
    service_number: Optional[str] = None,
    subscriber_status: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get Park records with optional filtering"""
    query = db.query(Park)

    if customer_code:
        query = query.filter(Park.customer_code.contains(customer_code))
    if service_number:
        query = query.filter(Park.service_number.contains(service_number))
    if subscriber_status:
        query = query.filter(Park.subscriber_status == subscriber_status)
    if state:
        query = query.filter(Park.state == state)

    parks = query.offset(skip).limit(limit).all()
    return parks


@router.get("/data", response_model=ParkDataListResponse)
async def get_saved_park_data(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        50, ge=1, le=1000, description="Number of records per page"),
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    subscriber_status: Optional[str] = Query(
        None, description="Filter by subscriber status"),
    telecom_type: Optional[str] = Query(
        None, description="Filter by telecom type"),
    offer_type: Optional[str] = Query(None, description="Filter by offer type")
):
    """Get saved park data with pagination and filtering"""

    # Build query
    query = db.query(Park)

    # Apply search filter
    if search:
        search_filter = or_(
            Park.customer_code.ilike(f"%{search}%"),
            Park.service_number.ilike(f"%{search}%"),
            Park.customer_full_name.ilike(f"%{search}%"),
            Park.username.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    # Apply status filter
    if subscriber_status:
        query = query.filter(Park.subscriber_status == subscriber_status)

    # Apply telecom type filter
    if telecom_type:
        query = query.filter(Park.telecom_type == telecom_type)

    # Apply offer type filter
    if offer_type:
        query = query.filter(Park.offer_type == offer_type)

    # Get total count
    total = query.count()

    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    # Get data
    parks = query.order_by(Park.created_at.desc()).offset(
        skip).limit(page_size).all()

    return ParkDataListResponse(
        data=parks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/data/stats")
async def get_park_data_stats(db: Session = Depends(get_db)):
    """Get statistics about saved park data"""

    total_records = db.query(Park).count()

    # Get unique values for filters
    subscriber_statuses = db.query(Park.subscriber_status).distinct().all()
    telecom_types = db.query(Park.telecom_type).distinct().all()
    offer_types = db.query(Park.offer_type).distinct().all()

    # Get recent records count (last 24 hours)
    from datetime import datetime, timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_records = db.query(Park).filter(
        Park.created_at >= yesterday).count()

    return {
        "total_records": total_records,
        "recent_records": recent_records,
        "subscriber_statuses": [status[0] for status in subscriber_statuses if status[0]],
        "telecom_types": [type[0] for type in telecom_types if type[0]],
        "offer_types": [type[0] for type in offer_types if type[0]]
    }


@router.get("/{park_id}", response_model=ParkResponse)
def get_park(park_id: int, db: Session = Depends(get_db)):
    """Get a specific Park record by ID"""
    park = db.query(Park).filter(Park.id == park_id).first()
    if not park:
        raise HTTPException(status_code=404, detail="Park record not found")
    return park


@router.get("/stats/summary")
def get_park_stats(db: Session = Depends(get_db)):
    """Get summary statistics for Park records"""
    total_parks = db.query(Park).count()
    total_dots = db.query(DOT).count()

    # Get subscriber status distribution
    status_distribution = db.query(
        Park.subscriber_status,
        func.count(Park.id)
    ).group_by(Park.subscriber_status).all()

    # Get state distribution
    state_distribution = db.query(
        Park.state,
        func.count(Park.id)
    ).group_by(Park.state).all()

    return {
        "total_parks": total_parks,
        "total_dots": total_dots,
        "subscriber_status_distribution": dict(status_distribution),
        "state_distribution": dict(state_distribution)
    }

# New endpoints for Parc Corporate NGBSS processing


@router.post("/process-excel")
async def process_excel_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Process Excel file with Parc Corporate NGBSS rules"""
    try:
        # Read file content
        content = await file.read()

        # Create processor
        processor = ParkDataProcessor(db)

        # Save file temporarily
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Process the file
            result = processor.process_excel_data(tmp_file_path)

            if result["success"]:
                # Save to database
                save_result = processor.save_to_database(result["data"])
                result["save_result"] = save_result

            return result

        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/process-excel-background")
async def process_excel_file_background(
    file: UploadFile = File(...),
    user_id: int = 1  # TODO: Get from authentication
):
    """Process Excel file in background with high performance"""
    try:
        # Read file content
        content = await file.read()

        # Save file temporarily
        import tempfile
        import os
        import uuid

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Generate file ID (you might want to save this to database)
        file_id = str(uuid.uuid4())

        # Start background processing
        task_id = background_processor.start_processing(
            file_path=tmp_file_path,
            file_id=file_id,
            user_id=user_id
        )

        return {
            "success": True,
            "task_id": task_id,
            "file_id": file_id,
            "message": "Processing started in background",
            "status": ProcessingStatus.PROCESSING
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error starting background processing: {str(e)}")


@router.get("/processing-status/{task_id}")
def get_processing_status(task_id: str):
    """Get processing status for a specific task"""
    status = background_processor.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": status["status"],
        "progress": status["progress"],
        "total_rows": status["total_rows"],
        "processed_rows": status["processed_rows"],
        "filtered_rows": status["filtered_rows"],
        "saved_rows": status["saved_rows"],
        "errors": status["errors"],
        "anomalies": status["anomalies"],
        "statistics": status["statistics"],
        "start_time": status["start_time"],
        "end_time": status["end_time"]
    }


@router.get("/processing-tasks")
def get_all_processing_tasks():
    """Get all active processing tasks"""
    tasks = background_processor.get_all_tasks()

    # Return simplified task info
    simplified_tasks = {}
    for task_id, task in tasks.items():
        simplified_tasks[task_id] = {
            "task_id": task_id,
            "file_id": task["file_id"],
            "user_id": task["user_id"],
            "status": task["status"],
            "progress": task["progress"],
            "total_rows": task["total_rows"],
            "processed_rows": task["processed_rows"],
            "start_time": task["start_time"],
            "end_time": task["end_time"]
        }

    return simplified_tasks


@router.post("/cancel-processing/{task_id}")
def cancel_processing_task(task_id: str):
    """Cancel a processing task"""
    success = background_processor.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "success": True,
        "message": f"Task {task_id} cancelled",
        "task_id": task_id
    }


@router.post("/cleanup-tasks")
def cleanup_completed_tasks(max_age_hours: int = 24):
    """Clean up old completed tasks"""
    background_processor.cleanup_completed_tasks(max_age_hours)

    return {
        "success": True,
        "message": f"Cleaned up tasks older than {max_age_hours} hours"
    }


@router.delete("/data/clear-all")
async def clear_all_park_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all park data from the database (Admin only)"""
    # RBAC: Only ADMIN can clear all data
    from services.permission_service import PermissionService
    PermissionService.check_admin_permissions(current_user, db)

    try:
        # Get count before deletion
        total_count = db.query(Park).count()

        # Delete all park records
        deleted_count = db.query(Park).delete()

        # Commit the transaction
        db.commit()

        return {
            "success": True,
            "message": f"Successfully cleared {deleted_count} park records",
            "deleted_count": deleted_count,
            "total_count": total_count
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear park data: {str(e)}"
        )


@router.get("/analytics/overview")
def get_overview_analytics(db: Session = Depends(get_db)):
    """Get overview analytics for Parc Corporate NGBSS"""

    # Total counts
    total_parks = db.query(Park).count()
    total_dots = db.query(DOT).count()

    # Active vs Inactive
    active_count = db.query(Park).filter(
        Park.subscriber_status == "Active"
    ).count()

    inactive_count = total_parks - active_count

    # Recent activity (last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_count = db.query(Park).filter(
        Park.created_at >= thirty_days_ago
    ).count()

    return {
        "total_parks": total_parks,
        "total_dots": total_dots,
        "active_parks": active_count,
        "inactive_parks": inactive_count,
        "recent_activity": recent_count,
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/analytics/by-dot")
def get_analytics_by_dot(db: Session = Depends(get_db)):
    """Get analytics grouped by DOT"""

    # Get DOT statistics with park counts
    dot_stats = db.query(
        DOT.name,
        DOT.id,
        func.count(Park.id).label('park_count'),
        func.count(func.distinct(Park.customer_code)).label('unique_customers')
    ).outerjoin(Park, DOT.id == Park.dot_id)\
     .group_by(DOT.id, DOT.name)\
     .all()

    # Get subscriber status by DOT
    status_by_dot = db.query(
        DOT.name,
        Park.subscriber_status,
        func.count(Park.id).label('count')
    ).join(Park, DOT.id == Park.dot_id)\
     .group_by(DOT.name, Park.subscriber_status)\
     .all()

    # Format results
    dots_data = []
    for dot in dot_stats:
        dot_data = {
            "dot_name": dot.name,
            "dot_id": dot.id,
            "total_parks": dot.park_count,
            "unique_customers": dot.unique_customers,
            "subscriber_status_breakdown": {}
        }

        # Add subscriber status breakdown
        for status in status_by_dot:
            if status.name == dot.name:
                dot_data["subscriber_status_breakdown"][status.subscriber_status] = status.count

        dots_data.append(dot_data)

    return {
        "by_dot": dots_data,
        "total_dots": len(dots_data)
    }


@router.get("/analytics/by-telecom-type")
def get_analytics_by_telecom_type(db: Session = Depends(get_db)):
    """Get analytics grouped by Telecom Type"""

    telecom_stats = db.query(
        Park.telecom_type,
        func.count(Park.id).label('count'),
        func.count(func.distinct(Park.customer_code)).label('unique_customers')
    ).filter(Park.telecom_type.isnot(None))\
     .group_by(Park.telecom_type)\
     .all()

    # Get offer types by telecom type
    offer_by_telecom = db.query(
        Park.telecom_type,
        Park.offer_type,
        func.count(Park.id).label('count')
    ).filter(
        and_(
            Park.telecom_type.isnot(None),
            Park.offer_type.isnot(None)
        )
    ).group_by(Park.telecom_type, Park.offer_type)\
     .all()

    # Format results
    telecom_data = []
    for telecom in telecom_stats:
        telecom_info = {
            "telecom_type": telecom.telecom_type,
            "total_parks": telecom.count,
            "unique_customers": telecom.unique_customers,
            "offer_types": {}
        }

        # Add offer types
        for offer in offer_by_telecom:
            if offer.telecom_type == telecom.telecom_type:
                telecom_info["offer_types"][offer.offer_type] = offer.count

        telecom_data.append(telecom_info)

    return {
        "by_telecom_type": telecom_data,
        "total_telecom_types": len(telecom_data)
    }


@router.get("/analytics/by-customer-l2")
def get_analytics_by_customer_l2(db: Session = Depends(get_db)):
    """Get analytics grouped by Customer L2"""

    l2_stats = db.query(
        Park.customer_l2_code,
        Park.customer_l2_description,
        func.count(Park.id).label('count'),
        func.count(func.distinct(Park.customer_code)).label('unique_customers')
    ).filter(Park.customer_l2_code.isnot(None))\
     .group_by(Park.customer_l2_code, Park.customer_l2_description)\
     .all()

    # Get L3 breakdown by L2
    l3_by_l2 = db.query(
        Park.customer_l2_code,
        Park.customer_l3_code,
        Park.customer_l3_description,
        func.count(Park.id).label('count')
    ).filter(
        and_(
            Park.customer_l2_code.isnot(None),
            Park.customer_l3_code.isnot(None)
        )
    ).group_by(Park.customer_l2_code, Park.customer_l3_code, Park.customer_l3_description)\
     .all()

    # Format results
    l2_data = []
    for l2 in l2_stats:
        l2_info = {
            "customer_l2_code": l2.customer_l2_code,
            "customer_l2_description": l2.customer_l2_description,
            "total_parks": l2.count,
            "unique_customers": l2.unique_customers,
            "l3_breakdown": {}
        }

        # Add L3 breakdown
        for l3 in l3_by_l2:
            if l3.customer_l2_code == l2.customer_l2_code:
                l3_key = f"{l3.customer_l3_code} - {l3.customer_l3_description}"
                l2_info["l3_breakdown"][l3_key] = l3.count

        l2_data.append(l2_info)

    return {
        "by_customer_l2": l2_data,
        "total_l2_categories": len(l2_data)
    }


@router.get("/analytics/by-customer-l3")
def get_analytics_by_customer_l3(db: Session = Depends(get_db)):
    """Get analytics grouped by Customer L3"""

    l3_stats = db.query(
        Park.customer_l3_code,
        Park.customer_l3_description,
        func.count(Park.id).label('count'),
        func.count(func.distinct(Park.customer_code)).label('unique_customers')
    ).filter(Park.customer_l3_code.isnot(None))\
     .group_by(Park.customer_l3_code, Park.customer_l3_description)\
     .all()

    # Get subscriber status by L3
    status_by_l3 = db.query(
        Park.customer_l3_code,
        Park.subscriber_status,
        func.count(Park.id).label('count')
    ).filter(
        and_(
            Park.customer_l3_code.isnot(None),
            Park.subscriber_status.isnot(None)
        )
    ).group_by(Park.customer_l3_code, Park.subscriber_status)\
     .all()

    # Format results
    l3_data = []
    for l3 in l3_stats:
        l3_info = {
            "customer_l3_code": l3.customer_l3_code,
            "customer_l3_description": l3.customer_l3_description,
            "total_parks": l3.count,
            "unique_customers": l3.unique_customers,
            "subscriber_status_breakdown": {}
        }

        # Add subscriber status breakdown
        for status in status_by_l3:
            if status.customer_l3_code == l3.customer_l3_code:
                l3_info["subscriber_status_breakdown"][status.subscriber_status] = status.count

        l3_data.append(l3_info)

    return {
        "by_customer_l3": l3_data,
        "total_l3_categories": len(l3_data)
    }


@router.get("/filters/options")
def get_filter_options(db: Session = Depends(get_db)):
    """Get available filter options for the frontend"""

    # Get unique values for each filter
    dots = db.query(DOT.name, DOT.id).all()
    actel_codes = db.query(Park.actel_code).filter(
        Park.actel_code.isnot(None)).distinct().all()
    subscriber_statuses = db.query(Park.subscriber_status).filter(
        Park.subscriber_status.isnot(None)).distinct().all()
    telecom_types = db.query(Park.telecom_type).filter(
        Park.telecom_type.isnot(None)).distinct().all()
    offer_names = db.query(Park.offer_name).filter(
        Park.offer_name.isnot(None)).distinct().all()
    customer_l2_codes = db.query(Park.customer_l2_code, Park.customer_l2_description).filter(
        Park.customer_l2_code.isnot(None)).distinct().all()
    customer_l3_codes = db.query(Park.customer_l3_code, Park.customer_l3_description).filter(
        Park.customer_l3_code.isnot(None)).distinct().all()

    return {
        "dots": [{"id": dot.id, "name": dot.name} for dot in dots],
        "actel_codes": [code[0] for code in actel_codes],
        "subscriber_statuses": [status[0] for status in subscriber_statuses],
        "telecom_types": [ttype[0] for ttype in telecom_types],
        "offer_names": [offer[0] for offer in offer_names],
        "customer_l2_codes": [{"code": l2[0], "description": l2[1]} for l2 in customer_l2_codes],
        "customer_l3_codes": [{"code": l3[0], "description": l3[1]} for l3 in customer_l3_codes]
    }


@router.get("/filtered")
def get_filtered_parks(
    skip: int = 0,
    limit: int = 100,
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
    customer_l2_codes: Optional[str] = Query(
        None, description="Comma-separated L2 codes"),
    customer_l3_codes: Optional[str] = Query(
        None, description="Comma-separated L3 codes"),
    search: Optional[str] = Query(
        None, description="Search in customer code, service number, or customer name"),
    db: Session = Depends(get_db)
):
    """Get filtered Park records with advanced filtering"""

    query = db.query(Park)

    # Apply filters
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

    if customer_l2_codes:
        l2_list = [code.strip()
                   for code in customer_l2_codes.split(',') if code.strip()]
        query = query.filter(Park.customer_l2_code.in_(l2_list))

    if customer_l3_codes:
        l3_list = [code.strip()
                   for code in customer_l3_codes.split(',') if code.strip()]
        query = query.filter(Park.customer_l3_code.in_(l3_list))

    # Apply search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Park.customer_code.like(search_term),
                Park.service_number.like(search_term),
                Park.customer_full_name.like(search_term)
            )
        )

    # Get total count
    total_count = query.count()

    # Apply pagination
    parks = query.offset(skip).limit(limit).all()

    return {
        "parks": parks,
        "total_count": total_count,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total_count
    }
