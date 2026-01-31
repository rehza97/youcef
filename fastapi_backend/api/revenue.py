"""
Revenue (Chiffre d'Affaires AR DOT) API Endpoints
Handles file upload, processing, and data retrieval for revenue data
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import extract, distinct, or_
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
    file_upload_id: Optional[int] = None
    dot_id: Optional[int] = None
    org_name: Optional[str] = None
    origine: Optional[str] = None
    n_fact: Optional[str] = None
    typ_fact: Optional[str] = None
    date_fact: Optional[date] = None
    n_client: Optional[str] = None
    client: Optional[str] = None
    delai_paie: Optional[str] = None
    devise: Optional[str] = None
    obj_fact: Optional[str] = None
    cpt_comptable: Optional[str] = None
    date_facture_gl: Optional[date] = None
    date_gl: Optional[date] = None
    periode_de_facturation: Optional[str] = None
    reference: Optional[str] = None
    termine_flag: Optional[bool] = None
    tax_amount: Optional[float] = None
    creer_par: Optional[str] = None
    n_ligne: Optional[str] = None
    description_ligne_de_produit: Optional[str] = None
    uom: Optional[str] = None
    qte: Optional[float] = None
    prix_uni: Optional[float] = None
    taux_change: Optional[float] = None
    mnt_ht: Optional[float] = None
    tax: Optional[str] = None
    mnt_tax: Optional[float] = None
    mnt_ttc: Optional[float] = None
    memo_line_id: Optional[str] = None
    chiffre_aff_exe_dzd: Optional[float] = None
    tva: Optional[float] = None
    chiffre_aff_exe_dzd_ttc: Optional[float] = None
    taux_realisation_ca: Optional[float] = None
    account_description_id: Optional[int] = None
    revenue_objective_id: Optional[int] = None
    is_anomaly: Optional[bool] = None
    anomaly_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccountDescriptionResponse(BaseModel):
    id: int
    file_upload_id: Optional[int] = None
    cpt_comptable: str
    description_cpt_comptable: Optional[str] = None
    aut_bdg: Optional[str] = None
    aut_imp: Optional[str] = None
    type_cpte: Optional[str] = None
    auxil: Optional[str] = None
    let: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RevenueObjectiveResponse(BaseModel):
    id: int
    file_upload_id: Optional[int] = None
    dot_id: Optional[int] = None
    dot_name: str
    objectif_ca: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # Exclude the dot relationship to avoid serialization issues
        # We already have dot_id and dot_name which is sufficient


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


class PaginatedRevenueJournalResponse(BaseModel):
    data: List[RevenueJournalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


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


@router.post("/upload/dot-corporate", response_model=FileUploadResponse)
async def upload_dot_corporate(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload DOT Corporate revenue file with monthly data
    Requires: can_upload_files permission
    """
    PermissionService.require_permission(
        current_user, db, "can_upload_files")

    try:
        # Save file
        upload_dir = "uploads/revenue/dot_corporate"
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
            file_type="dot_corporate",
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
        result = processor.process_dot_corporate(
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
            message="DOT Corporate file processed successfully" if result.get(
                "success") else f"Error: {result.get('error')}",
            file_id=file_upload.id,
            processed_rows=result.get("processed_rows", 0)
        )

    except Exception as e:
        logger.error(f"Error uploading DOT Corporate file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account-descriptions", response_model=List[AccountDescriptionResponse])
