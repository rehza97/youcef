# File Upload and Preview Documentation

This document provides comprehensive information about the file upload and preview functionality for Excel and CSV files in the FastAPI backend.

## 📋 Overview

The file upload system provides comprehensive functionality for:

- ✅ **Excel file upload and preview** (`.xlsx`, `.xls`)
- ✅ **CSV file upload and preview** (`.csv`)
- ✅ **Multi-sheet Excel support** with individual sheet previews
- ✅ **File management** (upload, download, delete, list)
- ✅ **Preview generation** with customizable row limits
- ✅ **Processing status tracking** (pending, processing, completed, failed)
- ✅ **File statistics** and user-specific file management
- ✅ **Security** with user-based access control

## 🏗️ Architecture

### Database Models

#### FileUpload Model

```python
class FileUpload(Base):
    __tablename__ = "file_uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)  # Generated unique filename
    original_filename = Column(String(255), nullable=False)  # Original filename
    file_path = Column(String(500), nullable=False)  # Storage path
    file_size = Column(Integer, nullable=False)  # File size in bytes
    file_type = Column(String(50), nullable=False)  # 'excel' or 'csv'
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### FilePreview Model

```python
class FilePreview(Base):
    __tablename__ = "file_previews"

    id = Column(Integer, primary_key=True, index=True)
    file_upload_id = Column(Integer, ForeignKey("file_uploads.id"), nullable=False)
    sheet_name = Column(String(255), nullable=True)  # For Excel sheets
    preview_data = Column(Text, nullable=False)  # JSON string of preview data
    total_rows = Column(Integer, nullable=False)
    total_columns = Column(Integer, nullable=False)
    preview_rows = Column(Integer, nullable=False)  # Number of rows in preview
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### File Storage Structure

```
uploads/
├── excel/          # Excel files (.xlsx, .xls)
├── csv/           # CSV files (.csv)
└── temp/          # Temporary files
```

## 🔧 API Endpoints

### File Upload

#### `POST /api/files/upload`

Upload Excel or CSV file with automatic processing and preview generation.

**Request:**

- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: File upload with field name `file`

**Response:**

```json
{
  "id": 1,
  "filename": "uuid-generated-filename.xlsx",
  "original_filename": "data.xlsx",
  "file_size": 24576,
  "file_type": "excel",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "uploaded_by": 1,
  "is_processed": true,
  "processing_status": "completed",
  "error_message": null,
  "metadata": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:05Z"
}
```

### File Management

#### `GET /api/files/`

Get user's uploaded files with pagination.

**Query Parameters:**

- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 10, max: 100)

**Response:**

```json
{
  "files": [
    {
      "id": 1,
      "filename": "uuid-generated-filename.xlsx",
      "original_filename": "data.xlsx",
      "file_size": 24576,
      "file_type": "excel",
      "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "uploaded_by": 1,
      "is_processed": true,
      "processing_status": "completed",
      "error_message": null,
      "metadata": null,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:05Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10
}
```

#### `GET /api/files/{file_id}`

Get file details with all previews.

**Response:**

```json
{
  "id": 1,
  "filename": "uuid-generated-filename.xlsx",
  "original_filename": "data.xlsx",
  "file_size": 24576,
  "file_type": "excel",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "uploaded_by": 1,
  "is_processed": true,
  "processing_status": "completed",
  "error_message": null,
  "metadata": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:05Z",
  "file_previews": [
    {
      "id": 1,
      "file_upload_id": 1,
      "sheet_name": "Sheet1",
      "preview_data": "[{\"Name\":\"John Doe\",\"Age\":\"30\",\"Email\":\"john@example.com\"}]",
      "total_rows": 100,
      "total_columns": 5,
      "preview_rows": 10,
      "created_at": "2024-01-15T10:30:05Z"
    }
  ]
}
```

### File Preview

#### `GET /api/files/{file_id}/previews`

Get all previews for a specific file.

**Response:**

```json
[
  {
    "id": 1,
    "file_upload_id": 1,
    "sheet_name": "Sheet1",
    "preview_data": "[{\"Name\":\"John Doe\",\"Age\":\"30\",\"Email\":\"john@example.com\"}]",
    "total_rows": 100,
    "total_columns": 5,
    "preview_rows": 10,
    "created_at": "2024-01-15T10:30:05Z"
  }
]
```

#### `POST /api/files/{file_id}/preview`

Generate new preview with custom parameters.

**Request:**

```json
{
  "max_rows": 5,
  "sheet_name": "Sheet1" // Optional, for Excel files
}
```

**Response:**

```json
[
  {
    "id": 2,
    "file_upload_id": 1,
    "sheet_name": "Sheet1",
    "preview_data": "[{\"Name\":\"John Doe\",\"Age\":\"30\"}]",
    "total_rows": 100,
    "total_columns": 5,
    "preview_rows": 5,
    "created_at": "2024-01-15T10:35:00Z"
  }
]
```

### File Status

#### `GET /api/files/{file_id}/status`

Get file processing status.

**Response:**

```json
{
  "file_id": 1,
  "status": "completed",
  "progress": null,
  "message": null,
  "error": null
}
```

### File Download

#### `GET /api/files/{file_id}/download`

Download the original file.

**Response:**

- File download with original filename and MIME type

### File Statistics

#### `GET /api/files/stats/summary`

Get file upload statistics for current user.

**Response:**

