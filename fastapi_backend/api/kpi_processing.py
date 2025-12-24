"""
Unified KPI File Processing API
Automatically detects and routes files to appropriate processors based on detected KPI type
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.file_upload import FileUpload
from services.file_service import FileService
from services.file_detector_service import KPIFileType, file_detector_service
from services.notification_service import NotificationService

logger = logging.getLogger('kpi_processing')

kpi_processing_router = APIRouter()
file_service = FileService()


@kpi_processing_router.post("/{file_id}/process-kpi")
async def process_kpi_file(
    file_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a KPI file with automatic type detection and routing

    This endpoint:
    1. Retrieves the uploaded file
    2. Uses the detected KPI type (or detects if not already done)
    3. Routes to the appropriate ETL processor
    4. Returns processing task information
    """
    logger.info(
        f"🎯 KPI processing request received for file_id: {file_id} by user: {current_user.id}")

    try:
        # Get file upload record
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)
        logger.info(
            f"📁 Found file: {file_upload.original_filename} (ID: {file_id})")

        # Check if KPI type was detected during upload
        detected_type = file_upload.detected_kpi_type
        confidence = file_upload.detection_confidence or 0

        # If not detected, detect now
        if not detected_type or detected_type == 'unknown':
            logger.info(
                f"🔍 KPI type not detected during upload, detecting now...")
            kpi_type, detection_info = file_detector_service.detect_file_type(
                file_upload.file_path)
            detected_type = detection_info.get('detected_type')
            confidence = detection_info.get('confidence', 0)

            # Update file record with detection results
            file_upload.detected_kpi_type = detected_type
            file_upload.detection_confidence = int(confidence)
            db.commit()
            db.refresh(file_upload)

            logger.info(
                f"✅ Detected KPI type: {detected_type} ({confidence}% confidence)")

        # Check if we have a valid KPI type
        if detected_type == 'unknown' or confidence < 40:
            logger.warning(
                f"⚠️ Unable to determine KPI type with sufficient confidence ({confidence}%)")
            raise HTTPException(
                status_code=400,
                detail=f"Unable to determine KPI file type. Confidence: {confidence}%. "
                f"Please ensure the file has the correct structure and headers."
            )

        # Get processor information
        try:
            kpi_type_enum = KPIFileType(detected_type)
        except ValueError:
            logger.error(f"❌ Invalid KPI type: {detected_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid KPI type: {detected_type}"
            )

        processor_name = file_detector_service.get_processor_for_type(
            kpi_type_enum)

        if not processor_name:
            logger.warning(
                f"⚠️ No processor available for KPI type: {detected_type}")
            raise HTTPException(
                status_code=501,
                detail=f"Processing for {detected_type} files is not yet implemented. "
                f"Detected type: {kpi_type_enum.value}"
            )

        # Add background task for processing
        import uuid
        task_id = str(uuid.uuid4())

        background_tasks.add_task(
            process_kpi_file_background,
            file_id,
            current_user.id,
            detected_type,
            processor_name,
            task_id
        )

        logger.info(
            f"🚀 Background KPI processing task added for file {file_id}")
        logger.info(f"   KPI Type: {detected_type}")
        logger.info(f"   Processor: {processor_name}")
        logger.info(f"   Task ID: {task_id}")

        return {
            "message": f"KPI file processing started",
            "file_id": file_id,
            "task_id": task_id,
            "kpi_type": detected_type,
            "processor": processor_name,
            "confidence": confidence
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"❌ Failed to start KPI processing for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start KPI file processing: {str(e)}"
        )