async def list_account_descriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cpt_comptable: Optional[str] = Query(None, description="Filter by account code"),
    file_upload_id: Optional[int] = Query(None, description="Filter by file upload ID"),
    type_cpte: Optional[str] = Query(None, description="Filter by account type")
):
    """
    List all account descriptions
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        query = db.query(AccountDescription)

        # Apply filters
        if cpt_comptable:
            query = query.filter(AccountDescription.cpt_comptable.ilike(f"%{cpt_comptable}%"))
        
        if file_upload_id:
            query = query.filter(AccountDescription.file_upload_id == file_upload_id)
        
        if type_cpte:
            query = query.filter(AccountDescription.type_cpte.ilike(f"%{type_cpte}%"))

        accounts = query.order_by(AccountDescription.cpt_comptable.asc()).all()

        # Convert to response models, explicitly constructing to avoid
        # Pydantic serialization issues with SQLAlchemy relationship objects
        result = []
        for acc in accounts:
            response = AccountDescriptionResponse(
                id=acc.id,
                file_upload_id=acc.file_upload_id,
                cpt_comptable=acc.cpt_comptable,
                description_cpt_comptable=acc.description_cpt_comptable,
                aut_bdg=acc.aut_bdg,
                aut_imp=acc.aut_imp,
                type_cpte=acc.type_cpte,
                auxil=acc.auxil,
                let=acc.let,
                created_at=acc.created_at,
                updated_at=acc.updated_at,
            )
            result.append(response)
        
        return result

    except Exception as e:
        logger.error(f"Error listing account descriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account-descriptions/{account_id}", response_model=AccountDescriptionResponse)
async def get_account_description(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific account description by ID
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        account = db.query(AccountDescription).filter(
            AccountDescription.id == account_id).first()

        if not account:
            raise HTTPException(status_code=404, detail="Account description not found")

        # Convert to response model, explicitly constructing to avoid
        # Pydantic serialization issues with SQLAlchemy relationship objects
        return AccountDescriptionResponse(
            id=account.id,
            file_upload_id=account.file_upload_id,
            cpt_comptable=account.cpt_comptable,
            description_cpt_comptable=account.description_cpt_comptable,
            aut_bdg=account.aut_bdg,
            aut_imp=account.aut_imp,
            type_cpte=account.type_cpte,
            auxil=account.auxil,
            let=account.let,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account description: {e}")
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


@router.get("/objectives", response_model=List[RevenueObjectiveResponse])
async def list_revenue_objectives(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    dot_name: Optional[str] = Query(None, description="Filter by DOT name"),
    file_upload_id: Optional[int] = Query(None, description="Filter by file upload ID")
):
    """
    List all revenue objectives (now sourced from RevenueDOTCorporate with monthly details)
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        from models.revenue import RevenueDOTCorporate
        from datetime import datetime

        # Query from RevenueDOTCorporate (monthly objectives table)
        current_year = datetime.utcnow().year
        query = db.query(RevenueDOTCorporate).filter(
            RevenueDOTCorporate.year == current_year
        )

        # Apply filters
        if dot_name:
            query = query.filter(RevenueDOTCorporate.dot_name.ilike(f"%{dot_name}%"))

        if file_upload_id:
            query = query.filter(RevenueDOTCorporate.file_upload_id == file_upload_id)

        objectives = query.order_by(RevenueDOTCorporate.dot_name.asc()).all()

        # Convert to response models, using annual_objective for objectif_ca
        result = []
        for obj in objectives:
            response = RevenueObjectiveResponse(
                id=obj.id,
                file_upload_id=obj.file_upload_id,
                dot_id=obj.dot_id,
                dot_name=obj.dot_name,
                objectif_ca=float(obj.annual_objective),  # Calculate from monthly values
                created_at=obj.created_at,
                updated_at=obj.updated_at,
            )
            result.append(response)

        return result

    except Exception as e:
        logger.error(f"Error listing revenue objectives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/objectives/{objective_id}", response_model=RevenueObjectiveResponse)
