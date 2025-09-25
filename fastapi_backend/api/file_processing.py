from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any

from database.connection import get_db
from core.security import get_current_user
from models.user import User
from models.file_upload import FileProcessingStatus
from services.file_service import FileService
from services.file_processing_service import FileProcessingService
from services.notification_service import NotificationService
import logging

logger = logging.getLogger('file_processing')

file_processing_router = APIRouter()
file_service = FileService()
processing_service = FileProcessingService()


@file_processing_router.post("/{file_id}/process")
async def process_file(
    file_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start file processing in background"""
    logger.info(
        f"🎯 File processing request received for file_id: {file_id} by user: {current_user.id}")

    try:
        file_upload = file_service.get_file_upload(
            db, file_id, current_user.id)
        logger.info(
            f"📁 Found file: {file_upload.original_filename} (ID: {file_id})")

        # Generate task_id for WebSocket subscription
        task_id = None

        # For supported file types, get the task_id from background processor
        if file_upload.file_type in ["csv", "excel"]:
            from services.background_processor import background_processor
            # Pre-generate task_id that will be used by the background processor
            import uuid
            task_id = str(uuid.uuid4())
            logger.info(f"🆔 Generated task_id: {task_id} for file {file_id}")

        # Add background task for processing
        background_tasks.add_task(
            process_file_background,
            file_id,
            current_user.id,
            task_id
        )

        logger.info(
            f"🚀 Background processing task added for file {file_id} by user {current_user.id}")

        response = {"message": "File processing started", "file_id": file_id}
        if task_id:
            response["task_id"] = task_id

        return response

    except Exception as e:
        logger.error(
            f"❌ Failed to start processing for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start file processing: {str(e)}"
        )


@file_processing_router.get("/{file_id}/status", response_model=FileProcessingStatus)
async def get_processing_status(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file processing status"""
    file_service.get_file_upload(db, file_id, current_user.id)  # Check access

    status = processing_service.get_processing_status(db, file_id)
    logger.info(
        f"Processing status for file {file_id} retrieved by user {current_user.id}")
    return status


@file_processing_router.post("/{file_id}/cancel-processing")
async def cancel_file_processing(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel file processing"""
    file_service.get_file_upload(db, file_id, current_user.id)  # Check access

    try:
        processing_service.cancel_processing(db, file_id)
        logger.info(
            f"Processing cancelled for file {file_id} by user {current_user.id}")
        return {"message": "Processing cancelled successfully"}

    except Exception as e:
        logger.error(f"Failed to cancel processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling processing: {str(e)}"
        )


@file_processing_router.get("/{file_id}/results")
async def get_processing_results(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get file processing results"""
    file_service.get_file_upload(db, file_id, current_user.id)  # Check access

    try:
        results = processing_service.get_processing_results(db, file_id)
        logger.info(
            f"Processing results for file {file_id} retrieved by user {current_user.id}")
        return results

    except Exception as e:
        logger.error(f"Failed to get processing results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving processing results: {str(e)}"
        )


async def process_file_background(file_id: int, user_id: int, task_id: str = None):
    """Background task for file processing"""
    from database.connection import SessionLocal

    logger.info(
        f"🔄 Starting background processing for file_id: {file_id}, user_id: {user_id}")

    db = SessionLocal()
    notification_service = NotificationService()

    try:
        # Start processing
        logger.info(f"⚙️ Calling processing service for file_id: {file_id} with task_id: {task_id}")
        result = await processing_service.process_file(db, file_id, task_id)
        logger.info(f"✅ Processing service completed for file_id: {file_id}")

        # Send success notification
        logger.info(f"📢 Sending success notification for file_id: {file_id}")
        await notification_service.notify_file_processing_completed(
            db,
            user_id=user_id,
            filename=f"File {file_id}",
            results=result
        )
        logger.info(f"📢 Success notification sent for file_id: {file_id}")

        logger.info(
            f"🎉 Background processing completed successfully for file {file_id}")

    except Exception as e:
        logger.error(
            f"💥 Background processing failed for file {file_id}: {str(e)}")
        logger.error(f"💥 Error type: {type(e)}")
        logger.error(f"💥 Error details: {str(e)}")

        # Send error notification
        logger.info(f"📢 Sending error notification for file_id: {file_id}")
        await notification_service.notify_file_processing_failed(
            db,
            user_id=user_id,
            filename=f"File {file_id}",
            error=str(e)
        )
        logger.info(f"📢 Error notification sent for file_id: {file_id}")

    finally:
        db.close()
        logger.info(f"🔒 Database connection closed for file_id: {file_id}")
