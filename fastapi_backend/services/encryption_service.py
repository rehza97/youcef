import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self):
        self._initialize_encryption_key()

    def _initialize_encryption_key(self):
        """Initialize encryption key from environment or generate new one"""
        try:
            # Try to get key from environment variable
            key_b64 = os.environ.get('ENCRYPTION_KEY')

            if key_b64:
                self.encryption_key = key_b64.encode()
                self.fernet = Fernet(self.encryption_key)
            else:
                # Generate new key for development (should be set in production)
                logger.warning("No ENCRYPTION_KEY found in environment, generating new key for development")
                self.encryption_key = Fernet.generate_key()
                self.fernet = Fernet(self.encryption_key)
                logger.warning(f"Generated encryption key: {self.encryption_key.decode()}")
                logger.warning("Please set this key in your environment variables for production!")

        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            # Fallback to a generated key
            self.encryption_key = Fernet.generate_key()
            self.fernet = Fernet(self.encryption_key)

    def encrypt_message(self, plaintext: str) -> str:
        """Encrypt message content"""
        try:
            if not plaintext:
                return ""

            # Convert to bytes and encrypt
            plaintext_bytes = plaintext.encode('utf-8')
            encrypted_bytes = self.fernet.encrypt(plaintext_bytes)

            # Return base64 encoded string for database storage
            return base64.b64encode(encrypted_bytes).decode('utf-8')

        except Exception as e:
            logger.error(f"Error encrypting message: {e}")
            # Return original text if encryption fails (for debugging)
            return plaintext

    def decrypt_message(self, encrypted_text: str) -> str:
        """Decrypt message content"""
        try:
            if not encrypted_text:
                return ""

            # If text doesn't look encrypted (no base64), return as-is (backward compatibility)
            if not self._is_base64(encrypted_text):
                return encrypted_text

            # Decode from base64 and decrypt
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)

            return decrypted_bytes.decode('utf-8')

        except Exception as e:
            logger.error(f"Error decrypting message: {e}")
            # Return placeholder if decryption fails
            return "[Decryption failed]"

    def encrypt_file_path(self, file_path: str) -> str:
        """Encrypt file path for secure storage"""
        try:
            return self.encrypt_message(file_path)
        except Exception as e:
            logger.error(f"Error encrypting file path: {e}")
            return file_path

    def decrypt_file_path(self, encrypted_path: str) -> str:
        """Decrypt file path"""
        try:
            return self.decrypt_message(encrypted_path)
        except Exception as e:
            logger.error(f"Error decrypting file path: {e}")
            return encrypted_path

    def encrypt_metadata(self, metadata_dict: dict) -> str:
        """Encrypt metadata dictionary"""
        try:
            import json
            metadata_str = json.dumps(metadata_dict)
            return self.encrypt_message(metadata_str)
        except Exception as e:
            logger.error(f"Error encrypting metadata: {e}")
            return json.dumps(metadata_dict)

    def decrypt_metadata(self, encrypted_metadata: str) -> dict:
        """Decrypt metadata dictionary"""
        try:
            import json
            decrypted_str = self.decrypt_message(encrypted_metadata)
            return json.loads(decrypted_str)
        except Exception as e:
            logger.error(f"Error decrypting metadata: {e}")
            try:
                # Try to parse as unencrypted JSON
                return json.loads(encrypted_metadata)
            except:
                return {}

    def generate_file_key(self, file_id: int, user_id: int) -> str:
        """Generate unique key for file encryption based on file and user ID"""
        try:
            # Create unique salt based on file_id and user_id
            salt_string = f"file_{file_id}_user_{user_id}".encode('utf-8')

            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_string,
                iterations=100000,
            )

            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
            return key.decode('utf-8')

        except Exception as e:
            logger.error(f"Error generating file key: {e}")
            return base64.urlsafe_b64encode(self.encryption_key).decode('utf-8')

    def _is_base64(self, s: str) -> bool:
        """Check if string is valid base64"""
        try:
            if len(s) % 4 != 0:
                return False
            base64.b64decode(s.encode('utf-8'))
            return True
        except Exception:
            return False

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt (for future password encryption features)"""
        try:
            if salt is None:
                salt = os.urandom(32)
            else:
                salt = salt.encode('utf-8')

            # Use PBKDF2 for password hashing
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )

            hashed = kdf.derive(password.encode('utf-8'))

            return (
                base64.b64encode(hashed).decode('utf-8'),
                base64.b64encode(salt).decode('utf-8')
            )

        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            return password, ""

    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            salt_bytes = base64.b64decode(salt.encode('utf-8'))
            hashed_bytes = base64.b64decode(hashed.encode('utf-8'))

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
            )

            kdf.verify(password.encode('utf-8'), hashed_bytes)
            return True

        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

# Global instance
encryption_service = EncryptionService()