async def get_revenue_objective(
    objective_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific revenue objective by ID (now sourced from RevenueDOTCorporate)
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        from models.revenue import RevenueDOTCorporate
        from datetime import datetime

        # Query from RevenueDOTCorporate (monthly objectives table)
        current_year = datetime.utcnow().year
        objective = db.query(RevenueDOTCorporate).filter(
            RevenueDOTCorporate.id == objective_id,
            RevenueDOTCorporate.year == current_year
        ).first()

        if not objective:
            raise HTTPException(status_code=404, detail="Revenue objective not found")

        # Convert to response model, using annual_objective for objectif_ca
        return RevenueObjectiveResponse(
            id=objective.id,
            file_upload_id=objective.file_upload_id,
            dot_id=objective.dot_id,
            dot_name=objective.dot_name,
            objectif_ca=float(objective.annual_objective),  # Calculate from monthly values
            created_at=objective.created_at,
            updated_at=objective.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting revenue objective: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal", response_model=PaginatedRevenueJournalResponse)
async def list_revenue_journals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    org_name: Optional[str] = Query(None, description="Filter by organization name"),
    file_upload_id: Optional[int] = Query(None, description="Filter by file upload ID"),
    n_fact: Optional[str] = Query(None, description="Filter by invoice number"),
    cpt_comptable: Optional[str] = Query(None, description="Filter by account code"),
    start_date: Optional[date] = Query(None, description="Filter by start date (Date GL)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (Date GL)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page")
):
    """
    List all revenue journal entries with pagination
    Requires: can_view_analytics permission
    """
    PermissionService.require_permission(
        current_user, db, "can_view_analytics")

    try:
        query = db.query(RevenueJournal)

        # Apply filters
        if org_name:
            query = query.filter(RevenueJournal.org_name.ilike(f"%{org_name}%"))
        
        if file_upload_id:
            query = query.filter(RevenueJournal.file_upload_id == file_upload_id)
        
        if n_fact:
            query = query.filter(RevenueJournal.n_fact.ilike(f"%{n_fact}%"))
        
        if cpt_comptable:
            query = query.filter(RevenueJournal.cpt_comptable.ilike(f"%{cpt_comptable}%"))
        
        if start_date:
            query = query.filter(RevenueJournal.date_gl >= start_date)
        
        if end_date:
            query = query.filter(RevenueJournal.date_gl <= end_date)

        # Get total count for pagination
        total = query.count()

        # Pagination
        offset = (page - 1) * page_size
        journals = query.order_by(RevenueJournal.date_gl.desc(), RevenueJournal.created_at.desc()).offset(offset).limit(page_size).all()

        # Convert to response models, explicitly constructing to avoid
        # Pydantic serialization issues with SQLAlchemy relationship objects
        result = []
        for journal in journals:
            response = RevenueJournalResponse(
                id=journal.id,
                file_upload_id=journal.file_upload_id,
                dot_id=journal.dot_id,
                org_name=journal.org_name,
                origine=journal.origine,
                n_fact=journal.n_fact,
                typ_fact=journal.typ_fact,
                date_fact=journal.date_fact,
                n_client=journal.n_client,
                client=journal.client,
                delai_paie=journal.delai_paie,
                devise=journal.devise,
                obj_fact=journal.obj_fact,
                cpt_comptable=journal.cpt_comptable,
                date_facture_gl=journal.date_facture_gl,
                date_gl=journal.date_gl,
                periode_de_facturation=journal.periode_de_facturation,
                reference=journal.reference,
                termine_flag=journal.termine_flag,
                tax_amount=float(journal.tax_amount) if journal.tax_amount else None,
                creer_par=journal.creer_par,
                n_ligne=journal.n_ligne,
                description_ligne_de_produit=journal.description_ligne_de_produit,
                uom=journal.uom,
                qte=float(journal.qte) if journal.qte else None,
                prix_uni=float(journal.prix_uni) if journal.prix_uni else None,
                taux_change=float(journal.taux_change) if journal.taux_change else None,
                mnt_ht=float(journal.mnt_ht) if journal.mnt_ht else None,
                tax=journal.tax,
                mnt_tax=float(journal.mnt_tax) if journal.mnt_tax else None,
                mnt_ttc=float(journal.mnt_ttc) if journal.mnt_ttc else None,
                memo_line_id=journal.memo_line_id,
                chiffre_aff_exe_dzd=float(journal.chiffre_aff_exe_dzd) if journal.chiffre_aff_exe_dzd else None,
                tva=float(journal.tva) if journal.tva else None,
                chiffre_aff_exe_dzd_ttc=float(journal.chiffre_aff_exe_dzd_ttc) if journal.chiffre_aff_exe_dzd_ttc else None,
                taux_realisation_ca=float(journal.taux_realisation_ca) if journal.taux_realisation_ca else None,
                account_description_id=journal.account_description_id,
                revenue_objective_id=journal.revenue_objective_id,
                is_anomaly=journal.is_anomaly,
                anomaly_reason=journal.anomaly_reason,
                created_at=journal.created_at,
                updated_at=journal.updated_at,
            )
            result.append(response)
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return PaginatedRevenueJournalResponse(
            data=result,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error listing revenue journals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


