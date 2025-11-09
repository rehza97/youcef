from pydantic import Field
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
    # Production default key set - can be overridden via environment variable or .env file
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "Pr0d-S3cr3tK3y!@#$%X9mN8pQ7rS6tU5vW4xY3zAb2cD1eF0gH")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for development
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption key for sensitive data (messages, file paths, etc.)
    # In production, set this via environment variable with a secure Fernet key
    # Generate a new key with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY", "RtDWPt-l76-kKWG8T7Wa23RDiR64eLS2N2D3rDgE00c=")

    # Database
    # Production default password set - can be overridden via environment variable or .env file
    # The database password must match DB_PASSWORD in docker-compose.yml and PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:Pr0d@ctS3cur3P@ssw0rd!2024XyZ#9mK$L5vN@postgres:5432/youcef_db")
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 300

    # Redis (for caching and WebSocket)
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

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

# ============================================================================
# VALIDATION: Log current configuration status
# ============================================================================
import logging
logger = logging.getLogger(__name__)

# Check if using production credentials
if "Pr0d@ctS3cur3P@ssw0rd" in settings.DATABASE_URL:
    logger.info("✅ Using production DATABASE_URL with secure password")
else:
    logger.warning("⚠️  WARNING: DATABASE_URL does not contain expected production password")
    logger.warning("   Set DB_PASSWORD in .env file to override")

if "Pr0d-S3cr3tK3y" in settings.SECRET_KEY:
    logger.info("✅ Using production SECRET_KEY")
else:
    logger.warning("⚠️  WARNING: SECRET_KEY does not contain expected production key")
    logger.warning("   Set SECRET_KEY in .env file to override")

# Override CORS origins from environment if provided
cors_origins = os.getenv("CORS_ORIGINS")
if cors_origins:
    settings.CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in cors_origins.split(",") if origin.strip()
    ]

# Environment-specific settings
if settings.DEBUG:
    # Development settings
    for origin in [
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]:
        if origin not in settings.CORS_ALLOWED_ORIGINS:
            settings.CORS_ALLOWED_ORIGINS.append(origin)
else:
    # Production settings
    settings.DEBUG = False
    settings.DATABASE_ECHO = False
    settings.LOG_LEVEL = "WARNING"
