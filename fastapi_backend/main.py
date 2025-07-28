from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import List, Optional
import logging
from datetime import datetime

# Import routers
from api.auth import auth_router
from api.users import users_router
from api.notifications import notifications_router
from api.messaging import messaging_router
from api.health import health_router
from api.files import files_router

# Import database and dependencies
from database.connection import init_db, close_db
from core.config import settings
from core.security import get_current_user
from core.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s',
    handlers=[
        logging.FileHandler('fastapi.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting FastAPI application...")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    await close_db()
    logger.info("Database connection closed")

# Create FastAPI app
app = FastAPI(
    title="Youcef Backend API",
    description="A comprehensive FastAPI backend with real-time features, RBAC, and messaging",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Rate limiter
rate_limiter = RateLimiter()

# Include routers
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"],
    dependencies=[Depends(rate_limiter.check_rate_limit)]
)

app.include_router(
    users_router,
    prefix="/api/users",
    tags=["User Management"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    notifications_router,
    prefix="/api/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    messaging_router,
    prefix="/api/messaging",
    tags=["Messaging"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    health_router,
    prefix="/api",
    tags=["Health"]
)

app.include_router(
    files_router,
    prefix="/api/files",
    tags=["File Upload & Preview"],
    dependencies=[Depends(get_current_user)]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Youcef Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "name": "Youcef Backend API",
        "version": "1.0.0",
        "description": "FastAPI backend with real-time features",
        "features": [
            "Authentication & Authorization",
            "Role-Based Access Control (RBAC)",
            "Real-time Messaging",
            "Notifications System",
            "WebSocket Support",
            "Rate Limiting",
            "CORS Support"
        ],
        "endpoints": {
            "authentication": "/api/auth",
            "users": "/users",
            "notifications": "/api/notifications",
            "messaging": "/api/messaging",
            "health": "/api/health"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
