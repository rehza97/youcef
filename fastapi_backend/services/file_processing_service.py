from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from services.notification_service import NotificationService
from services.dot_service import DOTService

logger = logging.getLogger(__name__)


class FileProcessingService:
    """Encapsulates file upload notifications and background processing.

    Routers should delegate to this service to keep endpoints thin.
    """

    @staticmethod
    async def _send_progress_update(file_id: int, update_data: dict, total_rows: int):
        """Send progress update via WebSocket"""
        try:
            from services.processing_websocket import processing_ws_manager
            await processing_ws_manager.send_task_update(
                str(file_id),
                {
                    "status": update_data["status"],
                    "progress": update_data["progress"],
                    "message": update_data["message"],
                    "statistics": {
                        "total_rows": total_rows,
                        "processed_rows": update_data.get("saved_count", 0),
                        "errors": update_data.get("errors_count", 0)
                    }
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to send progress update: {e}")

    async def notify_upload_started(self, user_id: int, filename: str, file_id: int) -> None:
        try:
            await NotificationService.notify_file_uploaded(
                user_id=user_id,
                filename=filename,
                file_id=file_id,
            )
        except Exception:
            # Intentionally swallow to avoid failing request on notification errors
            pass

    async def notify_processing_started(self, user_id: int, filename: str, file_id: int) -> None:
        try:
            await NotificationService.notify_file_processing_started(
                user_id=user_id,
                filename=filename,
                file_id=file_id,
            )
        except Exception:
            pass

    async def notify_processing_progress(self, db: Session, user_id: int, filename: str, progress: int) -> None:
        try:
            await NotificationService.notify_file_processing_progress(
                db=db,
                user_id=user_id,
                filename=filename,
                progress=progress,
            )
        except Exception:
            pass

    async def notify_processing_completed(self, db: Session, user_id: int, filename: str, results: Dict[str, Any]) -> None:
        try:
            await NotificationService.notify_file_processing_completed(
                db=db,
                user_id=user_id,
                filename=filename,
                results=results,
            )
        except Exception:
            pass

    async def process_file(self, db: Session, file_id: int, task_id: str = None) -> Dict[str, Any]:
        """Process a file and return results"""
        import logging
        import pandas as pd
        import os
        logger = logging.getLogger('file_processing')

        try:
            logger.info(f"🚀 Starting file processing for file_id: {file_id}")

            # Get file upload record
            from models.file_upload import FileUpload
            file_upload = db.query(FileUpload).filter(
                FileUpload.id == file_id).first()

            if not file_upload:
                logger.error(f"❌ File with ID {file_id} not found")
                raise ValueError(f"File with ID {file_id} not found")

            logger.info(
                f"📁 Processing file: {file_upload.original_filename} (Size: {file_upload.file_size} bytes)")

            # Check if file exists
            if not os.path.exists(file_upload.file_path):
                logger.error(
                    f"❌ File not found at path: {file_upload.file_path}")
                raise ValueError(
                    f"File not found at path: {file_upload.file_path}")

            # Update processing status
            file_upload.processing_status = "processing"
            db.commit()
            logger.info(
                f"📊 Updated file status to 'processing' for file_id: {file_id}")

            # Count total rows in the file
            total_rows = 0
            try:
                if file_upload.file_type == "csv":
                    # For CSV files, count rows efficiently
                    with open(file_upload.file_path, 'r', encoding='utf-8') as f:
                        total_rows = sum(1 for line in f) - \
                            1  # Subtract header
                elif file_upload.file_type == "excel":
                    # For Excel files, read and count rows
                    df = pd.read_excel(file_upload.file_path)
                    total_rows = len(df)
                else:
                    logger.warning(
                        f"⚠️ Unsupported file type: {file_upload.file_type}")
                    total_rows = 0
            except Exception as e:
                logger.error(f"❌ Error counting rows: {str(e)}")
                total_rows = 0

            logger.info(f"📊 File contains {total_rows} rows")

            # Process file with actual processing logic
            processed_rows = 0
            errors = 0
            anomalies = []
            statistics = {}
            # Use provided task_id or default to file_id
            if task_id is None:
                task_id = str(file_id)

            try:
                # Use BackgroundProcessor for actual processing if it's a supported file type
                if file_upload.file_type in ["csv", "excel"]:
                    from services.background_processor import background_processor

                    logger.info(
                        "🔧 Using BackgroundProcessor for real file processing with row limits")

                    # Start background processing with predefined task_id
                    actual_task_id = background_processor.start_processing(
                        file_upload.file_path,
                        str(file_id),
                        file_upload.uploaded_by,
                        task_id  # Pass our predefined task_id
                    )

                    logger.info(
                        f"🚀 Started background processing task: {actual_task_id} (requested: {task_id})")

                    # Wait for processing to complete and monitor progress
                    while True:
                        task_status = background_processor.get_task_status(
                            actual_task_id)
                        if not task_status:
                            logger.error("❌ Task status not found")
                            break

                        status = task_status.get("status", "unknown")
                        progress = task_status.get("progress", 0)
                        processed_rows = task_status.get("processed_rows", 0)
                        saved_rows = task_status.get("saved_rows", 0)
                        errors = len(task_status.get("errors", []))

                        # Send progress update using the frontend task_id (for subscription)
                        await self._send_progress_update(task_id, {
                            "status": status,
                            "progress": progress,
                            "message": f"Processing... {processed_rows} rows processed, {saved_rows} saved",
                            "saved_count": saved_rows,
                            "errors_count": errors
                        }, total_rows)

                        if status in ["completed", "failed", "cancelled"]:
                            logger.info(
                                f"🏁 Processing finished with status: {status}")
                            break

                        # Wait a bit before checking again (reduced for better responsiveness)
                        await asyncio.sleep(0.5)

                    # Get final results
                    final_status = background_processor.get_task_status(
                        actual_task_id)
                    if final_status:
                        processed_rows = final_status.get("saved_rows", 0)
                        errors = len(final_status.get("errors", []))
                        anomalies = final_status.get("anomalies", [])
                        statistics = final_status.get("statistics", {})

                        if final_status.get("status") == "completed":
                            logger.info(
                                f"✅ Processing completed successfully: {processed_rows} rows saved")
                        else:
                            logger.error(
                                f"❌ Processing failed: {final_status.get('errors', [])}")
                            raise Exception(
                                f"Processing failed: {final_status.get('errors', [])}")
                    else:
                        raise Exception(
                            "Could not retrieve final processing status")
                else:
                    # For unsupported file types, just simulate processing
                    logger.info(
                        "⚠️ File type not supported for processing, simulating...")
                    total_steps = 5
                    for step in range(total_steps):
                        progress = int((step + 1) / total_steps * 100)
                        processed_rows = int(total_rows * progress / 100)

                        try:
                            from services.processing_websocket import processing_ws_manager
                            await processing_ws_manager.send_task_update(
                                str(file_id),
                                {
                                    "status": "processing",
                                    "progress": progress,
                                    "message": f"Simulating processing... {progress}%",
                                    "statistics": {
                                        "total_rows": total_rows,
                                        "processed_rows": processed_rows,
                                        "errors": 0
                                    }
                                }
                            )
                        except Exception as ws_error:
                            logger.warning(
                                f"⚠️ Failed to send WebSocket update: {ws_error}")

                        await asyncio.sleep(0.3)

                    processed_rows = total_rows

            except Exception as processing_error:
                logger.error(
                    f"❌ Error during file processing: {str(processing_error)}")
                errors = 1
                processed_rows = 0

            # Update processing status to completed
            file_upload.processing_status = "completed"
            db.commit()
            logger.info(
                f"✅ File processing completed successfully for file_id: {file_id}")

            # Send completion WebSocket update
            try:
                from services.processing_websocket import processing_ws_manager
                await processing_ws_manager.send_task_update(
                    task_id,
                    {
                        "status": "completed",
                        "progress": 100,
                        "message": "File processing completed successfully",
                        "statistics": {
                            "total_rows": total_rows,
                            "processed_rows": processed_rows,
                            "errors": errors,
                            **statistics  # Include additional statistics from processing
                        },
                        # Show first 10 anomalies
                        "anomalies": anomalies[:10] if anomalies else []
                    }
                )
                logger.info(
                    f"📡 Sent completion WebSocket update for file_id: {file_id}")
            except Exception as ws_error:
                logger.warning(
                    f"⚠️ Failed to send completion WebSocket update: {ws_error}")

            # Return processing results
            result = {
                "file_id": file_id,
                "status": "completed",
                "message": "File processed successfully",
                "total_rows": total_rows,
                "processed_rows": processed_rows,
                "errors": errors,
                "anomalies": anomalies,
                "statistics": statistics
            }
            logger.info(f"📋 Processing results: {result}")
            return result

        except Exception as e:
            logger.error(
                f"❌ File processing failed for file_id: {file_id}: {str(e)}")
            # Update processing status to failed
            if 'file_upload' in locals() and file_upload:
                file_upload.processing_status = "failed"
                file_upload.error_message = str(e)
                db.commit()
                logger.error(
                    f"📝 Updated file status to 'failed' for file_id: {file_id}")
            raise e

    def get_processing_status(self, db: Session, file_id: int) -> Dict[str, Any]:
        """Get processing status for a file"""
        from models.file_upload import FileUpload

        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()
        if not file_upload:
            raise ValueError(f"File with ID {file_id} not found")

        return {
            "file_id": file_id,
            "status": file_upload.processing_status or "pending",
            "progress": None,
            "message": None,
            "error": file_upload.error_message
        }

    def get_processing_results(self, db: Session, file_id: int) -> Dict[str, Any]:
        """Get processing results for a file"""
        from models.file_upload import FileUpload
        import pandas as pd
        import os

        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()
        if not file_upload:
            raise ValueError(f"File with ID {file_id} not found")

        # Count actual rows in the file
        total_rows = 0
        try:
            if os.path.exists(file_upload.file_path):
                if file_upload.file_type == "csv":
                    # For CSV files, count rows efficiently
                    with open(file_upload.file_path, 'r', encoding='utf-8') as f:
                        total_rows = sum(1 for line in f) - \
                            1  # Subtract header
                elif file_upload.file_type == "excel":
                    # For Excel files, read and count rows
                    df = pd.read_excel(file_upload.file_path)
                    total_rows = len(df)
        except Exception as e:
            # If we can't count rows, use 0
            total_rows = 0

        return {
            "file_id": file_id,
            "status": file_upload.processing_status or "pending",
            "results": {
                "total_rows": total_rows,
                "processed_rows": total_rows if file_upload.processing_status == "completed" else 0,
                "errors": 0
            },
            "error": file_upload.error_message
        }

    def cancel_processing(self, db: Session, file_id: int) -> None:
        """Cancel processing for a file"""
        from models.file_upload import FileUpload
        from services.background_processor import background_processor

        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()
        if not file_upload:
            raise ValueError(f"File with ID {file_id} not found")

        # Try to cancel the background processor task
        # Look for active tasks that match this file_id
        active_tasks = background_processor.get_all_tasks()
        for task_id, task_info in active_tasks.items():
            if task_info.get("file_id") == str(file_id):
                logger.info(
                    f"Cancelling background processor task {task_id} for file {file_id}")
                background_processor.cancel_task(task_id)
                break

        # Update database status
        file_upload.processing_status = "cancelled"
        db.commit()

        logger.info(f"Processing cancelled for file {file_id}")

    def run_background_processing(self, db_factory, filename: str, user_id: int) -> None:
        async def _runner():
            # Simulate staged progress callbacks as before
            for progress in [25, 50, 75, 100]:
                await asyncio.sleep(1)
                db_session = db_factory()
                try:
                    await self.notify_processing_progress(
                        db=db_session, user_id=user_id, filename=filename, progress=progress
                    )
                finally:
                    db_session.close()

            db_session = db_factory()
            try:
                await self.notify_processing_completed(
                    db=db_session,
                    user_id=user_id,
                    filename=filename,
                    results={"total_rows": 100,
                             "processed_rows": 100, "errors": 0},
                )
            finally:
                db_session.close()

        asyncio.create_task(_runner())
