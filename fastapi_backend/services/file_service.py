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
            processing_status="pending"
        )

        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # Automatically generate preview after file upload
        try:
            if file_type in ['excel', 'csv']:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Generating preview for file {file_upload.id} of type {file_type}")

                # Create a default preview request
                class DefaultPreviewRequest:
                    def __init__(self):
                        self.max_rows = 100  # Show more rows in preview by default

                preview_request = DefaultPreviewRequest()
                previews = await self.generate_file_preview(db, file_upload, preview_request, user_id)
                logger.info(
                    f"Generated {len(previews)} previews for file {file_upload.id}")
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Skipping preview generation for file {file_upload.id} of type {file_type}")
        except Exception as e:
            # Log error but don't fail the upload
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to generate preview for file {file_upload.id}: {str(e)}")

        return file_upload

    def process_excel_file(self, file_path: str, max_rows: int = 100) -> List[Dict[str, Any]]:
        """Process Excel file and return preview data"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            previews = []

            for sheet_name in sheet_names:
                # Read sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)

                # Get preview data
                preview_data = self._get_dataframe_preview(df, max_rows)

                previews.append({
                    "sheet_name": sheet_name,
                    "preview_data": preview_data,
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "preview_rows": min(max_rows, len(df))
                })

            return previews

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing Excel file: {str(e)}")

    def process_csv_file(self, file_path: str, max_rows: int = 100) -> Dict[str, Any]:
        """Process CSV file and return preview data"""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)

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
        """Delete file upload, physical file, and all related park data"""
        file_upload = self.get_file_upload(db, file_id, user_id)

        # Delete all related park data first (due to foreign key constraint)
        from models.park import Park
        park_count = db.query(Park).filter(
            Park.file_upload_id == file_id).count()
        if park_count > 0:
            logger.info(
                f"Deleting {park_count} park records related to file {file_id}")
            db.query(Park).filter(Park.file_upload_id == file_id).delete()

        # Delete physical file with Windows file locking handling
        if os.path.exists(file_upload.file_path):
            self._safe_delete_file(file_upload.file_path)

        # Delete from database (this will also delete file_previews due to cascade)
        db.delete(file_upload)
        db.commit()

        logger.info(
            f"Successfully deleted file {file_id} and {park_count} related park records")
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
            # Process file based on type
            if file_upload.file_type == "excel":
                previews_data = self.process_excel_file(
                    file_upload.file_path, preview_request.max_rows)
            elif file_upload.file_type == "csv":
                previews_data = self.process_csv_file(
                    file_upload.file_path, preview_request.max_rows)
            else:
                raise HTTPException(
                    status_code=400, detail="Unsupported file type for preview")

            # Create preview records in database
            preview_records = self.create_file_preview_records(
                db, file_upload.id, previews_data)

            # Convert to response models
            preview_responses = [FilePreviewResponse.from_orm(
                preview) for preview in preview_records]

            return preview_responses

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating preview: {str(e)}")

    def process_csv_file(self, file_path: str, max_rows: int = 100) -> List[Dict[str, Any]]:
        """Process CSV file and return preview data"""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)

            # Get preview data
            preview_data = self._get_dataframe_preview(df, max_rows)

            return [{
                "sheet_name": None,  # CSV files don't have sheet names
                "preview_data": preview_data,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "preview_rows": min(max_rows, len(df))
            }]

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing CSV file: {str(e)}")

    def get_preview_data(self, db: Session, preview_id: int, user_id: int) -> Dict[str, Any]:
        """Get preview data content for a specific preview"""
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
            return {
                "preview_id": preview.id,
                "file_upload_id": preview.file_upload_id,
                "sheet_name": preview.sheet_name,
                "data": parsed_data,  # This is the array that frontend expects
                "total_rows": preview.total_rows,
                "total_columns": preview.total_columns,
                "preview_rows": preview.preview_rows,
                "created_at": preview.created_at
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
