import mimetypes
from models.user import User
import os
import json
import uuid
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models.file_upload import FileUpload, FilePreview, FileUploadCreate, FilePreviewCreate

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file uploads and processing"""

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

        # Create subdirectories for different file types
        (self.upload_dir / "excel").mkdir(exist_ok=True)
        (self.upload_dir / "csv").mkdir(exist_ok=True)
        (self.upload_dir / "temp").mkdir(exist_ok=True)

    def get_file_type(self, filename: str, mime_type: str) -> str:
        """Determine file type based on filename and MIME type"""
        filename_lower = filename.lower()

        # Check Excel files
        if (filename_lower.endswith(('.xlsx', '.xls')) or
            mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'application/vnd.ms-excel']):
            return 'excel'

        # Check CSV files
        if (filename_lower.endswith('.csv') or
                mime_type in ['text/csv', 'application/csv']):
            return 'csv'

        raise HTTPException(
            status_code=400, detail="Unsupported file type. Only Excel and CSV files are supported.")

    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Check file type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        self.get_file_type(file.filename, mime_type or '')

    def save_file(self, file: UploadFile, user_id: int) -> Tuple[str, str]:
        """Save uploaded file and return file path and filename"""
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Determine file type and subdirectory
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        file_type = self.get_file_type(file.filename, mime_type or '')

        # Save to appropriate subdirectory
        subdir = self.upload_dir / file_type
        file_path = subdir / unique_filename

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return str(file_path), unique_filename

    async def save_uploaded_file(self, db: Session, file: UploadFile, user_id: int) -> FileUpload:
        """Save uploaded file and create database record"""
        from models.file_upload import FileUpload, FileUploadCreate

        # Validate file
        self.validate_file(file)

        # Reset file pointer to beginning
        await file.seek(0)

        # Get file size
        file_size = 0
        content = await file.read()
        file_size = len(content)

        # Reset file pointer again
        await file.seek(0)

        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Determine file type and subdirectory
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        file_type = self.get_file_type(file.filename, mime_type or '')

        # Save to appropriate subdirectory
        subdir = self.upload_dir / file_type
        file_path = subdir / unique_filename

        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Detect KPI type for CSV and Excel files
        detected_kpi_type = None
        detection_confidence = None

        if file_type in ['excel', 'csv']:
            try:
                from services.file_detector_service import file_detector_service
                logger.info(f"🔍 Detecting KPI type for file: {file.filename}")

                kpi_type, detection_info = file_detector_service.detect_file_type(
                    str(file_path))
                detected_kpi_type = detection_info.get('detected_type')
                detection_confidence = int(detection_info.get('confidence', 0))

                logger.info(
                    f"✅ Detected KPI type: {detected_kpi_type} ({detection_confidence}% confidence)")
                logger.info(
                    f"   Matched columns: {detection_info.get('matched_columns', [])}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to detect KPI type: {str(e)}")
                # Continue without detection - not a critical error

        # Create database record
        file_upload = FileUpload(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type or '',
            uploaded_by=user_id,
            is_processed=False,
            processing_status="pending",
            detected_kpi_type=detected_kpi_type,
            detection_confidence=detection_confidence
        )

        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # File upload completed successfully with KPI detection
        logger.info(f"File upload completed successfully: {file_upload.id}")
        logger.info(f"  - Original filename: {file_upload.original_filename}")
        logger.info(f"  - Detected KPI type: {detected_kpi_type}")
        logger.info(f"  - Detection confidence: {detection_confidence}%")
        logger.info(f"  - File size: {file_size} bytes")

        return file_upload

    def process_excel_file(self, file_path: str, max_rows: int = 100) -> List[Dict[str, Any]]:
        """Process Excel file and return preview data"""
        try:
            logger.info(f"Reading Excel file: {file_path}")

            # Validate file is actually an Excel file; if it's HTML masquerading as .xls, we'll handle via HTML fallback
            is_html_fake_xls = False
            try:
                self._validate_excel_file(file_path)
            except HTTPException as ex:
                # If HTML masquerading as .xls, allow fallback path
                error_detail = str(ex.detail).lower()
                if ex.status_code == 400 and ('html' in error_detail or 'html content' in error_detail):
                    logger.info("⚠️ File detected as HTML, will attempt to parse as HTML tables")
                    is_html_fake_xls = True
                else:
                    raise

            # Determine engine based on file extension
            file_ext = Path(file_path).suffix.lower()
            if file_ext == '.xls':
                engine = 'xlrd'
            elif file_ext == '.xlsx':
                engine = 'openpyxl'
            else:
                engine = None  # Let pandas auto-detect

            # If HTML masquerading as .xls, parse HTML tables instead of using Excel engines
            if is_html_fake_xls:
                logger.info("Parsing HTML tables from .xls file")
                # Read tables without header first to detect structure
                tables_raw = pd.read_html(file_path, header=None)
                previews = []
                # limit to first 5 tables
                for idx, table_raw in enumerate(tables_raw[:5]):
                    logger.info(
                        f"HTML table {idx}: {len(table_raw)} rows, {len(table_raw.columns)} columns")

                    # Search for header row in first 20 rows
                    header_row = self._find_header_row_in_table(table_raw)

                    if header_row is not None and header_row > 0:
                        # Skip rows before header and set proper column names
                        logger.info(f"   Found headers at row {header_row}")
                        df = table_raw.iloc[header_row+1:].copy()  # Data starts after header
                        df.columns = table_raw.iloc[header_row].astype(str).tolist()  # Set header names
                        df.reset_index(drop=True, inplace=True)
                    elif header_row == 0:
                        # Header is at row 0
                        logger.info(f"   Found headers at row 0")
                        df = table_raw.iloc[1:].copy()  # Data starts after header
                        df.columns = table_raw.iloc[0].astype(str).tolist()
                        df.reset_index(drop=True, inplace=True)
                    else:
                        # No clear header found, use table as-is
                        logger.info(f"   No clear header found, using default column names")
                        df = table_raw

                    logger.info(f"   Processing {len(df)} data rows with {len(df.columns)} columns")

                    preview_data = self._get_dataframe_preview(df, max_rows)
                    previews.append({
                        "sheet_name": f"table_{idx}",
                        "preview_data": preview_data,
                        "total_rows": len(df),
                        "total_columns": len(df.columns),
                        "preview_rows": min(max_rows, len(df))
                    })
                logger.info(
                    f"HTML file processing completed. Generated {len(previews)} previews")
                return previews

            # Read Excel file with appropriate engine
            if engine:
                excel_file = pd.ExcelFile(file_path, engine=engine)
            else:
                excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")

            previews = []

            for sheet_name in sheet_names:
                logger.info(f"Processing sheet: {sheet_name}")

                # Read sheet with limited rows for preview
                if engine:
                    df = pd.read_excel(
                        file_path, sheet_name=sheet_name, nrows=max_rows * 2, engine=engine)
                else:
                    df = pd.read_excel(
                        file_path, sheet_name=sheet_name, nrows=max_rows * 2)

                logger.info(
                    f"Sheet {sheet_name}: {len(df)} rows, {len(df.columns)} columns")

                # Get preview data
                preview_data = self._get_dataframe_preview(df, max_rows)

                previews.append({
                    "sheet_name": sheet_name,
                    "preview_data": preview_data,
                    "total_rows": len(df),  # Note: This is limited by nrows
                    "total_columns": len(df.columns),
                    "preview_rows": min(max_rows, len(df))
                })

                logger.info(f"Completed processing sheet: {sheet_name}")

            logger.info(
                f"Excel file processing completed. Generated {len(previews)} previews")
            return previews

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Error processing Excel file {file_path}: {error_msg}")

            # Provide more helpful error messages
            if "Expected BOF record; found" in error_msg and "html" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file appears to be HTML content, not a valid Excel file. Please ensure you're uploading a proper Excel file (.xls or .xlsx)."
                )
            elif "Unsupported format" in error_msg or "corrupt file" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="The file appears to be corrupted or in an unsupported format. Please ensure you're uploading a valid Excel file (.xls or .xlsx)."
                )
            else:
                raise HTTPException(
                    status_code=500, detail=f"Error processing Excel file: {error_msg}"
                )

    def _validate_excel_file(self, file_path: str) -> None:
        """Validate that the file is actually an Excel file by checking file header"""
        try:
            with open(file_path, 'rb') as f:
                # Read first 50 bytes to check file signature and detect HTML
                header = f.read(50)
                header_lower = header.lower()
                # Strip leading whitespace/BOM for HTML detection
                header_stripped = header.lstrip(b' \t\n\r\xef\xbb\xbf')
                header_stripped_lower = header_stripped.lower()

                # Check for Excel file signatures
                if header.startswith(b'PK\x03\x04'):  # .xlsx files (ZIP format)
                    logger.info("✅ Detected .xlsx file (ZIP signature)")
                    return
                # .xls files (OLE2 format)
                elif header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                    logger.info("✅ Detected .xls file (OLE2 signature)")
                    return
                # Check for HTML content (case-insensitive, handles variations like <html xmlns=...)
                # Check both original and stripped versions
                elif (header_lower.startswith(b'<html') or header_lower.startswith(b'<!doctype') or
                      header_stripped_lower.startswith(b'<html') or header_stripped_lower.startswith(b'<!doctype')):
                    logger.error("❌ File appears to be HTML, not Excel")
                    raise HTTPException(
                        status_code=400,
                        detail="The uploaded file appears to be HTML content, not a valid Excel file. Please ensure you're uploading a proper Excel file (.xls or .xlsx)."
                    )
                elif header.startswith(b'%PDF'):
                    logger.error("❌ File appears to be PDF, not Excel")
                    raise HTTPException(
                        status_code=400,
                        detail="File appears to be a PDF, not a valid Excel file. Please upload an Excel file (.xls or .xlsx)."
                    )
                else:
                    logger.warning(f"⚠️ Unknown file signature: {header[:8]}")
                    # Don't raise error here, let pandas try to handle it

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Could not validate file header: {str(e)}")
            # Don't raise error here, let pandas try to handle it

    def process_csv_file(self, file_path: str, max_rows: int = 100) -> Dict[str, Any]:
        """Process CSV file and return preview data"""
        try:
            # Auto-detect delimiter by trying common delimiters
            delimiter = None
            best_columns = 0
            for test_delimiter in [',', ';', '\t', '|']:
                try:
                    test_df = pd.read_csv(file_path, nrows=1, sep=test_delimiter, encoding='utf-8')
                    if len(test_df.columns) > best_columns:
                        best_columns = len(test_df.columns)
                        delimiter = test_delimiter
                except:
                    continue

            if delimiter is None:
                delimiter = ','  # Default fallback

            logger.info(f"Detected CSV delimiter: '{delimiter}' with {best_columns} columns")

            # Read CSV file
            df = pd.read_csv(file_path, sep=delimiter, encoding='utf-8')

            # Get preview data
            preview_data = self._get_dataframe_preview(df, max_rows)

            return {
                "sheet_name": None,
                "preview_data": preview_data,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "preview_rows": min(max_rows, len(df))
            }

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing CSV file: {str(e)}")

    def _get_dataframe_preview(self, df: pd.DataFrame, max_rows: int) -> str:
        """Get preview data from DataFrame as JSON string"""
        # Get preview rows
        preview_df = df.head(max_rows)

        # Convert to list of dictionaries
        preview_data = []
        for index, row in preview_df.iterrows():
            row_dict = {}
            for col in df.columns:
                # Handle NaN values
                if pd.isna(row[col]):
                    row_dict[col] = None
                else:
                    row_dict[col] = str(row[col])
            preview_data.append(row_dict)

        return json.dumps(preview_data)

    def create_file_upload_record(self, db: Session, file_info: Dict[str, Any], user_id: int) -> FileUpload:
        """Create file upload record in database"""
        file_upload_data = FileUploadCreate(
            filename=file_info["filename"],
            original_filename=file_info["original_filename"],
            file_path=file_info["file_path"],
            file_size=file_info["file_size"],
            file_type=file_info["file_type"],
            mime_type=file_info["mime_type"],
            uploaded_by=user_id
        )

        db_file_upload = FileUpload(**file_upload_data.dict())
        db.add(db_file_upload)
        db.commit()
        db.refresh(db_file_upload)

        return db_file_upload

    def create_file_preview_records(self, db: Session, file_upload_id: int, previews: List[Dict[str, Any]]) -> List[FilePreview]:
        """Create file preview records in database"""
        preview_records = []

        for preview in previews:
            preview_data = FilePreviewCreate(
                file_upload_id=file_upload_id,
                sheet_name=preview["sheet_name"],
                preview_data=preview["preview_data"],
                total_rows=preview["total_rows"],
                total_columns=preview["total_columns"],
                preview_rows=preview["preview_rows"]
            )

            db_preview = FilePreview(**preview_data.dict())
            db.add(db_preview)
            preview_records.append(db_preview)

        db.commit()

        # Refresh all preview records
        for preview in preview_records:
            db.refresh(preview)

        return preview_records

    def get_file_upload(self, db: Session, file_id: int, user_id: int) -> FileUpload:
        """Get file upload by ID with user permission check"""
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id,
            FileUpload.uploaded_by == user_id
        ).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        return file_upload

    def get_user_files(self, db: Session, user_id: int, skip: int = 0, limit: int = 10) -> Tuple[List[FileUpload], int]:
        """Get user's uploaded files with pagination"""
        files = db.query(FileUpload).filter(
            FileUpload.uploaded_by == user_id
        ).order_by(FileUpload.created_at.desc()).offset(skip).limit(limit).all()

        total = db.query(FileUpload).filter(
            FileUpload.uploaded_by == user_id
        ).count()

        return files, total

    def delete_file(self, db: Session, file_id: int, user_id: int) -> bool:
        """Delete file upload, physical file, and all related data"""
        file_upload = self.get_file_upload(db, file_id, user_id)

        # Delete all related data first (due to foreign key constraints)
        # Use direct SQL queries to avoid SQLAlchemy relationship loading issues
        from sqlalchemy import text

        # Delete related park data (from both parks and parks_2b tables)
        from models.park import Park
        from models.park_2b import Park2B
        try:
            park_count = db.query(Park).filter(
                Park.file_upload_id == file_id).count()
            if park_count > 0:
                logger.info(
                    f"Deleting {park_count} park records related to file {file_id}")
                db.query(Park).filter(Park.file_upload_id == file_id).delete()
        except Exception as e:
            logger.warning(f"Error deleting park records: {e}")

        # Delete related parks_2b data
        try:
            park_2b_count = db.query(Park2B).filter(
                Park2B.file_upload_id == file_id).count()
            if park_2b_count > 0:
                logger.info(
                    f"Deleting {park_2b_count} parks_2b records related to file {file_id}")
                db.query(Park2B).filter(Park2B.file_upload_id == file_id).delete()
        except Exception as e:
            logger.warning(f"Error deleting parks_2b records: {e}")

        # Delete related creance aggregate views first (due to foreign key constraint)
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'creance_aggregate_views')"
            )).scalar()

            if result:
                creance_agg_count = db.execute(text(
                    "DELETE FROM creance_aggregate_views WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if creance_agg_count > 0:
                    logger.info(
                        f"Deleted {creance_agg_count} creance aggregate view records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting creance aggregate view records: {e}")

        # Delete related creance periodique records if table exists
        try:
            # Check if table exists first
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'creance_periodique_dot')"
            )).scalar()

            if result:
                # Table exists, delete records
                creance_count = db.execute(text(
                    "DELETE FROM creance_periodique_dot WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if creance_count > 0:
                    logger.info(
                        f"Deleted {creance_count} creance records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting creance records: {e}")

        # Delete related encaissement aggregate views first (due to foreign key constraint)
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'encaissement_aggregate_views')"
            )).scalar()

            if result:
                agg_views_count = db.execute(text(
                    "DELETE FROM encaissement_aggregate_views WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if agg_views_count > 0:
                    logger.info(
                        f"Deleted {agg_views_count} encaissement aggregate view records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting encaissement aggregate view records: {e}")

        # Delete related encaissement anomalies (due to foreign key constraint)
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'encaissement_anomalies')"
            )).scalar()

            if result:
                anomalies_count = db.execute(text(
                    "DELETE FROM encaissement_anomalies WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if anomalies_count > 0:
                    logger.info(
                        f"Deleted {anomalies_count} encaissement anomaly records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting encaissement anomaly records: {e}")

        # Delete related encaissement records if table exists
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'encaissement_ar_dot')"
            )).scalar()

            if result:
                encaissement_count = db.execute(text(
                    "DELETE FROM encaissement_ar_dot WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if encaissement_count > 0:
                    logger.info(
                        f"Deleted {encaissement_count} encaissement records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting encaissement records: {e}")

        # Delete related revenue journal records if table exists
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'revenue_journal')"
            )).scalar()

            if result:
                revenue_count = db.execute(text(
                    "DELETE FROM revenue_journal WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if revenue_count > 0:
                    logger.info(
                        f"Deleted {revenue_count} revenue journal records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting revenue journal records: {e}")

        # Delete related revenue objectives records if table exists
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'revenue_objectives')"
            )).scalar()

            if result:
                objectives_count = db.execute(text(
                    "DELETE FROM revenue_objectives WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if objectives_count > 0:
                    logger.info(
                        f"Deleted {objectives_count} revenue objectives records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting revenue objectives records: {e}")

        # Delete related account descriptions records if table exists
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'account_descriptions')"
            )).scalar()

            if result:
                account_desc_count = db.execute(text(
                    "DELETE FROM account_descriptions WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if account_desc_count > 0:
                    logger.info(
                        f"Deleted {account_desc_count} account descriptions records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting account descriptions records: {e}")

        # Delete related revenue anomalies records if table exists
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'revenue_anomalies')"
            )).scalar()

            if result:
                anomalies_count = db.execute(text(
                    "DELETE FROM revenue_anomalies WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if anomalies_count > 0:
                    logger.info(
                        f"Deleted {anomalies_count} revenue anomalies records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting revenue anomalies records: {e}")

        # Delete related revenue pivot cache records if table exists
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'revenue_pivot_cache')"
            )).scalar()

            if result:
                pivot_cache_count = db.execute(text(
                    "DELETE FROM revenue_pivot_cache WHERE file_upload_id = :file_id RETURNING id"
                ), {"file_id": file_id}).rowcount
                if pivot_cache_count > 0:
                    logger.info(
                        f"Deleted {pivot_cache_count} revenue pivot cache records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting revenue pivot cache records: {e}")

        # Delete file_previews first (foreign key constraint)
        try:
            preview_count = db.execute(text(
                "DELETE FROM file_previews WHERE file_upload_id = :file_id RETURNING id"
            ), {"file_id": file_id}).rowcount
            if preview_count > 0:
                logger.info(
                    f"Deleted {preview_count} preview records related to file {file_id}")
        except Exception as e:
            logger.warning(f"Error deleting file previews: {e}")

        # Delete physical file with Windows file locking handling
        if os.path.exists(file_upload.file_path):
            self._safe_delete_file(file_upload.file_path)

        # Delete from database
        # Use expunge to avoid triggering relationship loads
        db.expunge(file_upload)
        db.execute(text("DELETE FROM file_uploads WHERE id = :file_id"), {"file_id": file_id})
        db.commit()

        logger.info(
            f"Successfully deleted file {file_id} and all related records")
        return True

    def _safe_delete_file(self, file_path: str) -> bool:
        """Safely delete a file, handling Windows file locking issues"""
        import time
        import gc

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Force garbage collection to release any file handles
                gc.collect()

                # Try to delete the file
                os.remove(file_path)
                logger.info(f"Successfully deleted file: {file_path}")
                return True

            except PermissionError as e:
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"File deletion attempt {attempt + 1} failed (PermissionError): {e}")
                    logger.info(f"Retrying file deletion in 1 second...")
                    time.sleep(1)
                    continue
                else:
                    logger.error(
                        f"Failed to delete file after {max_attempts} attempts: {e}")
                    # Try to rename the file instead of deleting it
                    try:
                        import tempfile
                        temp_dir = tempfile.gettempdir()
                        temp_name = f"deleted_{os.path.basename(file_path)}_{int(time.time())}"
                        temp_path = os.path.join(temp_dir, temp_name)
                        os.rename(file_path, temp_path)
                        logger.info(f"Renamed locked file to: {temp_path}")
                        return True
                    except Exception as rename_error:
                        logger.error(
                            f"Failed to rename locked file: {rename_error}")
                        raise e

            except OSError as e:
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"File deletion attempt {attempt + 1} failed (OSError): {e}")
                    logger.info(f"Retrying file deletion in 1 second...")
                    time.sleep(1)
                    continue
                else:
                    logger.error(
                        f"Failed to delete file after {max_attempts} attempts: {e}")
                    raise e

            except Exception as e:
                logger.error(f"Unexpected error deleting file: {e}")
                raise e

        return False

    def _find_header_row_in_table(self, df_sample: pd.DataFrame) -> Optional[int]:
        """
        Search first 20 rows to find the header row containing known file type headers

        Args:
            df_sample: DataFrame with table data (header=None)

        Returns:
            Row index (0-based) where headers are found, or None if not found
        """
        # Define key headers for different file types
        # These should be distinctive enough to avoid false positives
        header_sets = {
            'revenue_journal': [
                'org name', 'date gl', 'cpt comptable',
                'prix uni', 'mnt ht', 'mnt tax', 'mnt ttc',
                'chiffre aff exe dzd', 'n fact'
            ],
            'parc_corporate': [
                'actel code', 'actel', 'customer level',
                'telecom type', 'primary offer', 'subscriber status',
                'offer type', 'price plan', 'activation date'
            ],
            'encaissement': [
                'organisation', 'encaissement', 'montant ht',
                'montant ttc', 'date fact'
            ],
            'creance': [
                'organisation', 'creance', 'montant', 'date'
            ]
        }

        best_row = None
        best_match_count = 0
        best_file_type = None

        # Search through first 20 rows
        for row_idx in range(min(20, len(df_sample))):
            row_values = df_sample.iloc[row_idx].astype(str).str.lower().str.strip()

            # Log first few rows for debugging
            if row_idx < 5:
                logger.debug(f"Row {row_idx}: {list(row_values[:5])}")

            # Try each header set
            for file_type, key_headers in header_sets.items():
                # Count how many key headers are present in this row
                match_count = 0
                matched_headers = []

                for header in key_headers:
                    for cell_value in row_values:
                        # Normalize cell value
                        cell_normalized = ''.join(c if c.isalnum() or c == ' ' else ' ' for c in cell_value)
                        cell_normalized = ' '.join(cell_normalized.split())

                        # More strict matching to avoid false positives:
                        # 1. For multi-word headers, require most words to match
                        # 2. Avoid matching very short words unless they're exact
                        header_words = header.split()

                        if len(header_words) == 1:
                            # Single word: require exact match or cell starts/ends with it
                            # and cell is not too long (to avoid matching "actel" in "Actel Code_Code d'actel")
                            if (cell_normalized == header or
                                (header in cell_normalized and len(cell_normalized) <= len(header) + 10)):
                                match_count += 1
                                matched_headers.append(header)
                                break
                        else:
                            # Multi-word: require at least half the words to match
                            words_matched = sum(1 for word in header_words if word in cell_normalized)
                            if words_matched >= len(header_words) / 2:
                                match_count += 1
                                matched_headers.append(header)
                                break

                # If this row has more matches, it's likely the header row
                if match_count > best_match_count:
                    best_match_count = match_count
                    best_row = row_idx
                    best_file_type = file_type
                    logger.debug(f"  Row {row_idx} - {file_type}: {match_count} matches ({matched_headers[:3]})")

        # Require at least 4 matching headers to consider it valid
        if best_match_count >= 4:
            logger.info(f"🎯 Found {best_file_type} header row at index {best_row} with {best_match_count} matching headers")
            return best_row
        else:
            logger.warning(f"⚠️ No clear header row found in first 20 rows (best match: {best_match_count} headers)")
            return None

    def get_file_previews(self, db: Session, file_id: int, user_id: int) -> List[FilePreview]:
        """Get file previews for a specific file"""
        file_upload = self.get_file_upload(db, file_id, user_id)

        return db.query(FilePreview).filter(
            FilePreview.file_upload_id == file_id
        ).all()

    def update_processing_status(self, db: Session, file_id: int, status: str, error_message: Optional[str] = None) -> FileUpload:
        """Update file processing status"""
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        file_upload.processing_status = status
        file_upload.is_processed = status == "completed"

        if error_message:
            file_upload.error_message = error_message

        db.commit()
        db.refresh(file_upload)

        return file_upload

    def get_all_files(self, db: Session, skip: int = 0, limit: int = 10) -> Tuple[List[FileUpload], int]:
        """Get all files with pagination (Admin only)"""
        files = db.query(FileUpload).order_by(
            FileUpload.created_at.desc()).offset(skip).limit(limit).all()

        total = db.query(FileUpload).count()

        return files, total

    def admin_delete_file(self, db: Session, file_id: int) -> bool:
        """Delete any file (Admin only)"""
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == file_id).first()

        if not file_upload:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete physical file
        if os.path.exists(file_upload.file_path):
            os.remove(file_upload.file_path)

        # Delete from database
        db.delete(file_upload)
        db.commit()

        return True

    def get_files_paginated(self, db: Session, user_id: int, page: int = 1, page_size: int = 25,
                            search: Optional[str] = None, file_type: Optional[str] = None) -> Dict[str, Any]:
        """Get files with pagination and filtering"""
        from models.file_upload import FileListResponse, FileUploadResponse

        # Calculate offset
        offset = (page - 1) * page_size

        # Build query
        query = db.query(FileUpload)

        # Apply filters
        if search:
            query = query.filter(
                FileUpload.original_filename.ilike(f"%{search}%")
            )

        if file_type:
            query = query.filter(FileUpload.file_type == file_type)

        # Get total count
        total = query.count()

        # Get paginated results
        files = query.order_by(FileUpload.created_at.desc()).offset(
            offset).limit(page_size).all()

        # Convert to response models
        file_responses = [FileUploadResponse.from_orm(file) for file in files]

        return {
            "files": file_responses,
            "total": total,
            "page": page,
            "per_page": page_size
        }

    def get_file_with_previews(self, db: Session, file_id: int, user_id: int):
        """Get file with all previews"""
        from models.file_upload import FileUploadWithPreviews, FileUploadResponse, FilePreviewResponse

        # Get file upload
        file_upload = self.get_file_upload(db, file_id, user_id)

        # Get file previews
        previews = self.get_file_previews(db, file_id, user_id)

        # Convert to response models
        file_response = FileUploadResponse.from_orm(file_upload)
        preview_responses = [FilePreviewResponse.from_orm(
            preview) for preview in previews]

        # Create file with previews response
        file_with_previews = FileUploadWithPreviews(
            **file_response.dict(),
            file_previews=preview_responses
        )

        return file_with_previews

    def get_files_by_user(self, db: Session, user_id: int, page: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """Get files by specific user with pagination"""
        from models.file_upload import FileListResponse, FileUploadResponse

        # Calculate offset
        offset = (page - 1) * page_size

        # Build query for specific user
        query = db.query(FileUpload).filter(FileUpload.uploaded_by == user_id)

        # Get total count
        total = query.count()

        # Get paginated results
        files = query.order_by(FileUpload.created_at.desc()).offset(
            offset).limit(page_size).all()

        # Convert to response models
        file_responses = [FileUploadResponse.from_orm(file) for file in files]

        return {
            "files": file_responses,
            "total": total,
            "page": page,
            "per_page": page_size
        }

    def get_file_with_previews(self, db: Session, file_id: int, user_id: int):
        """Get file with all previews"""
        from models.file_upload import FileUploadWithPreviews, FileUploadResponse, FilePreviewResponse

        # Get file upload
        file_upload = self.get_file_upload(db, file_id, user_id)

        # Get file previews
        previews = self.get_file_previews(db, file_id, user_id)

        # Convert to response models
        file_response = FileUploadResponse.from_orm(file_upload)
        preview_responses = [FilePreviewResponse.from_orm(
            preview) for preview in previews]

        # Create file with previews response
        file_with_previews = FileUploadWithPreviews(
            **file_response.dict(),
            file_previews=preview_responses
        )

        return file_with_previews

    async def generate_file_preview(self, db: Session, file_upload: FileUpload, preview_request, user_id: int):
        """Generate file preview and save to database"""
        from models.file_upload import FilePreviewResponse, FilePreviewRequest

        try:
            logger.info(
                f"Starting preview generation for file {file_upload.id} ({file_upload.file_type})")
            logger.info(f"File path: {file_upload.file_path}")
            logger.info(f"Max rows requested: {preview_request.max_rows}")

            # Process file based on type
            if file_upload.file_type == "excel":
                logger.info("Processing Excel file for preview")
                previews_data = self.process_excel_file(
                    file_upload.file_path, preview_request.max_rows)
            elif file_upload.file_type == "csv":
                logger.info("Processing CSV file for preview")
                previews_data = self.process_csv_file(
                    file_upload.file_path, preview_request.max_rows)
            else:
                raise HTTPException(
                    status_code=400, detail="Unsupported file type for preview")

            logger.info(
                f"File processing completed. Generated {len(previews_data)} preview data entries")

            # Create preview records in database
            logger.info("Creating preview records in database")
            preview_records = self.create_file_preview_records(
                db, file_upload.id, previews_data)

            logger.info(f"Created {len(preview_records)} preview records")

            # Convert to response models
            preview_responses = [FilePreviewResponse.from_orm(
                preview) for preview in preview_records]

            logger.info(
                f"Preview generation completed successfully for file {file_upload.id}")
            return preview_responses

        except Exception as e:
            logger.error(
                f"Error generating preview for file {file_upload.id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Error generating preview: {str(e)}")

    def process_csv_file(self, file_path: str, max_rows: int = 100) -> List[Dict[str, Any]]:
        """Process CSV file and return preview data"""
        try:
            logger.info(
                f"Processing CSV file: {file_path} with max_rows: {max_rows}")

            # Auto-detect delimiter by trying common delimiters with multiple encodings
            delimiter = None
            best_columns = 0
            best_encoding = 'utf-8'
            
            # Try different encodings (French CSV files often use latin-1 or cp1252)
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                for test_delimiter in [';', ',', '\t', '|']:  # Prioritize ';' for French CSV
                    try:
                        # Read first 5 rows to better detect delimiter and validate
                        test_df = pd.read_csv(
                            file_path, 
                            nrows=5, 
                            sep=test_delimiter, 
                            encoding=encoding,
                            header=0,
                            on_bad_lines='skip',
                            low_memory=False
                        )
                        # Count columns with actual data (not all NaN in first 5 rows)
                        non_empty_cols = test_df.notna().any(axis=0).sum()
                        total_cols = len(test_df.columns)
                        
                        # Prefer delimiters that give us more columns with data
                        # Also check if we have reasonable number of columns (not just 1)
                        if non_empty_cols > best_columns and total_cols > 1:
                            best_columns = non_empty_cols
                            delimiter = test_delimiter
                            best_encoding = encoding
                            logger.info(f"  Better delimiter found: '{delimiter}' with {total_cols} columns ({non_empty_cols} with data), encoding: {encoding}")
                    except Exception as e:
                        logger.debug(f"  Failed to test delimiter '{test_delimiter}' with encoding {encoding}: {e}")
                        continue

            if delimiter is None:
                # Try semicolon as default for French CSV files
                delimiter = ';'
                best_encoding = 'utf-8'
                logger.warning(f"Could not detect delimiter reliably, defaulting to ';'")
                try:
                    # Verify semicolon works
                    test_df = pd.read_csv(file_path, nrows=5, sep=';', encoding='utf-8', on_bad_lines='skip')
                    if len(test_df.columns) > 1:
                        logger.info(f"✅ Semicolon delimiter works: {len(test_df.columns)} columns")
                    else:
                        # Fallback to comma
                        delimiter = ','
                        logger.warning(f"Semicolon failed, trying comma")
                except Exception as e:
                    logger.warning(f"Semicolon failed: {e}, trying comma")
                    delimiter = ','

            logger.info(f"✅ Detected CSV delimiter: '{delimiter}' with {best_columns} columns (encoding: {best_encoding})")

            # Read only a limited number of rows for preview to handle large files
            # Read 2x for better sampling
            df = pd.read_csv(
                file_path, 
                nrows=max_rows * 2, 
                sep=delimiter, 
                encoding=best_encoding,
                header=0,
                on_bad_lines='skip',
                low_memory=False
            )

            logger.info(
                f"CSV file loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # Log first few column names for debugging
            if len(df.columns) > 0:
                logger.info(f"  First 10 columns: {list(df.columns[:10])}")
                logger.info(f"  All columns: {list(df.columns)}")
            
            # Clean column names (remove leading/trailing spaces, newlines, etc.)
            df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', ' ')
            
            # Check if we have reasonable number of columns
            if len(df.columns) == 1:
                logger.warning(f"⚠️ Only 1 column detected! CSV might not be parsed correctly. First row sample: {df.iloc[0, 0] if len(df) > 0 else 'N/A'}")
                # Try to re-read with semicolon if we only got 1 column
                if delimiter != ';':
                    logger.info(f"  Retrying with semicolon delimiter...")
                    try:
                        df_retry = pd.read_csv(
                            file_path, 
                            nrows=max_rows * 2, 
                            sep=';', 
                            encoding=best_encoding,
                            header=0,
                            on_bad_lines='skip',
                            low_memory=False
                        )
                        if len(df_retry.columns) > len(df.columns):
                            logger.info(f"  ✅ Semicolon works better: {len(df_retry.columns)} columns")
                            df = df_retry
                            df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', ' ')
                            delimiter = ';'
                    except Exception as e:
                        logger.warning(f"  Retry with semicolon failed: {e}")

            # Get preview data
            preview_data = self._get_dataframe_preview(df, max_rows)

            # Count total rows efficiently without loading entire file
            total_rows = 0
            try:
                with open(file_path, 'r', encoding=best_encoding) as f:
                    total_rows = sum(1 for line in f) - 1  # Subtract header
            except Exception as e:
                logger.warning(f"Could not count total rows: {str(e)}")
                total_rows = len(df)  # Fallback to loaded rows

            logger.info(
                f"CSV processing completed. Total rows: {total_rows}, Preview rows: {len(df)}")

            return [{
                "sheet_name": None,  # CSV files don't have sheet names
                "preview_data": preview_data,
                "total_rows": total_rows,
                "total_columns": len(df.columns),
                "preview_rows": min(max_rows, len(df))
            }]

        except Exception as e:
            logger.error(f"Error processing CSV file {file_path}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error processing CSV file: {str(e)}")

    def get_preview_data(self, db: Session, preview_id: int, user_id: int, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get preview data content for a specific preview with pagination"""
        # First check if the preview exists and user has access
        preview = db.query(FilePreview).filter(
            FilePreview.id == preview_id).first()

        if not preview:
            raise HTTPException(status_code=404, detail="Preview not found")

        # Check if user has access to the file
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == preview.file_upload_id,
            FileUpload.uploaded_by == user_id
        ).first()

        if not file_upload:
            raise HTTPException(
                status_code=403, detail="Access denied to this preview")

        # Parse the preview data JSON
        try:
            import json
            parsed_data = json.loads(preview.preview_data)

            # Apply pagination
            total_items = len(parsed_data)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_data = parsed_data[start_idx:end_idx]

            return {
                "preview_id": preview.id,
                "file_upload_id": preview.file_upload_id,
                "sheet_name": preview.sheet_name,
                "data": paginated_data,  # Paginated array that frontend expects
                "total_rows": preview.total_rows,
                "total_columns": preview.total_columns,
                "preview_rows": preview.preview_rows,
                "created_at": preview.created_at,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_items": total_items,
                    "total_pages": (total_items + per_page - 1) // per_page,
                    "has_next": end_idx < total_items,
                    "has_prev": page > 1
                }
            }
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error parsing preview data: {str(e)}"
            )

    def delete_file_preview(self, db: Session, preview_id: int, user_id: int) -> bool:
        """Delete a file preview"""
        # First check if the preview exists and user has access
        preview = db.query(FilePreview).filter(
            FilePreview.id == preview_id).first()

        if not preview:
            raise HTTPException(status_code=404, detail="Preview not found")

        # Check if user has access to the file
        file_upload = db.query(FileUpload).filter(
            FileUpload.id == preview.file_upload_id,
            FileUpload.uploaded_by == user_id
        ).first()

        if not file_upload:
            raise HTTPException(
                status_code=403, detail="Access denied to this preview")

        # Delete the preview
        db.delete(preview)
        db.commit()

        logger.info(f"Preview {preview_id} deleted by user {user_id}")
        return True
