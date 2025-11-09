from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.connection import Base


class FileUpload(Base):
    """File upload model for storing file metadata"""
    __tablename__ = "file_uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)  # 'excel', 'csv', etc.
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_processed = Column(Boolean, default=False)
    # pending, processing, completed, failed
    processing_status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    # JSON string for additional metadata
    file_metadata = Column(Text, nullable=True)
    # Detected KPI type (parc_corporate_ngbss, chiffre_affaires, encaissement, creance_periodique, unknown)
    detected_kpi_type = Column(String(100), nullable=True)
    # Detection confidence score (0-100)
    detection_confidence = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="file_uploads")
    file_previews = relationship(
        "FilePreview", back_populates="file_upload", cascade="all, delete-orphan")
    parks = relationship("Park", back_populates="file_upload",
                         cascade="all, delete-orphan")
    revenue_journals = relationship("RevenueJournal", back_populates="file_upload",
                                    cascade="all, delete-orphan")
    account_descriptions = relationship("AccountDescription", back_populates="file_upload",
                                        cascade="all, delete-orphan")
    revenue_objectives = relationship("RevenueObjective", back_populates="file_upload",
                                      cascade="all, delete-orphan")
    revenue_anomalies = relationship("RevenueAnomaly", back_populates="file_upload",
                                     cascade="all, delete-orphan")
    encaissement_ar_records = relationship("EncaissementARDot", back_populates="file_upload",
                                          cascade="all, delete-orphan")
    encaissement_anomaly_records = relationship("EncaissementAnomaly", back_populates="file_upload",
                                                cascade="all, delete-orphan")
    encaissement_aggregate_views = relationship("EncaissementAggregateView", back_populates="file_upload",
                                                cascade="all, delete-orphan")
    creance_periodique_records = relationship("CreancePeriodiqueDot", back_populates="file_upload",
                                              cascade="all, delete-orphan")
    creance_aggregate_views = relationship("CreanceAggregateView", back_populates="file_upload",
                                           cascade="all, delete-orphan")


class FilePreview(Base):
    """File preview model for storing preview data"""
    __tablename__ = "file_previews"

    id = Column(Integer, primary_key=True, index=True)
    file_upload_id = Column(Integer, ForeignKey(
        "file_uploads.id"), nullable=False)
    sheet_name = Column(String(255), nullable=True)  # For Excel files
    preview_data = Column(Text, nullable=False)  # JSON string of preview data
    total_rows = Column(Integer, nullable=False)
    total_columns = Column(Integer, nullable=False)
    preview_rows = Column(Integer, nullable=False)  # Number of rows in preview
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file_upload = relationship("FileUpload", back_populates="file_previews")


# Pydantic schemas
class FileUploadBase(BaseModel):
    filename: str = Field(..., description="Generated filename")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File type (excel, csv)")
    mime_type: str = Field(..., description="MIME type")


class FileUploadCreate(FileUploadBase):
    file_path: str = Field(..., description="File storage path")
    uploaded_by: int = Field(..., description="User ID who uploaded the file")


class FileUploadUpdate(BaseModel):
    """Update model for file upload"""
    original_filename: Optional[str] = Field(
        None, description="Original filename")
    file_metadata: Optional[str] = Field(
        None, description="Additional metadata")
    is_processed: Optional[bool] = Field(None, description="Processing status")
    processing_status: Optional[str] = Field(
        None, description="Processing status")


class FileUploadResponse(FileUploadBase):
    id: int
    uploaded_by: int
    is_processed: bool
    processing_status: str
    error_message: Optional[str] = None
    file_metadata: Optional[str] = None
    detected_kpi_type: Optional[str] = None
    detection_confidence: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FilePreviewBase(BaseModel):
    sheet_name: Optional[str] = Field(
        None, description="Sheet name for Excel files")
    preview_data: str = Field(..., description="JSON string of preview data")
    total_rows: int = Field(..., description="Total number of rows in file")
    total_columns: int = Field(...,
                               description="Total number of columns in file")
    preview_rows: int = Field(..., description="Number of rows in preview")


class FilePreviewCreate(FilePreviewBase):
    file_upload_id: int = Field(..., description="File upload ID")


class FilePreviewResponse(FilePreviewBase):
    id: int
    file_upload_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FileUploadWithPreviews(FileUploadResponse):
    file_previews: List[FilePreviewResponse] = []


class FileUploadRequest(BaseModel):
    """Request model for file upload"""
    pass  # File will be sent as multipart/form-data


class FilePreviewRequest(BaseModel):
    """Request model for file preview"""
    max_rows: int = Field(
        default=100, description="Maximum number of rows to preview")
    sheet_name: Optional[str] = Field(
        None, description="Sheet name for Excel files")


class FileProcessingStatus(BaseModel):
    """Response model for file processing status"""
    file_id: int
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None


class FileListResponse(BaseModel):
    """Response model for file list"""
    files: List[FileUploadResponse]
    total: int
    page: int
    per_page: int


class FilePreviewListResponse(BaseModel):
    """Response model for file preview list"""
    data: List[FilePreviewResponse]
    total: int
