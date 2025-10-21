from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Youcef Backend API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Security
    # Use a fixed SECRET_KEY to prevent token invalidation on server restart
    # In production, set this via environment variable
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "youcef-dev-secret-key-DO-NOT-USE-IN-PRODUCTION-12345678")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for development
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption key for sensitive data (messages, file paths, etc.)
    # In production, set this via environment variable with a secure Fernet key
    # Generate a new key with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY", "RtDWPt-l76-kKWG8T7Wa23RDiR64eLS2N2D3rDgE00c=")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:123456789@localhost:5432/youcef_db")
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 300

    # Redis (for caching and WebSocket)
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Allowed hosts - flexible to handle different input formats
    # Allow all hosts in Docker environment
    ALLOWED_HOSTS: Union[List[str], str] = ["*"]

    # Rate limiting
    RATE_LIMIT_ANON: str = "100/hour"
    RATE_LIMIT_USER: str = "1000/hour"
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/minute"

    # File upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024 * 1024  # 10GB - Very large limit
    UPLOAD_DIR: str = "uploads"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "fastapi.log"

    # WebSocket
    WS_MESSAGE_QUEUE_SIZE: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Environment-specific settings
if settings.DEBUG:
    # Development settings
    settings.CORS_ALLOWED_ORIGINS.extend([
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ])
else:
    # Production settings
    settings.DEBUG = False
    settings.DATABASE_ECHO = False
    settings.LOG_LEVEL = "WARNING"