```json
{
  "total_files": 5,
  "excel_files": 3,
  "csv_files": 2,
  "total_size_bytes": 1048576,
  "total_size_mb": 1.0,
  "pending_files": 0,
  "completed_files": 4,
  "failed_files": 1
}
```

### File Deletion

#### `DELETE /api/files/{file_id}`

Delete uploaded file and all associated previews.

**Response:**

```json
{
  "message": "File deleted successfully"
}
```

## 🔍 File Processing

### Supported File Types

#### Excel Files

- **Extensions**: `.xlsx`, `.xls`
- **MIME Types**:
  - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - `application/vnd.ms-excel`
- **Features**:
  - Multi-sheet support
  - Individual sheet previews
  - Sheet-specific preview generation

#### CSV Files

- **Extensions**: `.csv`
- **MIME Types**: `text/csv`, `application/csv`
- **Features**:
  - Single file preview
  - Configurable preview rows

### Processing Workflow

1. **File Upload**

   - Validate file type and size
   - Generate unique filename
   - Save to appropriate directory
   - Create database record

2. **File Processing**

   - Update status to "processing"
   - Read file content using pandas
   - Generate preview data
   - Create preview records
   - Update status to "completed"

3. **Error Handling**
   - Update status to "failed"
   - Store error message
   - Clean up temporary files

### Preview Data Format

Preview data is stored as JSON string containing array of objects:

```json
[
  {
    "Name": "John Doe",
    "Age": "30",
    "Email": "john@example.com",
    "Department": "IT",
    "Salary": "75000"
  },
  {
    "Name": "Jane Smith",
    "Age": "25",
    "Email": "jane@example.com",
    "Department": "HR",
    "Salary": "65000"
  }
]
```

## 🛡️ Security Features

### Access Control

- **User-based access**: Users can only access their own files
- **Authentication required**: All endpoints require valid JWT token
- **File ownership validation**: Prevents unauthorized access

### File Validation

- **File type validation**: Only Excel and CSV files allowed
- **File size limits**: Maximum 50MB per file
- **Filename sanitization**: Prevents path traversal attacks

### Storage Security

- **Unique filenames**: UUID-based naming prevents conflicts
- **Separate directories**: Different file types stored separately
- **Temporary file cleanup**: Automatic cleanup of temporary files

## 📊 Error Handling

### Common Error Responses

#### 400 Bad Request

```json
{
  "detail": "Unsupported file type. Only Excel and CSV files are supported."
}
```

#### 404 Not Found

```json
{
  "detail": "File not found"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Error processing file: Invalid file format"
}
```

### Processing Status Values

- `pending`: File uploaded, processing not started
- `processing`: File is being processed
- `completed`: File processed successfully
- `failed`: File processing failed

## 🚀 Usage Examples

### Upload Excel File

```python
import requests

# Login to get token
login_response = requests.post("http://127.0.0.1:8000/api/auth/login", json={
    "username": "admin",
    "password": "admin"
})
token = login_response.json()["access_token"]

# Upload Excel file
headers = {"Authorization": f"Bearer {token}"}
with open("data.xlsx", "rb") as f:
    files = {"file": ("data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = requests.post("http://127.0.0.1:8000/api/files/upload", headers=headers, files=files)

file_id = response.json()["id"]
print(f"File uploaded with ID: {file_id}")
```

### Get File Previews

```python
# Get file details with previews
response = requests.get(f"http://127.0.0.1:8000/api/files/{file_id}", headers=headers)
file_data = response.json()

for preview in file_data["file_previews"]:
    print(f"Sheet: {preview['sheet_name']}")
    print(f"Total rows: {preview['total_rows']}")
    print(f"Preview rows: {preview['preview_rows']}")

    # Parse preview data
    import json
    preview_rows = json.loads(preview["preview_data"])
    for row in preview_rows:
        print(row)
```

### Generate New Preview

```python
# Generate new preview with custom parameters
preview_request = {
    "max_rows": 5,
    "sheet_name": "Sheet1"  # For Excel files
}
response = requests.post(f"http://127.0.0.1:8000/api/files/{file_id}/preview",
                       json=preview_request, headers=headers)
```

## 🧪 Testing

### Test Scripts

- `test_file_upload.py`: Comprehensive file upload testing
- `test_comprehensive_detailed.py`: Includes file upload endpoints

### Test Features

- ✅ Excel file upload and preview
- ✅ CSV file upload and preview
- ✅ Multi-sheet Excel processing
- ✅ File management operations
- ✅ Error handling scenarios
- ✅ Invalid file type rejection

## 📝 Configuration

### Environment Variables

```bash
# File upload settings
UPLOAD_DIR=uploads
MAX_FILE_SIZE=52428800  # 50MB in bytes
```

### Dependencies

```txt
pandas==2.1.4
openpyxl==3.1.2
xlrd==2.0.1
```

## 🔧 Maintenance

### Database Migration

```bash
# Create new migration for file upload tables
alembic revision --autogenerate -m "Add file upload models"
alembic upgrade head
```

### File Cleanup

```python
# Clean up orphaned files
import os
from pathlib import Path

upload_dir = Path("uploads")
for file_path in upload_dir.rglob("*"):
    if file_path.is_file():
        # Check if file exists in database
        # Delete if not found
        pass
```

---

**Last Updated**: December 2024
**Version**: 1.0
**Maintainer**: FastAPI Backend Team
