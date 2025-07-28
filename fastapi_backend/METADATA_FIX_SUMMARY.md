# SQLAlchemy Metadata Conflict Fix

## 🐛 Problem

The FastAPI server was failing to start with the following error:

```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

This error occurred because the `FileUpload` model in `fastapi_backend/models/file_upload.py` had a column named `metadata`, which conflicts with SQLAlchemy's reserved `metadata` attribute.

## 🔧 Solution

### 1. Renamed the Column

**File:** `fastapi_backend/models/file_upload.py`

**Before:**

```python
# JSON string for additional metadata
metadata = Column(Text, nullable=True)
```

**After:**

```python
# JSON string for additional metadata
file_metadata = Column(Text, nullable=True)
```

### 2. Updated Pydantic Schema

**File:** `fastapi_backend/models/file_upload.py`

**Before:**

```python
class FileUploadResponse(FileUploadBase):
    # ... other fields ...
    metadata: Optional[str] = None
```

**After:**

```python
class FileUploadResponse(FileUploadBase):
    # ... other fields ...
    file_metadata: Optional[str] = None
```

## 📋 Changes Made

1. **Column Rename**: Changed `metadata` column to `file_metadata` in `FileUpload` model
2. **Schema Update**: Updated `FileUploadResponse` Pydantic schema to use `file_metadata`
3. **Indentation Fix**: Corrected indentation issues that were introduced during the fix

## ✅ Verification

- ✅ No more SQLAlchemy `InvalidRequestError`
- ✅ All imports work correctly
- ✅ Database table creation works
- ✅ Model instantiation works
- ✅ No conflicts with other `metadata` references (like `conversation_metadata`, `message_metadata`, `Base.metadata`)

## 🧪 Testing

Created `test_startup_fixed.py` to verify:

- All imports work correctly
- Database table creation succeeds
- Model instantiation works without conflicts
- All API routers can be imported

## 📝 Notes

- Other `metadata` references in the codebase are correct and don't need changes:
  - `conversation_metadata` in `Conversation` model
  - `message_metadata` in `Message` model
  - `Base.metadata` for SQLAlchemy metadata
- The fix only affects the file upload functionality
- All existing functionality remains intact

## 🚀 Next Steps

The FastAPI server should now start successfully. You can run:

```bash
cd fastapi_backend
python main.py
```

The file upload and preview functionality should work correctly with the renamed `file_metadata` field.