@kpi_processing_router.get("/{file_id}/kpi-info")
async def get_kpi_file_info(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI detection information for a file

    Returns:
        - detected_kpi_type: The detected KPI type
        - confidence: Detection confidence (0-100)
        - processor: Processor that will be used
        - requirements: Processing requirements
        - file_info: Basic file information
    """
    try:
        # Get file upload record
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)

        detected_type = file_upload.detected_kpi_type
        confidence = file_upload.detection_confidence or 0

        # If not detected yet, detect now
        if not detected_type:
            kpi_type, detection_info = file_detector_service.detect_file_type(
                file_upload.file_path)
            detected_type = detection_info.get('detected_type')
            confidence = detection_info.get('confidence', 0)

        # Get processor and requirements info
        processor_name = None
        requirements = None

        try:
            kpi_type_enum = KPIFileType(detected_type)
            processor_name = file_detector_service.get_processor_for_type(
                kpi_type_enum)
            requirements = file_detector_service.get_processing_requirements(
                kpi_type_enum)
        except ValueError:
            pass

        return {
            "file_id": file_id,
            "filename": file_upload.original_filename,
            "detected_kpi_type": detected_type,
            "confidence": confidence,
            "processor": processor_name,
            "requirements": requirements,
            "is_processable": processor_name is not None and confidence >= 40,
            "file_info": {
                "file_type": file_upload.file_type,
                "file_size": file_upload.file_size,
                "uploaded_at": file_upload.created_at.isoformat() if file_upload.created_at else None,
                "processing_status": file_upload.processing_status
            }
        }

    except Exception as e:
        logger.error(f"❌ Failed to get KPI info for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get KPI file information: {str(e)}"
        )


@kpi_processing_router.post("/batch-process")
async def batch_process_kpi_files(
    file_ids: list[int],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process multiple KPI files in batch

    Useful for processing related files together (e.g., Encaissement current year + N-1)
    """
    logger.info(
        f"📦 Batch KPI processing request for {len(file_ids)} files by user: {current_user.id}")

    results = []
    errors = []

    for file_id in file_ids:
        try:
            file_upload = file_service.get_file_upload(
                db, file_id, current_user.id)

            detected_type = file_upload.detected_kpi_type
            if not detected_type or detected_type == 'unknown':
                kpi_type, detection_info = file_detector_service.detect_file_type(
                    file_upload.file_path)
                detected_type = detection_info.get('detected_type')
                confidence = detection_info.get('confidence', 0)

                file_upload.detected_kpi_type = detected_type
                file_upload.detection_confidence = int(confidence)
                db.commit()

            results.append({
                "file_id": file_id,
                "filename": file_upload.original_filename,
                "kpi_type": detected_type,
                "status": "queued"
            })

        except Exception as e:
            logger.error(f"❌ Error processing file {file_id}: {str(e)}")
            errors.append({
                "file_id": file_id,
                "error": str(e)
            })

    # Group files by KPI type for efficient batch processing
    files_by_type = {}
    for result in results:
        kpi_type = result["kpi_type"]
        if kpi_type not in files_by_type:
            files_by_type[kpi_type] = []
        files_by_type[kpi_type].append(result["file_id"])

    # Add batch processing tasks
    task_ids = []
    for kpi_type, file_ids_group in files_by_type.items():
        task_id = f"batch_{kpi_type}_{len(task_ids)}"
        # TODO: Implement batch processing logic
        task_ids.append(task_id)

    return {
        "message": f"Batch processing started for {len(results)} files",
        "successful": results,
        "failed": errors,
        "grouped_by_type": files_by_type,
        "task_ids": task_ids
    }


async def process_kpi_file_background(
    file_id: int,
    user_id: int,
    kpi_type: str,
    processor_name: str,
    task_id: str = None
):
    """Background task for KPI file processing"""
    from database.connection import SessionLocal

    logger.info(f"🔄 Starting background KPI processing for file_id: {file_id}")
    logger.info(f"   KPI Type: {kpi_type}")
    logger.info(f"   Processor: {processor_name}")

    db = SessionLocal()
    notification_service = NotificationService()

    try:
        # Get file record
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()
        if not file_upload:
            raise ValueError(f"File {file_id} not found")

        # Update status
        file_upload.processing_status = "processing"
        db.commit()

        # Route to appropriate processor
        result = await route_to_processor(
            kpi_type=kpi_type,
            processor_name=processor_name,
            file_path=Path(file_upload.file_path),
            task_id=task_id
        )

        # Update status based on result
        if result.get('success'):
            file_upload.processing_status = "completed"
            file_upload.is_processed = True
        else:
            file_upload.processing_status = "failed"
            file_upload.error_message = result.get('error', 'Unknown error')

        db.commit()

        # Send notification
        await notification_service.notify_file_processing_completed(
            db,
            user_id=user_id,
            filename=file_upload.original_filename,
            results=result
        )

        logger.info(
            f"✅ Background KPI processing completed for file {file_id}")

    except Exception as e:
        logger.error(
            f"💥 Background KPI processing failed for file {file_id}: {str(e)}")

        # Update status
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()
        if file_upload:
            file_upload.processing_status = "failed"
            file_upload.error_message = str(e)
            db.commit()

        # Send error notification
        await notification_service.notify_file_processing_failed(
            db,
            user_id=user_id,
            filename=f"File {file_id}",
            error_message=str(e)
        )

    finally:
        db.close()


async def route_to_processor(
    kpi_type: str,
    processor_name: str,
    file_path: Path,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Route file to appropriate ETL processor based on KPI type

    Args:
        kpi_type: The detected KPI type
        processor_name: Name of the processor class
        file_path: Path to the file to process
        task_id: Optional task ID for tracking

    Returns:
        Processing result dictionary
    """
    logger.info(
        f"🔀 Routing to processor: {processor_name} for KPI type: {kpi_type}")

    try:
        # Import appropriate processor
        if processor_name == 'ParcCorporateNGBSSETL':
            from services.etl.parc_corporate_ngbss_etl import ParcCorporateNGBSSETL
            processor = ParcCorporateNGBSSETL()

        elif processor_name == 'EncaissementETL':
            from services.etl.encaissement_etl import EncaissementETL
            processor = EncaissementETL()

        elif processor_name == 'EncaissementARDotETL':
            from services.etl.encaissement_ar_dot_etl import EncaissementARDotETL
            processor = EncaissementARDotETL()

        elif processor_name == 'CreancePeriodiqueDotETL':
            from services.etl.creance_periodique_dot_etl import CreancePeriodiqueDotETL
            processor = CreancePeriodiqueDotETL()

        elif processor_name == 'SubscriberParkETL':
            from services.etl.subscriber_park_etl import SubscriberParkETL
            processor = SubscriberParkETL()

        else:
            return {
                'success': False,
                'error': f"Processor {processor_name} not implemented",
                'kpi_type': kpi_type
            }

        # Run ETL processing
        logger.info(f"⚙️ Starting ETL processing with {processor_name}")
        etl_result = processor.run_etl([file_path])

        # Convert ETL result to dictionary
        result = {
            'success': etl_result.success,
            'kpi_type': kpi_type,
            'processor': processor_name,
            'input_records': etl_result.input_records_count,
            'output_records': etl_result.output_records_count,
            'anomaly_records': etl_result.anomaly_records_count,
            'processing_time': etl_result.processing_time_seconds,
            'output_files': [str(f) for f in etl_result.output_files],
            'anomaly_files': [str(f) for f in etl_result.anomaly_files],
            'errors': etl_result.errors,
            'summary': etl_result.to_summary()
        }

        logger.info(f"✅ ETL processing completed: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ Error routing to processor: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'kpi_type': kpi_type,
            'processor': processor_name
        }
