import os
import uuid
import mimetypes
import hashlib
import logging

# Optional import for magic library
try:
    import magic
    # Test if magic actually works by trying to create an instance
    magic.from_buffer(b'test', mime=True)
    HAS_MAGIC = True
except (ImportError, OSError, Exception):
    HAS_MAGIC = False
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from models.file_upload import FileUpload, FileUploadCreate
from models.user import User
from services.dot_service import DOTService

logger = logging.getLogger(__name__)

class SecureFileService:
    """Secure file service with proper validation and sanitization"""

    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB
        'document': 50 * 1024 * 1024,  # 50MB
        'excel': 100 * 1024 * 1024,  # 100MB
        'csv': 20 * 1024 * 1024,  # 20MB
        'message_attachment': 25 * 1024 * 1024,  # 25MB
        'default': 5 * 1024 * 1024  # 5MB
    }

    # Allowed MIME types and their corresponding file types
    ALLOWED_MIME_TYPES = {
        # Images
        'image/jpeg': 'image',
        'image/png': 'image',
        'image/gif': 'image',
        'image/webp': 'image',
        # Documents
        'application/pdf': 'document',
        'application/msword': 'document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
        # Spreadsheets
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
        'application/vnd.ms-excel': 'excel',
        'text/csv': 'csv',
        'application/csv': 'csv',
        # Text
        'text/plain': 'text',
        'application/json': 'text'
    }

    # Magic number signatures for file type validation
    MAGIC_SIGNATURES = {
        b'\xFF\xD8\xFF': 'image/jpeg',
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'GIF87a': 'image/gif',
        b'GIF89a': 'image/gif',
        b'RIFF': 'image/webp',
        b'%PDF': 'application/pdf',
        b'PK\x03\x04': 'application/vnd.openxmlformats-officedocument',  # Office files
        b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': 'application/vnd.ms-office'  # Old Office files
    }

    def __init__(self, upload_dir: str = "secure_uploads"):
        self.upload_dir = Path(upload_dir).resolve()  # Resolve to absolute path
        self._setup_directories()

    def _setup_directories(self):
        """Setup secure directory structure"""
        try:
            # Create main upload directory with restricted permissions
            self.upload_dir.mkdir(exist_ok=True, mode=0o750)

            # Create subdirectories for different file types
            subdirs = ['images', 'documents', 'excel', 'csv', 'messages', 'broadcast', 'temp']
            for subdir in subdirs:
                (self.upload_dir / subdir).mkdir(exist_ok=True, mode=0o750)

            # Create quarantine directory for suspicious files
            (self.upload_dir / 'quarantine').mkdir(exist_ok=True, mode=0o700)

            logger.info(f"Secure upload directories created at: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create secure upload directories: {e}")
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks"""
        if not filename:
            raise HTTPException(status_code=400, detail="Filename cannot be empty")

        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', '~', '$', '&', ';', '|', '<', '>', '`']
        sanitized = filename

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')

        # Ensure filename isn't too long
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:150] + ext

        # Ensure we have a filename after sanitization
        if not sanitized or sanitized == '_':
            sanitized = f"file_{uuid.uuid4().hex[:8]}"

        return sanitized

    def _validate_file_content(self, content: bytes, filename: str) -> Tuple[str, str]:
        """Validate file content using magic numbers and return actual MIME type and file type"""
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Check magic numbers (first few bytes) to determine actual file type
        detected_mime = None
        for signature, mime_type in self.MAGIC_SIGNATURES.items():
            if content.startswith(signature):
                detected_mime = mime_type
                break

        # Use python-magic if available for more accurate detection
        if not detected_mime and HAS_MAGIC:
            try:
                detected_mime = magic.from_buffer(content, mime=True)
            except:
                pass

        # Fallback to filename-based detection if magic detection failed
        if not detected_mime:
            detected_mime, _ = mimetypes.guess_type(filename)

        if not detected_mime:
            raise HTTPException(status_code=400, detail="Cannot determine file type")

        # Handle Office documents special case
        if detected_mime == 'application/vnd.openxmlformats-officedocument':
            if filename.lower().endswith(('.xlsx', '.xls')):
                detected_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif filename.lower().endswith(('.docx', '.doc')):
                detected_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        # Check if MIME type is allowed
        if detected_mime not in self.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{detected_mime}' is not allowed"
            )

        file_type = self.ALLOWED_MIME_TYPES[detected_mime]
        return detected_mime, file_type

    def _validate_file_size(self, content: bytes, file_type: str, upload_type: str = 'default') -> None:
        """Validate file size based on type"""
        file_size = len(content)

        # Determine size limit based on upload type or file type
        size_limit = self.MAX_FILE_SIZES.get(upload_type) or self.MAX_FILE_SIZES.get(file_type) or self.MAX_FILE_SIZES['default']

        if file_size > size_limit:
            size_mb = size_limit / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size for {file_type} files is {size_mb:.1f}MB"
            )

    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content for integrity checking"""
        return hashlib.sha256(content).hexdigest()

    def _get_secure_file_path(self, file_type: str, filename: str, upload_context: str = 'general') -> Path:
        """Generate secure file path within sandbox"""
        # Create context-specific subdirectory
        if upload_context == 'message':
            subdir = self.upload_dir / 'messages'
        elif upload_context == 'broadcast':
            subdir = self.upload_dir / 'broadcast'
        else:
            subdir = self.upload_dir / file_type.lower()

        # Ensure path is within our upload directory (prevent directory traversal)
        try:
            secure_path = (subdir / filename).resolve()
            if not str(secure_path).startswith(str(self.upload_dir)):
                raise ValueError("Path traversal attempt detected")
            return secure_path
        except Exception as e:
            logger.error(f"Path validation failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid file path")

    def _scan_for_malware(self, content: bytes, filename: str) -> bool:
        """Basic malware scanning - placeholder for integration with antivirus"""
        # This is a placeholder - in production, integrate with ClamAV or similar
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'<?php',
            b'eval(',
            b'exec(',
            b'system(',
            b'<iframe'
        ]

        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                logger.warning(f"Suspicious content detected in file: {filename}")
                return False

        return True

    async def save_file_securely(
        self,
        db: Session,
        file: UploadFile,
        user_id: int,
        upload_context: str = 'general',
        additional_validation: Optional[callable] = None
    ) -> FileUpload:
        """Save file with comprehensive security validation"""
        try:
            # Read file content
            content = await file.read()
            original_filename = self._sanitize_filename(file.filename or "unknown")

            # Validate file content and get actual type
            detected_mime, file_type = self._validate_file_content(content, original_filename)

            # Validate file size
            self._validate_file_size(content, file_type, upload_context)

            # Scan for malware
            if not self._scan_for_malware(content, original_filename):
                # Move to quarantine
                quarantine_path = self.upload_dir / 'quarantine' / f"quarantine_{uuid.uuid4().hex[:8]}_{original_filename}"
                with open(quarantine_path, 'wb') as f:
                    f.write(content)
                logger.error(f"File quarantined due to suspicious content: {original_filename}")
                raise HTTPException(status_code=400, detail="File contains suspicious content")

            # Generate unique secure filename
            file_extension = Path(original_filename).suffix.lower()
            unique_filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}{file_extension}"

            # Get secure file path
            file_path = self._get_secure_file_path(file_type, unique_filename, upload_context)

            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(content)

            # Apply additional validation if provided
            if additional_validation:
                additional_validation(content, original_filename, detected_mime)

            # Save file with restricted permissions
            with open(file_path, 'wb') as f:
                f.write(content)
            os.chmod(file_path, 0o640)  # Read/write for owner, read for group

            # Create database record
            file_upload = FileUpload(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=str(file_path),
                file_size=len(content),
                file_type=file_type,
                mime_type=detected_mime,
                uploaded_by=user_id,
                file_metadata=f'{{"hash": "{file_hash}", "upload_context": "{upload_context}"}}'
            )

            db.add(file_upload)
            db.commit()
            db.refresh(file_upload)

            logger.info(f"File saved securely: {file_upload.id} ({original_filename})")
            return file_upload

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving file securely: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save file securely")

    def validate_file_access(
        self,
        db: Session,
        file_upload: FileUpload,
        user: User,
        access_context: str = 'download'
    ) -> bool:
        """Validate user access to file based on DOT permissions and context"""
        try:
            # Superusers and staff have access to all files
            if user.is_superuser or user.is_staff:
                return True

            # File owner always has access
            if file_upload.uploaded_by == user.id:
                return True

            # For broadcast files, check if user has appropriate access
            if 'broadcast' in file_upload.file_metadata:
                # Parse metadata to check broadcast permissions
                import json
                try:
                    metadata = json.loads(file_upload.file_metadata)
                    if metadata.get('broadcast_type') == 'all_users':
                        return True
                    elif metadata.get('broadcast_type') == 'dot_users':
                        target_dot_id = metadata.get('target_dot_id')
                        if target_dot_id and DOTService.validate_dot_access(db, user.id, target_dot_id):
                            return True
                except:
                    pass

            # For message attachments, validate through conversation participation
            if access_context == 'message_attachment':
                # This would need integration with conversation/message models
                # For now, allow access if user is in same DOT
                uploader = db.query(User).filter(User.id == file_upload.uploaded_by).first()
                if uploader and user.dot_id and user.dot_id == uploader.dot_id:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error validating file access: {e}")
            return False

    def get_secure_file_path(self, file_upload: FileUpload) -> Optional[Path]:
        """Get secure file path if file exists and is valid"""
        try:
            file_path = Path(file_upload.file_path)

            # Ensure path is within our upload directory
            if not str(file_path.resolve()).startswith(str(self.upload_dir)):
                logger.error(f"File path outside upload directory: {file_path}")
                return None

            # Check if file exists
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            return file_path

        except Exception as e:
            logger.error(f"Error getting secure file path: {e}")
            return None

    def delete_file_securely(self, db: Session, file_upload: FileUpload) -> bool:
        """Securely delete file and database record"""
        try:
            file_path = self.get_secure_file_path(file_upload)

            if file_path and file_path.exists():
                # Overwrite file content before deletion for security
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_upload.file_size))
                    f.flush()
                    os.fsync(f.fileno())

                # Delete file
                file_path.unlink()

            # Remove database record
            db.delete(file_upload)
            db.commit()

            logger.info(f"File deleted securely: {file_upload.id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file securely: {e}")
            db.rollback()
            return False

# Global instance
secure_file_service = SecureFileService()