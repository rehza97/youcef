"""
High-Performance Background Processing System for Park Data
Handles large Excel files with multi-threading and bulk operations
"""

import asyncio
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List, Any, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
import os
import tempfile
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from database.connection import SessionLocal, engine
from models.park import Park
from models.dot import DOT
from services.park_processing import ParkDataProcessor
import uuid

logger = logging.getLogger(__name__)


class ProcessingStatus:
    """Track processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundProcessor:
    """High-performance background processor for large datasets"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(
            max_workers=min(4, os.cpu_count() or 1))
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.batch_size = 10000  # Process in batches of 10k rows
        self.chunk_size = 2500  # Read file in chunks of 2.5k rows for better progress updates
        self.max_rows_limit = 10000  # Limit processing to 10k rows for testing
        self._shutdown_event = threading.Event()

        # Create high-performance database engine for bulk operations
        self.bulk_engine = create_engine(
            engine.url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            echo=False
        )

        logger.info(
            f"Background processor initialized with {self.max_workers} workers")

    def start_processing(self, file_path: str, file_id: str, user_id: int, task_id: str = None) -> str:
        """Start background processing of a file"""
        if task_id is None:
            task_id = str(uuid.uuid4())
        else:
            logger.info(f"🆔 Using provided task_id: {task_id}")

        # Initialize task status
        self.active_tasks[task_id] = {
            "task_id": task_id,
            "file_id": file_id,
            "file_path": file_path,
            "user_id": user_id,
            "status": ProcessingStatus.PENDING,
            "progress": 0,
            "total_rows": 0,
            "processed_rows": 0,
            "filtered_rows": 0,
            "saved_rows": 0,
            "errors": [],
            "anomalies": [],
            "start_time": datetime.utcnow(),
            "end_time": None,
            "statistics": {},
            "cancelled": False
        }

        # Start background processing
        future = self.thread_pool.submit(self._process_file_async, task_id)

        logger.info(
            f"Started background processing task {task_id} for file {file_id}")
        return task_id

    def _process_file_async(self, task_id: str):
        """Process file asynchronously with progress tracking"""
        try:
            task = self.active_tasks[task_id]
            task["status"] = ProcessingStatus.PROCESSING

            # Get file info
            file_path = task["file_path"]

            # Count total rows first
            logger.info(f"Counting rows in file {file_path}")
            total_rows = self._count_file_rows(file_path)
            task["total_rows"] = total_rows

            logger.info(
                f"File has {total_rows} rows, processing in chunks of {self.chunk_size}")

            # Process file in chunks
            processed_rows = 0
            filtered_rows = 0
            saved_rows = 0
            all_anomalies = []
            all_statistics = {}

            # Create DOTs first
            self._create_dots()

            # Send initial WebSocket update
            self._send_websocket_update(task_id, {
                "status": "processing",
                "progress": 0,
                "message": "Starting processing...",
                "saved_count": 0,
                "errors_count": 0,
                "statistics": {
                    "total_rows": total_rows,
                    "processed_rows": 0,
                    "errors": 0
                }
            })

            # Process file in chunks, limited to max_rows_limit for testing
            chunk_num = 0
            total_processed = 0
            for chunk_df in pd.read_csv(file_path, chunksize=self.chunk_size):
                if task["cancelled"] or self._shutdown_event.is_set():
                    task["status"] = ProcessingStatus.CANCELLED
                    return

                # Limit processing to max_rows_limit for testing
                if total_processed >= self.max_rows_limit:
                    logger.info(
                        f"Reached max rows limit ({self.max_rows_limit}) for testing")
                    break

                # Limit chunk size to remaining rows
                remaining_rows = self.max_rows_limit - total_processed
                if len(chunk_df) > remaining_rows:
                    chunk_df = chunk_df.head(remaining_rows)
                    logger.info(
                        f"Limiting chunk to {remaining_rows} rows for testing")

                chunk_num += 1
                logger.info(
                    f"Processing chunk {chunk_num} with {len(chunk_df)} rows (Total processed: {total_processed})")

                # Process chunk
                chunk_result = self._process_chunk(chunk_df, task_id)

                if chunk_result["success"]:
                    processed_rows += chunk_result["processed_rows"]
                    filtered_rows += chunk_result["filtered_rows"]
                    saved_rows += chunk_result["saved_rows"]
                    # Update total processed count
                    total_processed += len(chunk_df)
                    all_anomalies.extend(chunk_result["anomalies"])

                    # Merge statistics
                    for key, value in chunk_result["statistics"].items():
                        if key in all_statistics:
                            if isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                    all_statistics[key][sub_key] = all_statistics[key].get(
                                        sub_key, 0) + sub_value
                            else:
                                all_statistics[key] += value
                        else:
                            all_statistics[key] = value

                    # Update progress
                    progress = min(
                        100, (total_processed / min(total_rows, self.max_rows_limit)) * 100)
                    task["progress"] = progress
                    task["processed_rows"] = processed_rows
                    task["filtered_rows"] = filtered_rows
                    task["saved_rows"] = saved_rows
                    task["anomalies"] = all_anomalies
                    task["statistics"] = all_statistics

                    logger.info(
                        f"Chunk {chunk_num} completed. Progress: {progress:.1f}% (Total processed: {total_processed})")

                    # Send real-time WebSocket update
                    self._send_websocket_update(task_id, {
                        "status": "processing",
                        "progress": progress,
                        "message": f"Processing... {processed_rows} rows processed, {saved_rows} saved",
                        "saved_count": saved_rows,
                        "errors_count": len(task.get("errors", [])),
                        "statistics": {
                            "total_rows": total_rows,
                            "processed_rows": processed_rows,
                            "errors": len(task.get("errors", []))
                        }
                    })
                else:
                    task["errors"].append(
                        f"Chunk {chunk_num} failed: {chunk_result['error']}")
                    logger.error(
                        f"Chunk {chunk_num} processing failed: {chunk_result['error']}")

            # Mark as completed
            task["status"] = ProcessingStatus.COMPLETED
            task["end_time"] = datetime.utcnow()
            task["progress"] = 100

            # Send final WebSocket update
            self._send_websocket_update(task_id, {
                "status": "completed",
                "progress": 100,
                "message": "Processing completed successfully",
                "saved_count": saved_rows,
                "errors_count": len(task.get("errors", [])),
                "statistics": {
                    "total_rows": total_rows,
                    "processed_rows": processed_rows,
                    "errors": len(task.get("errors", [])),
                    "total_records": saved_rows,
                    "by_dot": all_statistics.get("by_dot", {}),
                    "by_telecom_type": all_statistics.get("by_telecom_type", {}),
                    "by_customer_l2": all_statistics.get("by_customer_l2", {}),
                    "by_customer_l3": all_statistics.get("by_customer_l3", {}),
                    "by_subscriber_status": all_statistics.get("by_subscriber_status", {}),
                    "by_offer_type": all_statistics.get("by_offer_type", {})
                },
                "anomalies": all_anomalies
            })

            logger.info(f"Processing completed for task {task_id}. "
                        f"Processed: {processed_rows}, Filtered: {filtered_rows}, Saved: {saved_rows}")

        except Exception as e:
            logger.error(f"Processing failed for task {task_id}: {e}")
            task["status"] = ProcessingStatus.FAILED
            task["errors"].append(str(e))
            task["end_time"] = datetime.utcnow()

    def _count_file_rows(self, file_path: str) -> int:
        """Count total rows in file efficiently, limited to max_rows_limit for testing"""
        try:
            # Use pandas to count rows efficiently, but limit to max_rows_limit for testing
            chunk_iter = pd.read_csv(file_path, chunksize=10000)
            total_rows = 0
            for chunk in chunk_iter:
                total_rows += len(chunk)
                if total_rows >= self.max_rows_limit:
                    logger.info(
                        f"Limiting row count to {self.max_rows_limit} for testing")
                    return self.max_rows_limit
            return total_rows
        except Exception as e:
            logger.error(f"Error counting rows: {e}")
            return 0

    def _process_chunk(self, chunk_df: pd.DataFrame, task_id: str) -> Dict[str, Any]:
        """Process a chunk of data"""
        try:
            # Get file_upload_id from task
            task = self.active_tasks.get(task_id, {})
            file_upload_id = int(task.get("file_id")) if task.get(
                "file_id") else None

            # Apply processing rules
            processor = ParkDataProcessor(SessionLocal())
            processed_df = processor._apply_processing_rules(chunk_df)

            # Get statistics
            stats = processor._generate_statistics(processed_df)

            # Save to database in bulk
            saved_count = self._bulk_save_parks(
                processed_df.to_dict('records'), file_upload_id)

            return {
                "success": True,
                "processed_rows": len(processed_df),
                "filtered_rows": len(chunk_df) - len(processed_df),
                "saved_rows": saved_count,
                "anomalies": processor.anomalies,
                "statistics": stats
            }

        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_rows": 0,
                "filtered_rows": 0,
                "saved_rows": 0,
                "anomalies": [],
                "statistics": {}
            }

    def _bulk_save_parks(self, records: List[Dict[str, Any]], file_upload_id: int = None) -> int:
        """Bulk save parks to database for maximum performance"""
        if not records:
            return 0

        try:
            # Prepare data for bulk insert
            park_data = []
            for record in records:
                try:
                    park_record = self._map_to_park_dict(
                        record, file_upload_id)
                    park_data.append(park_record)
                except Exception as e:
                    logger.warning(
                        f"Skipping record due to mapping error: {e}")
                    continue

            if not park_data:
                logger.warning("No valid records to save after mapping")
                return 0

            # Use bulk insert for maximum performance
            with self.bulk_engine.begin() as conn:
                # Use pandas to_sql for bulk insert (fastest method)
                df = pd.DataFrame(park_data)
                df.to_sql(
                    'parks',
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )

            logger.info(f"Bulk saved {len(park_data)} park records")
            return len(park_data)

        except Exception as e:
            logger.error(f"Bulk save failed: {e}")
            # Fallback to individual saves
            return self._fallback_save_parks(records, file_upload_id)

    def _fallback_save_parks(self, records: List[Dict[str, Any]], file_upload_id: int = None) -> int:
        """Fallback method for saving parks individually"""
        saved_count = 0
        db = SessionLocal()

        try:
            for record in records:
                try:
                    park_record = self._map_to_park_dict(
                        record, file_upload_id)
                    park = Park(**park_record)
                    park.created_at = datetime.utcnow()

                    db.add(park)
                    saved_count += 1

                    # Commit in batches
                    if saved_count % 1000 == 0:
                        db.commit()

                except Exception as e:
                    logger.error(f"Error saving individual record: {e}")
                    # Rollback the current transaction and continue
                    try:
                        db.rollback()
                    except:
                        pass
                    continue

            db.commit()

        except Exception as e:
            logger.error(f"Error in fallback save: {e}")
            try:
                db.rollback()
            except:
                pass
        finally:
            db.close()

        return saved_count

    def _map_to_park_dict(self, record: Dict[str, Any], file_upload_id: int = None) -> Dict[str, Any]:
        """Map Excel record to Park dictionary for bulk insert"""
        return {
            'file_upload_id': file_upload_id,
            'extraction_date': self._safe_date(record.get('Extraction Date_Date d \'extraction')),
            'dot_id': self._safe_int(record.get('dot_id')),
            'actel_code': self._safe_string(record.get('Actel Code_Code d\'actel')),
            'customer_l1_code': self._safe_string(record.get('Code Customer L1_Code Catégorie level 1')),
            'customer_l1_description': self._safe_string(record.get('Description Customer L1_Nom du Catégorie level 1')),
            'customer_l2_code': self._safe_string(record.get('Code Customer L2_Code Catégorie level 2')),
            'customer_l2_description': self._safe_string(record.get('Description Customer L2_Nom du Catégorie level 2')),
            'customer_l3_code': self._safe_string(record.get('Code Customer L3_Code Catégorie level 3')),
            'customer_l3_description': self._safe_string(record.get('Description Customer L3_Nom du Catégorie level 3')),
            'telecom_type': self._safe_string(record.get('Telecom type_SERVICE / PRODUIT')),
            'offer_type': self._safe_string(record.get('Offer Type_Type d\'offre')),
            'offer_name': self._safe_string(record.get('Offer name_Nom de l\'offre')),
            'rental_fees': self._safe_float(record.get('Rental Fees_Frais d\'abonnement')),
            'customer_code': self._safe_string(record.get('Customer code_NCLI')),
            'service_number': self._safe_string(record.get('Service number_ND')),
            'related_service_number': self._safe_string(record.get('Related Service Number_Numero de service correspondant')),
            'username': self._safe_string(record.get('USERNAME_Nom d\'utilisateur')),
            'subscriber_status': self._safe_string(record.get('Subscriber status_Status de l\'abonne')),
            'status_date': self._safe_date(record.get('Status date_Date du statut')),
            'creation_date': self._safe_date(record.get('Creation Date_Date de creation')),
            'active_date': self._safe_date(record.get('Active Date_Date d\'activation')),
            'csr_name': self._safe_string(record.get('CSR Name_Nom CSR')),
            'department_name': self._safe_string(record.get('Department Name_Nom de département1')),
            'state': self._safe_string(record.get('State_Wilaya')),
            'area': self._safe_string(record.get('Area_Daira')),
            'town': self._safe_string(record.get('Town_Commune')),
            'grid': self._safe_string(record.get('Grid_Quartier')),
            'street': self._safe_string(record.get('Street_Voie')),
            'street_number': self._safe_string(record.get('Street Number_Numero De Voie')),
            'building_no': self._safe_string(record.get('Building No._Batiment')),
            'unit': self._safe_string(record.get('Unit_Escalier')),
            'floor': self._safe_string(record.get('Floor_Etage')),
            'house_no': self._safe_string(record.get('House No._Numero de maison')),
            'additional_address_info': self._safe_string(record.get('Additional Address Information_Complément d\'adresse')),
            'customer_full_name': self._safe_string(record.get('Customer full name_NOM ET PRENOM')),
            'province': self._safe_string(record.get('Province_Wilaya')),
            'district': self._safe_string(record.get('District_Daira')),
            'city': self._safe_string(record.get('City_Commune')),
            'postal_code': self._safe_string(record.get('Postal Code_Code postal')),
            'expiry_date': self._safe_date(record.get('Expiry Date_Date d\'expiration')),
            'iccid': self._safe_string(record.get('ICCID_N° SIM')),
            'imsi': self._safe_string(record.get('IMSI_IMSI')),
            'contact_number': self._safe_string(record.get('Contact number_Numéro de contact')),
            'created_at': datetime.utcnow()
        }

    def _create_dots(self):
        """Create DOTs if they don't exist"""
        db = SessionLocal()
        try:
            # Create DOT OUARGLA
            if not db.query(DOT).filter(DOT.name == "DOT OUARGLA").first():
                dot_ouargla = DOT(
                    name="DOT OUARGLA",
                    description="DOT for Ouargla region",
                    created_at=datetime.utcnow()
                )
                db.add(dot_ouargla)

            # Create DOT SIEGE
            if not db.query(DOT).filter(DOT.name == "DOT SIEGE").first():
                dot_siege = DOT(
                    name="DOT SIEGE",
                    description="DOT for Grand Compte",
                    created_at=datetime.utcnow()
                )
                db.add(dot_siege)

            db.commit()

        finally:
            db.close()

    def _safe_date(self, value) -> Optional[datetime]:
        """Safely convert value to date"""
        if pd.isna(value) or value is None:
            return None
        try:
            if isinstance(value, str):
                return pd.to_datetime(value)
            elif hasattr(value, 'to_pydatetime'):
                return value.to_pydatetime()
            return None
        except:
            return None

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if pd.isna(value) or value is None:
            return None
        try:
            return float(value)
        except:
            return None

    def _safe_string(self, value) -> Optional[str]:
        """Safely convert value to string"""
        if pd.isna(value) or value is None:
            return None
        try:
            # Convert to string, handling both numeric and string values
            if isinstance(value, (int, float)):
                # For large numbers, convert to string without scientific notation
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                else:
                    return str(value)
            return str(value)
        except:
            return None

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to integer"""
        if pd.isna(value) or value is None:
            return None
        try:
            return int(value)
        except:
            return None

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a processing task"""
        return self.active_tasks.get(task_id)

    def _send_websocket_update(self, task_id: str, data: Dict[str, Any]):
        """Send WebSocket update for task progress"""
        try:
            # Update the task data in memory immediately
            if task_id in self.active_tasks:
                self.active_tasks[task_id].update({
                    "progress": data.get("progress", 0),
                    "status": data.get("status", "processing"),
                    "message": data.get("message", ""),
                    "saved_rows": data.get("saved_count", 0),
                    "errors_count": data.get("errors_count", 0),
                })

            # For now, log the progress update (the file processing service handles the actual WebSocket sends)
            logger.info(
                f"📊 Background processor progress for task {task_id}: {data.get('progress', 0)}% - {data.get('message', 'Processing...')}")

        except Exception as e:
            logger.warning(f"Failed to update task progress: {e}")

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a processing task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["cancelled"] = True
            self.active_tasks[task_id]["status"] = ProcessingStatus.CANCELLED
            return True
        return False

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active tasks"""
        return self.active_tasks.copy()

    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.utcnow() - pd.Timedelta(hours=max_age_hours)

        tasks_to_remove = []
        for task_id, task in self.active_tasks.items():
            if (task["status"] in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]
                    and task["end_time"] and task["end_time"] < cutoff_time):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]

        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

    def shutdown(self):
        """Shutdown the processor and kill all child processes"""
        logger.info("Shutting down background processor...")

        # Set shutdown event to stop processing
        self._shutdown_event.set()

        # Cancel all active tasks
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)

        # Shutdown thread pool
        logger.info("Shutting down thread pool...")
        self.thread_pool.shutdown(wait=False, cancel_futures=True)

        # Shutdown process pool
        logger.info("Shutting down process pool...")
        self.process_pool.shutdown(wait=False, cancel_futures=True)

        # Close database engine
        logger.info("Closing database engine...")
        self.bulk_engine.dispose()

        logger.info("Background processor shutdown complete")

    def set_max_rows_limit(self, limit: int):
        """Set the maximum number of rows to process (for testing)"""
        self.max_rows_limit = limit
        logger.info(f"Set max rows limit to {limit} for testing")


# Global processor instance
background_processor = BackgroundProcessor()

