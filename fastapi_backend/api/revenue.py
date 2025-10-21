"""
Revenue (Chiffre d'Affaires AR DOT) API Endpoints
Handles file upload, processing, and data retrieval for revenue data
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database.connection import get_db
from models.user import User
from models.revenue import RevenueJournal, AccountDescription, RevenueObjective, RevenueAnomaly
from models.file_upload import FileUpload
from services.revenue_processing import RevenueDataProcessor
from services.permission_service import PermissionService
from core.security import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime, date
import os
import shutil
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/revenue", tags=["Revenue"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class RevenueJournalResponse(BaseModel):
    id: int
    org_name: Optional[str]
    n_fact: Optional[str]
    date_fact: Optional[date]
    n_client: Optional[str]
    client: Optional[str]
    chiffre_aff_exe_dzd: Optional[float]
    tva: Optional[float]
    chiffre_aff_exe_dzd_ttc: Optional[float]
    taux_realisation_ca: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class AccountDescriptionResponse(BaseModel):
    id: int
    cpt_comptable: str
    description_cpt_comptable: Optional[str]
    type_cpte: Optional[str]

    class Config:
        from_attributes = True


class RevenueObjectiveResponse(BaseModel):
    id: int
    dot_name: str
    objectif_ca: float

    class Config:
        from_attributes = True


class RevenueAnomalyResponse(BaseModel):
    id: int
    org_name: Optional[str]
    n_fact: Optional[str]
    cpt_comptable: Optional[str]
    anomaly_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[int] = None
    processed_rows: Optional[int] = None
    anomalies: Optional[List[Dict[str, Any]]] = None


class RevenueListResponse(BaseModel):
    items: List[RevenueJournalResponse]
    total: int
    page: int
    page_size: int


class RevenueOverviewResponse(BaseModel):
    total_revenue: float
    total_records: int
    by_org_name: Dict[str, float]
    by_month: Dict[str, float]
    anomalies_count: int


# ============================================================================
# Upload Endpoints
# ============================================================================

@router.post("/upload/journal", response_model=FileUploadResponse)
async def upload_revenue_journal(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process Revenue Journal file (AT- Journal Chiffre d affaire)
    Requires: can_upload_files permission
    """
    # Check permission
    PermissionService.require_permission(
        current_user, db, "can_upload_files")

    try:
        # Save file
        upload_dir = "uploads/revenue/journal"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(
            upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create file upload record
        file_upload = FileUpload(
            filename=file.filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type="revenue_journal",
            mime_type=file.content_type,
            uploaded_by=current_user.id,
            detected_kpi_type="chiffre_affaires",
            processing_status="processing"
        )
        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # Process file
        processor = RevenueDataProcessor(db)
        result = processor.process_revenue_journal(
            file_path, file_upload.id)

        # Update file upload status
        file_upload.processing_status = "completed" if result.get(
            "success") else "failed"
        file_upload.is_processed = result.get("success", False)
        if not result.get("success"):
            file_upload.error_message = result.get("error", "Unknown error")
        db.commit()

        return FileUploadResponse(
            success=result.get("success", False),
            message="Revenue journal processed successfully" if result.get(
                "success") else f"Error: {result.get('error')}",
            file_id=file_upload.id,
            processed_rows=result.get("processed_rows", 0),
            anomalies=result.get("anomalies", [])
        )

    except Exception as e:
        logger.error(f"Error uploading revenue journal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/account-descriptions", response_model=FileUploadResponse)
async def upload_account_descriptions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload Account Descriptions file (Description Cpt Comptable.xlsx)
    Requires: can_upload_files permission
    """
    PermissionService.require_permission(
        current_user, db, "can_upload_files")

    try:
        # Save file
        upload_dir = "uploads/revenue/account_descriptions"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(
            upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create file upload record
        file_upload = FileUpload(
            filename=file.filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type="account_descriptions",
            mime_type=file.content_type,
            uploaded_by=current_user.id,
            processing_status="processing"
        )
        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # Process file
        processor = RevenueDataProcessor(db)
        result = processor.process_account_descriptions(
            file_path, file_upload.id)

        # Update status
        file_upload.processing_status = "completed" if result.get(
            "success") else "failed"
        file_upload.is_processed = result.get("success", False)
        if not result.get("success"):
            file_upload.error_message = result.get("error")
        db.commit()

        return FileUploadResponse(
            success=result.get("success", False),
            message="Account descriptions processed successfully" if result.get(
                "success") else f"Error: {result.get('error')}",
            file_id=file_upload.id,
            processed_rows=result.get("processed_rows", 0)
        )

    except Exception as e:
        logger.error(f"Error uploading account descriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/objectives", response_model=FileUploadResponse)
async def upload_revenue_objectives(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload Revenue Objectives file (Objectif C.A.xlsx)
    Requires: can_upload_files permission
    """
    PermissionService.require_permission(
        current_user, db, "can_upload_files")

    try:
        # Save file
        upload_dir = "uploads/revenue/objectives"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(
            upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create file upload record
        file_upload = FileUpload(
            filename=file.filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type="revenue_objectives",
            mime_type=file.content_type,
            uploaded_by=current_user.id,
            processing_status="processing"
        )
        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # Process file
        processor = RevenueDataProcessor(db)
        result = processor.process_revenue_objectives(
            file_path, file_upload.id)

        # Update status
        file_upload.processing_status = "completed" if result.get(
            "success") else "failed"
        file_upload.is_processed = result.get("success", False)
        if not result.get("success"):
            file_upload.error_message = result.get("error")
        db.commit()

        return FileUploadResponse(
            success=result.get("success", False),
            message="Revenue objectives processed successfully" if result.get(
                "success") else f"Error: {result.get('error')}",
            file_id=file_upload.id,
            processed_rows=result.get("processed_rows", 0)
        )

    except Exception as e:
        logger.error(f"Error uploading revenue objectives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Continued in next file due to length limit...
