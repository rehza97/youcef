import os
import json
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models.file_upload import FileUpload, FilePreview, FileUploadCreate, FilePreviewCreate
from models.user import User
import mimetypes


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

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if hasattr(file, 'size') and file.size > max_size:
            raise HTTPException(
                status_code=400, detail="File too large. Maximum size is 50MB")

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

    def process_excel_file(self, file_path: str, max_rows: int = 10) -> List[Dict[str, Any]]:
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

    def process_csv_file(self, file_path: str, max_rows: int = 10) -> Dict[str, Any]:
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
        """Delete file upload and physical file"""
        file_upload = self.get_file_upload(db, file_id, user_id)

        # Delete physical file
        if os.path.exists(file_upload.file_path):
            os.remove(file_upload.file_path)

        # Delete from database
        db.delete(file_upload)
        db.commit()

        return True

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
