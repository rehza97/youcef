"""
High-Performance Background Processing System for Park Data
Handles large Excel files with multi-threading and bulk operations
"""

import asyncio
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
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
from services.dot_service import DOTService
from prk_column_mapping import map_prk_record_to_park_dict
from services.fast_batch_mapper import fast_mapper
import uuid

logger = logging.getLogger(__name__)

# Thread-local storage for per-thread DOT cache (Performance optimization)
thread_local = threading.local()


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
        # ✅ OPTIMIZED: 8 workers for optimal CPU/IO balance
        self.max_workers = max_workers or min(8, (os.cpu_count() or 1))
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(
            max_workers=min(4, os.cpu_count() or 1))
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.batch_size = 20000
        self.chunk_size = 5000
        self.max_rows_limit = None
        self._shutdown_event = threading.Event()
        self._last_websocket_update = {}

        # ✅ PERFORMANCE: Global DOT cache with lock
        self._dot_cache = {}  # {dot_name_upper: dot_id}
        self._dot_cache_lock = threading.Lock()

        # ✅ PERFORMANCE: Dedicated background engine
        from database.connection import background_engine
        self.bulk_engine = background_engine

        # ✅ NEW: Pre-compile column mapping for vectorization
        self._column_mapping_cache = {}

        logger.info(f"✅ Background processor initialized (OPTIMIZED v2.0):")
        logger.info(f"   Workers: {self.max_workers} threads")
        logger.info(f"   Chunk size: {self.chunk_size} rows")
        logger.info(
            f"   Features: Streaming pipeline + Vectorization + Thread-local cache")

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
                    "total_records": 0,  # Frontend expects this field
                    "processed_rows": 0,
                    "filtered_rows": 0,  # Add missing field
                    "saved_rows": 0,
                    "errors": 0
                }
            })

            # ✅ OPTIMIZED: Streaming pipeline with as_completed()
            # Process chunks as they're read (no pre-collection)
            chunk_num = 0
            total_processed = 0
            active_futures = {}  # {future: (chunk_num, chunk_size)}
            chunks_submitted = 0

            logger.info(
                f"🚀 Starting OPTIMIZED streaming pipeline with {self.max_workers} workers")

            # Stream chunks and process immediately
            for chunk_df in self._read_file_chunks(file_path, chunksize=self.chunk_size):
                if task["cancelled"] or self._shutdown_event.is_set():
                    task["status"] = ProcessingStatus.CANCELLED
                    return

                chunk_num += 1
                chunk_size = len(chunk_df)

                # ✅ Submit immediately (no waiting for all chunks)
                future = self.thread_pool.submit(
                    self._process_chunk, chunk_df, task_id)
                active_futures[future] = (chunk_num, chunk_size)
                chunks_submitted += 1

                # ✅ Process completed chunks as they finish (non-blocking)
                # Check if we have capacity or if any futures are done
                while len(active_futures) >= self.max_workers or (chunks_submitted > 0 and any(f.done() for f in active_futures)):
                    # Use as_completed to get results as they finish
                    completed_futures = [f for f in active_futures if f.done()]

                    for future in completed_futures:
                        chunk_num_completed, chunk_size_completed = active_futures[future]
                        del active_futures[future]

                        try:
                            chunk_result = future.result(timeout=1)

                            if chunk_result["success"]:
                                processed_rows += chunk_result["processed_rows"]
                                filtered_rows += chunk_result["filtered_rows"]
                                saved_rows += chunk_result["saved_rows"]
                                total_processed += chunk_size_completed
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

                                logger.debug(
                                    f"✅ Chunk {chunk_num_completed} completed ({saved_rows} total saved)")
                            else:
                                task["errors"].append(
                                    f"Chunk {chunk_num_completed} failed: {chunk_result['error']}")
                                logger.error(
                                    f"❌ Chunk {chunk_num_completed} failed")

                        except Exception as e:
                            error_msg = f"Chunk {chunk_num_completed} failed: {str(e)}"
                            task["errors"].append(error_msg)
                            logger.error(error_msg)

                        # Update progress after each completed chunk
                        progress = min(
                            100, (total_processed / total_rows) * 100) if total_rows > 0 else 0
                        task["progress"] = progress
                        task["processed_rows"] = processed_rows
                        task["filtered_rows"] = filtered_rows
                        task["saved_rows"] = saved_rows

                        # Throttled WebSocket updates (every 2 seconds)
                        self._send_websocket_update(task_id, {
                            "status": "processing",
                            "progress": progress,
                            "message": f"Processing... {saved_rows}/{total_rows} saved",
                            "saved_count": saved_rows,
                            "errors_count": len(task.get("errors", [])),
                            "statistics": {
                                "total_rows": total_rows,
                                "total_records": processed_rows,
                                "processed_rows": processed_rows,
                                "filtered_rows": filtered_rows,
                                "saved_rows": saved_rows,
                                "errors": len(task.get("errors", []))
                            }
                        })

                    # Break if we have capacity for more chunks
                    if len(active_futures) < self.max_workers:
                        break

            # ✅ Process remaining futures using as_completed() for optimal performance
            logger.info(
                f"📥 Processing {len(active_futures)} remaining chunks...")
            for future in as_completed(active_futures.keys()):
                chunk_num_completed, chunk_size_completed = active_futures[future]

                try:
                    chunk_result = future.result(timeout=300)

                    if chunk_result["success"]:
                        processed_rows += chunk_result["processed_rows"]
                        filtered_rows += chunk_result["filtered_rows"]
                        saved_rows += chunk_result["saved_rows"]
                        total_processed += chunk_size_completed
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

                        logger.debug(
                            f"✅ Final chunk {chunk_num_completed} completed")
                    else:
                        task["errors"].append(
                            f"Chunk {chunk_num_completed} failed: {chunk_result['error']}")

                except Exception as e:
                    error_msg = f"Chunk {chunk_num_completed} failed: {str(e)}"
                    task["errors"].append(error_msg)
                    logger.error(error_msg)

            # Final update
            task["progress"] = 100
            task["processed_rows"] = processed_rows
            task["filtered_rows"] = filtered_rows
            task["saved_rows"] = saved_rows
            task["anomalies"] = all_anomalies
            task["statistics"] = all_statistics

            logger.info(
                f"🎉 Streaming pipeline completed: {chunks_submitted} chunks processed")

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

    def _read_file_chunks(self, file_path: str, chunksize: int = 5000):
        """Generator that yields chunks of data from any supported file type"""
        from pathlib import Path
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.csv':
            # CSV file - use chunksize
            for chunk in pd.read_csv(file_path, chunksize=chunksize):
                yield chunk
        elif file_ext in ['.xlsx', '.xls']:
            # Excel file - read entire file then yield in chunks
            try:
                if file_ext == '.xlsx':
                    df = pd.read_excel(file_path, engine='openpyxl')
                else:
                    # .xls - might be HTML masquerading as Excel
                    try:
                        df = pd.read_excel(file_path, engine='xlrd')
                    except:
                        # Try HTML parsing - use largest table
                        tables = pd.read_html(file_path)
                        if tables:
                            df = max(tables, key=len)
                        else:
                            logger.error("No tables found in HTML file")
                            return

                # Yield in chunks
                for start in range(0, len(df), chunksize):
                    yield df.iloc[start:start + chunksize]
            except Exception as e:
                logger.error(f"Error reading Excel file: {e}")
                raise
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _count_file_rows(self, file_path: str) -> int:
        """Count total rows in file efficiently"""
        try:
            from pathlib import Path
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.csv':
                # CSV file - use chunksize
                chunk_iter = pd.read_csv(file_path, chunksize=10000)
                total_rows = 0
                for chunk in chunk_iter:
                    total_rows += len(chunk)
                return total_rows
            elif file_ext in ['.xlsx', '.xls']:
                # Excel file - read with appropriate engine
                try:
                    if file_ext == '.xlsx':
                        df = pd.read_excel(file_path, engine='openpyxl', nrows=None)
                    else:
                        # .xls - might be HTML masquerading as Excel
                        try:
                            df = pd.read_excel(file_path, engine='xlrd', nrows=None)
                        except:
                            # Try HTML parsing
                            tables = pd.read_html(file_path)
                            if tables:
                                # Use largest table
                                df = max(tables, key=len)
                            else:
                                return 0
                    return len(df)
                except Exception as e:
                    logger.error(f"Error reading Excel file: {e}")
                    return 0
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                return 0
        except Exception as e:
            logger.error(f"Error counting rows: {e}")
            return 0

    def _process_chunk(self, chunk_df: pd.DataFrame, task_id: str) -> Dict[str, Any]:
        """Process a chunk of data"""
        db_session = None
        try:
            # Get file_upload_id from task
            task = self.active_tasks.get(task_id, {})
            file_upload_id = int(task.get("file_id")) if task.get(
                "file_id") else None

            # Create database session for processing
            db_session = SessionLocal()

            # Apply processing rules
            processor = ParkDataProcessor(db_session)
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
        finally:
            # Always close the database session
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    logger.warning(f"Error closing database session: {e}")

    def _bulk_save_parks(self, records: List[Dict[str, Any]], file_upload_id: int = None) -> int:
        """✅ OPTIMIZED v3: ULTRA-FAST batch mapping with vectorized operations"""
        if not records:
            return 0

        try:
            import time
            t_start = time.time()

            # ✅ ULTRA-FAST: Convert records → DataFrame → Map columns (NO LOOPS!)
            logger.info(f"⚡ Fast-mapping {len(records)} records...")
            df_source = pd.DataFrame(records)

            t1 = time.time()
            # Use fast batch mapper (50× faster than loop!)
            df = fast_mapper.map_dataframe_to_parks(df_source, file_upload_id)
            t2 = time.time()

            logger.info(
                f"✅ Mapped in {(t2-t1):.2f}s ({len(records)/(t2-t1):.0f} rec/s)")

            if df.empty:
                return 0

            # ✅ STEP 2: Extract unique DOT names using vectorized operations
            dot_col = None
            for col_name in ['dot_name', 'DOT', 'dot']:
                if col_name in df.columns:
                    dot_col = col_name
                    break

            if dot_col:
                # Vectorized: Get unique DOT names (1 operation instead of 5000 iterations)
                unique_dot_names = df[dot_col].dropna(
                ).str.strip().str.upper().unique()

                if len(unique_dot_names) > 0:
                    logger.debug(
                        f"📊 {len(unique_dot_names)} unique DOTs in batch of {len(df)} records")

                    # ✅ STEP 3: Use thread-local cache (reduces lock contention)
                    for dot_name in unique_dot_names:
                        self._get_dot_id_thread_local(dot_name)

                    # ✅ VECTORIZATION: Map all DOT names to IDs at once
                    df['dot_id'] = df[dot_col].str.strip().str.upper().map(
                        self._get_thread_local_dot_cache())

                    # Fill NaN with default DOT
                    default_dot_id = self._get_dot_id_thread_local(
                        "DOT OUARGLA")
                    df['dot_id'] = df['dot_id'].fillna(
                        default_dot_id).astype('Int64')

                    # Remove dot_name column as we have dot_id now
                    df = df.drop(columns=[dot_col], errors='ignore')

            # ✅ STEP 4: Add file_upload_id and timestamp (vectorized)
            df['file_upload_id'] = file_upload_id
            df['created_at'] = datetime.utcnow()

            # ✅ STEP 5: Bulk insert (already optimized)
            logger.info(f"💾 Bulk inserting {len(df)} records into database...")
            with self.bulk_engine.begin() as conn:
                df.to_sql(
                    'parks',
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=10000
                )

            logger.info(
                f"✅ SAVED {len(df)} records to database successfully!")
            return len(df)

        except Exception as e:
            logger.error(f"❌ Vectorized bulk save failed: {e}")
            logger.exception(e)  # Show full stack trace
            # Fallback to old method
            return self._bulk_save_parks_fallback(records, file_upload_id)

    def _bulk_save_parks_fallback(self, records: List[Dict[str, Any]], file_upload_id: int = None) -> int:
        """Old loop-based method (fallback if vectorization fails)"""
        park_data = []
        for record in records:
            try:
                park_record = self._map_to_park_dict(record, file_upload_id)
                park_data.append(park_record)
            except Exception as e:
                logger.warning(f"Skipping record: {e}")
                continue

        if park_data:
            with self.bulk_engine.begin() as conn:
                df = pd.DataFrame(park_data)
                df.to_sql('parks', conn, if_exists='append',
                          index=False, method='multi', chunksize=10000)
            return len(park_data)
        return 0

    def _fallback_save_parks(self, records: List[Dict[str, Any]], file_upload_id: int = None) -> int:
        """Individual save fallback method (slowest, for errors only)"""
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
        """Map Excel record to Park dictionary for bulk insert with DOT auto-creation"""
        # First try to use the PRK-specific mapping
        try:
            park_dict = map_prk_record_to_park_dict(record, file_upload_id)

            # Get actel code and DOT name for DOT assignment
            actel_code = park_dict.get('actel_code')
            dot_name = park_dict.get('dot_name')  # Get from mapped park_dict

            # Handle DOT assignment - prioritize DOT name from file
            dot_id = None
            if 'dot_id' in park_dict and park_dict.get('dot_id') is not None:
                # DOT ID already set
                dot_id = self._safe_int(park_dict.get('dot_id'))
            elif dot_name:
                # Use DOT name from file (most reliable source)
                dot_id = self._get_or_create_dot_id(dot_name)
                logger.debug(
                    f"DOT assigned from file: {dot_name} -> ID {dot_id}")
            elif actel_code:
                # Auto-assign DOT based on actel code
                dot_id = self._get_dot_id_from_actel_code(actel_code)
                logger.debug(
                    f"DOT assigned from actel code: {actel_code} -> ID {dot_id}")

            # Fallback: assign to DOT OUARGLA if no DOT is determined
            if dot_id is None:
                dot_id = self._get_or_create_dot_id("DOT OUARGLA")
                logger.debug(
                    f"DOT assigned fallback: DOT OUARGLA -> ID {dot_id}")

            park_dict['dot_id'] = dot_id
            # Remove dot_name from park_dict as we now have dot_id
            if 'dot_name' in park_dict:
                del park_dict['dot_name']
            return park_dict

        except Exception as e:
            logger.warning(
                f"PRK mapping failed, falling back to generic mapping: {e}")
            # Fallback to generic mapping for non-PRK files
            return self._map_to_park_dict_generic(record, file_upload_id)

    def _map_to_park_dict_generic(self, record: Dict[str, Any], file_upload_id: int = None) -> Dict[str, Any]:
        """Generic mapping for non-PRK files"""
        # Get actel code from various possible column names
        actel_code = None
        for col_name in ['Actel Code', 'Actel Code_Code d\'actel', 'actel_code_code_d_actel', 'actel_code']:
            if col_name in record and record.get(col_name) is not None:
                actel_code = self._safe_string(record.get(col_name))
                break

        # Handle DOT assignment based on actel code
        dot_id = None
        if 'dot_id' in record and record.get('dot_id') is not None:
            dot_id = self._safe_int(record.get('dot_id'))
        elif 'dot_name' in record and record.get('dot_name') is not None:
            # Auto-create DOT if DOT name is provided
            dot_name = self._safe_string(record.get('dot_name'))
            if dot_name:
                dot_id = self._get_or_create_dot_id(dot_name)
        elif actel_code:
            # Auto-assign DOT based on actel code
            dot_id = self._get_dot_id_from_actel_code(actel_code)

        # Fallback: assign to DOT OUARGLA if no DOT is determined
        if dot_id is None:
            dot_id = self._get_or_create_dot_id("DOT OUARGLA")

        return {
            'file_upload_id': file_upload_id,
            'extraction_date': self._safe_date(record.get('Extraction Date_Date d \'extraction')),
            'dot_id': dot_id,
            'actel_code': actel_code,
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

    def _get_dot_id_thread_local(self, dot_name: str) -> Optional[int]:
        """✅ OPTIMIZED: Thread-local DOT cache (reduces lock contention)"""
        if not dot_name:
            return None

        dot_name_normalized = dot_name.strip().upper()

        # Initialize thread-local cache if needed
        if not hasattr(thread_local, 'dot_cache'):
            thread_local.dot_cache = {}

        # Check thread-local cache first (NO LOCK!)
        if dot_name_normalized in thread_local.dot_cache:
            return thread_local.dot_cache[dot_name_normalized]

        # Check global cache with lock
        with self._dot_cache_lock:
            if dot_name_normalized in self._dot_cache:
                dot_id = self._dot_cache[dot_name_normalized]
                # Cache in thread-local for future lookups
                thread_local.dot_cache[dot_name_normalized] = dot_id
                return dot_id

        # Cache miss - query database (rare)
        db = SessionLocal()
        try:
            dot = DOTService.get_or_create_dot(db=db, name=dot_name.strip())
            dot_id = dot.id if dot else None

            # Update both caches
            with self._dot_cache_lock:
                self._dot_cache[dot_name_normalized] = dot_id
            thread_local.dot_cache[dot_name_normalized] = dot_id

            return dot_id
        finally:
            db.close()

    def _get_thread_local_dot_cache(self) -> Dict[str, int]:
        """Get thread-local DOT cache for vectorized mapping"""
        if not hasattr(thread_local, 'dot_cache'):
            thread_local.dot_cache = {}
        return thread_local.dot_cache

    def _create_dots(self):
        """Create DOTs and pre-populate cache (CRITICAL PERFORMANCE FIX)"""
        db = SessionLocal()
        try:
            dots_to_create = [
                ("DOT OUARGLA", "DOT for Ouargla region"),
                ("DOT SIEGE", "DOT for Grand Compte"),
            ]

            for dot_name, description in dots_to_create:
                dot = DOTService.get_or_create_dot(
                    db=db,
                    name=dot_name,
                    description=description
                )

                # ✅ Pre-populate cache for immediate access
                with self._dot_cache_lock:
                    self._dot_cache[dot_name.upper()] = dot.id

                logger.info(f"✅ Pre-cached DOT: {dot_name} → ID {dot.id}")

            logger.info(
                f"✅ DOT cache initialized with {len(self._dot_cache)} entries: {list(self._dot_cache.keys())}")

        except Exception as e:
            logger.error(f"Error creating DOTs: {e}")
        finally:
            db.close()

    def _ensure_dot_assignments(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure all records have DOT assignments"""
        # Get default DOT OUARGLA ID
        default_dot_id = self._get_or_create_dot_id("DOT OUARGLA")

        updated_count = 0
        for record in records:
            if record.get('dot_id') is None:
                record['dot_id'] = default_dot_id
                updated_count += 1

        if updated_count > 0:
            logger.info(
                f"Assigned default DOT to {updated_count} records without DOT assignment")

        return records

    def _get_or_create_dot_id(self, dot_name: str) -> Optional[int]:
        """Get or create DOT by name and return its ID (DEPRECATED - use cached version)"""
        # ⚠️ DEPRECATED: This function makes a DB query every time!
        # Use _get_or_create_dot_id_cached() instead for 1000× better performance
        return self._get_or_create_dot_id_cached(dot_name)

    def _get_or_create_dot_id_cached(self, dot_name: str) -> Optional[int]:
        """Get or create DOT by name with caching (CRITICAL PERFORMANCE FIX)"""
        if not dot_name:
            return None

        dot_name_normalized = dot_name.strip().upper()

        # ✅ Check cache first (in-memory, instant)
        with self._dot_cache_lock:
            if dot_name_normalized in self._dot_cache:
                return self._dot_cache[dot_name_normalized]

        # Cache miss - query database (only once per unique DOT)
        logger.info(f"🔍 DOT cache MISS: {dot_name} - querying database...")
        db = SessionLocal()
        try:
            dot = DOTService.get_or_create_dot(
                db=db,
                name=dot_name.strip(),
                description=f"Auto-created DOT for region: {dot_name.strip()}"
            )
            dot_id = dot.id if dot else None

            # ✅ Store in cache for future lookups
            with self._dot_cache_lock:
                self._dot_cache[dot_name_normalized] = dot_id

            logger.info(
                f"✅ Cached DOT: {dot_name} → ID {dot_id} (cache size: {len(self._dot_cache)})")
            return dot_id
        except Exception as e:
            logger.error(f"Error getting/creating DOT '{dot_name}': {e}")
            return None
        finally:
            db.close()

    def _get_dot_id_from_actel_code(self, actel_code: str) -> Optional[int]:
        """Get DOT ID based on actel code using business rules"""
        if not actel_code:
            return None

        actel_str = str(actel_code).upper()

        # Business rules for DOT assignment based on actel code
        if "2B" in actel_str and "HASSI MESSAOUD" in actel_str:
            return self._get_or_create_dot_id("DOT OUARGLA")
        elif "99" in actel_str and "GRAND COMPTE" in actel_str:
            return self._get_or_create_dot_id("DOT SIEGE")
        elif "2B" in actel_str:
            return self._get_or_create_dot_id("DOT OUARGLA")
        elif "99" in actel_str:
            return self._get_or_create_dot_id("DOT SIEGE")

        # Default fallback
        return self._get_or_create_dot_id("DOT OUARGLA")

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
        """Send WebSocket update for task progress with throttling to prevent browser slowdown"""
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

            # Throttle WebSocket updates to prevent browser slowdown
            current_time = datetime.utcnow()
            last_update = self._last_websocket_update.get(task_id)

            # Only send WebSocket update if:
            # 1. It's the first update for this task
            # 2. At least 2 seconds have passed since last update
            # 3. It's a completion/error status
            should_send = (
                last_update is None or
                (current_time - last_update).total_seconds() >= 2.0 or
                data.get("status") in ["completed", "failed", "cancelled"]
            )

            if should_send:
                self._last_websocket_update[task_id] = current_time

                # Send actual WebSocket update
                import asyncio
                from services.processing_websocket import processing_ws_manager

                # Run the async WebSocket update in the event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule the coroutine
                        asyncio.create_task(
                            processing_ws_manager.send_task_update(task_id, data))
                    else:
                        # If not in async context, run it
                        loop.run_until_complete(
                            processing_ws_manager.send_task_update(task_id, data))
                except RuntimeError:
                    # If no event loop exists, create one
                    asyncio.run(
                        processing_ws_manager.send_task_update(task_id, data))

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
