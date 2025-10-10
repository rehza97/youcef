#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Youcef Backend API - One-Tool Army
Automatically handles database creation, migrations, and server startup
"""

# Print immediately to show script is running (before any imports)
from websocket_manager import manager
from core.rate_limiter import RateLimiter
from core.config import settings
from core.security import verify_token, get_current_user
from models.message import Message
from models.conversation import Conversation, ConversationParticipant
from models.user import User
from database.connection import engine, Base, get_db
from services.processing_websocket import processing_ws_manager
from services.background_processor import background_processor
from api.dot_management import router as dot_management_router
from api.park_management import router as park_management_router
from api.kpi_processing import kpi_processing_router
from api.etl_processing import etl_processing_router
from api.encaissement_analytics import encaissement_analytics_router
from api.encaissement_upload import encaissement_upload_router
from api.websocket_messaging import router as websocket_router
from api.admin_broadcast import router as admin_broadcast_router
from api.secure_file_management import router as secure_file_router
from api.secure_messaging import router as secure_messaging_router
from api.message_reactions import message_reactions_router
from api.message_attachments import message_attachments_router
from api.message_crud import message_crud_router
from api.file_processing import file_processing_router
from api.file_preview import file_preview_router
from api.file_management import file_management_router
from api.file_upload import file_upload_router
from api.permission_management import permission_management_router
from api.role_management import role_management_router
from api.health import health_router
from api.user_blocks import user_blocks_router
from api.conversations import conversations_router
from api.notifications import notifications_router
from api.user_role_assignments import user_role_assignments_router
from api.users_management import users_management_router
from api.auth import auth_router
import sys
from sqlalchemy.orm import Session
import json
from datetime import datetime
import logging
from typing import List, Optional, Dict
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi.security import HTTPBearer
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from api.park_analytics import park_analytics_router
print("", flush=True)
print("=" * 70, flush=True)
print("  Starting Youcef Backend API...", flush=True)
print("=" * 70, flush=True)
print("", flush=True)


print("✓ Core imports successful", flush=True)

# Import routers

# Role and Permission Management (split from roles_permissions.py)

# File Management (split from files.py)

# Message Management (split from messages.py)

# New Secure Services

# Encaissement Management (split from encaissement.py)

# ETL Processing

# KPI Processing with Auto-Detection

# Park Management

# DOT Management

# Background Processing

# Import database and models

# Import WebSocket manager

print("✓ All modules imported successfully", flush=True)
print("", flush=True)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # Add UTF-8 encoding
        logging.FileHandler('debug.log', encoding='utf-8')
    ]
)

# Create loggers
logger = logging.getLogger("main")
ws_logger = logging.getLogger("websocket")
file_logger = logging.getLogger("files")

# Set log levels
ws_logger.setLevel(logging.DEBUG)
file_logger.setLevel(logging.DEBUG)

# Suppress verbose third-party library logs
logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
logging.getLogger("multipart").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Suppress verbose application logs during bulk processing
logging.getLogger("services.dot_service").setLevel(logging.INFO)

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("")
    logger.info("=" * 70)
    logger.info("  YOUCEF BACKEND API - AUTOMATIC SETUP & STARTUP")
    logger.info("=" * 70)
    logger.info("")

    # Step 1: Initialize database (create DB if needed, run migrations)
    try:
        logger.info("[1/3] Database Initialization")
        logger.info("-" * 70)
        from core.database_setup import initialize_database
        success = initialize_database(settings.DATABASE_URL)
        if success:
            logger.info("Database initialization completed successfully")
        else:
            logger.warning(
                "Database initialization had warnings, but continuing...")
    except ImportError as e:
        logger.warning(f"Database setup module not available: {e}")
        logger.info(
            "Skipping automatic database creation - will use existing DB")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.info("Continuing with manual database configuration...")

    logger.info("")

    # Step 2: Create database tables (for any models not in migrations)
    try:
        logger.info("[2/3] Database Tables")
        logger.info("-" * 70)
        from database.connection import engine
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        logger.error("")
        logger.error("=" * 70)
        logger.error(
            "CRITICAL ERROR: Cannot start without database connection")
        logger.error("Please ensure:")
        logger.error("  1. PostgreSQL is running")
        logger.error("  2. Database 'youcef_db' exists")
        logger.error("  3. Credentials in config.py are correct")
        logger.error("=" * 70)
        raise

    logger.info("")

    # Step 3: Initialize RBAC system (permissions and default roles)
    try:
        logger.info("[3/3] RBAC System Initialization")
        logger.info("-" * 70)
        from core.rbac_init import check_and_init_rbac
        check_and_init_rbac()
        logger.info("RBAC system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RBAC system: {e}")
        logger.warning("RBAC system may not be fully initialized")

    logger.info("")
    logger.info("=" * 70)
    logger.info("  SERVER READY")
    logger.info("  Access API Documentation: http://localhost:8001/docs")
    logger.info("  Health Check: http://localhost:8001/health")
    logger.info("=" * 70)
    logger.info("")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")

    # Shutdown background processor and kill all child processes
    try:
        from services.background_processor import background_processor
        background_processor.shutdown()
        logger.info("Background processor shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down background processor: {e}")

    # Close WebSocket connections
    try:
        manager.disconnect_all()
        logger.info("WebSocket connections closed")
    except Exception as e:
        logger.error(f"Error closing WebSocket connections: {e}")

    # Close processing WebSocket connections
    try:
        from services.processing_websocket import processing_ws_manager
        # Clear all connections
        processing_ws_manager.active_connections.clear()
        processing_ws_manager.processing_connections.clear()
        logger.info("Processing WebSocket connections closed")
    except Exception as e:
        logger.error(f"Error closing processing WebSocket connections: {e}")

    # Close database connections
    try:
        from database.connection import engine
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

    logger.info("FastAPI application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Youcef Backend API",
    description="A comprehensive FastAPI backend with real-time features, RBAC, and messaging",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware - Configure for WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware - Allow localhost and 127.0.0.1
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Allow all hosts for development
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
    users_management_router,
    prefix="/api/users",
    tags=["User Management"],
    dependencies=[Depends(get_current_user)]
)

# User Role Assignments (assign/remove/check roles & permissions)
app.include_router(
    user_role_assignments_router,
    prefix="/api/users",
    tags=["User Roles"],
    dependencies=[Depends(get_current_user)]
)

# Role and Permission Management
app.include_router(
    role_management_router,
    prefix="/api/roles",
    tags=["Role Management"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    permission_management_router,
    prefix="/api/permissions",
    tags=["Permission Management"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    notifications_router,
    prefix="/api/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    conversations_router,
    prefix="/api/conversations",
    tags=["Conversations"],
    dependencies=[Depends(get_current_user)]
)

# Message Management (split routers)
app.include_router(
    message_crud_router,
    prefix="/api/messages",
    tags=["Message CRUD"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    message_attachments_router,
    prefix="/api/messages",
    tags=["Message Attachments"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    message_reactions_router,
    prefix="/api/messages",
    tags=["Message Reactions"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    user_blocks_router,
    prefix="/api/blocks",
    tags=["User Blocks"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    health_router,
    prefix="/api",
    tags=["Health"]
)

# File Management (split routers)
app.include_router(
    file_upload_router,
    prefix="/api/files",
    tags=["File Upload"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    file_management_router,
    prefix="/api/files",
    tags=["File Management"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    file_preview_router,
    prefix="/api/files",
    tags=["File Preview"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    file_processing_router,
    prefix="/api/files",
    tags=["File Processing"],
    dependencies=[Depends(get_current_user)]
)

# Encaissement Management (split routers)
app.include_router(
    encaissement_upload_router,
    prefix="/api/encaissement",
    tags=["Encaissement Upload"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    encaissement_analytics_router,
    prefix="/api/encaissement",
    tags=["Encaissement Analytics"],
    dependencies=[Depends(get_current_user)]
)

# ETL Processing
app.include_router(
    etl_processing_router,
    prefix="/api/etl",
    tags=["ETL Processing"],
    dependencies=[Depends(get_current_user)]
)

# KPI Processing with Auto-Detection
app.include_router(
    kpi_processing_router,
    prefix="/api/kpi",
    tags=["KPI Processing"],
    dependencies=[Depends(get_current_user)]
)

# Park Management
app.include_router(
    park_management_router,
    tags=["Park Management"]
)

# DOT Management
app.include_router(
    dot_management_router,
    tags=["DOT Management"],
    dependencies=[Depends(get_current_user)]
)

# Park Analytics - Real data for dashboard
app.include_router(
    park_analytics_router,
    prefix="/api/park-analytics",
    tags=["Park Analytics"]
)

# New Secure Services
app.include_router(
    secure_messaging_router,
    tags=["Secure Messaging"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    secure_file_router,
    tags=["Secure File Management"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    admin_broadcast_router,
    tags=["Admin Broadcasting"],
    dependencies=[Depends(get_current_user)]
)

# WebSocket endpoints
app.include_router(
    websocket_router,
    tags=["WebSocket Messaging"]
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
            "Role-Based Access Control (RBAC) with DOT Integration",
            "Secure Real-time Messaging with Encryption",
            "Real-time Notifications",
            "Secure File Upload & Management",
            "Admin File Broadcasting",
            "Audit Logging & Security Tracking",
            "Path Traversal Protection",
            "Content Validation & Malware Scanning",
            "DOT-based Permission System",
            "Message Threading & Read Receipts",
            "Encaissement Processing"
        ],
        "websocket_endpoints": [
            "/ws/messaging",
            "/ws/notifications"
        ]
    }


# WebSocket Endpoints for Real-time Features

async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """Extract user from JWT token"""
    ws_logger.debug(f"Starting token validation for token: {token[:20]}...")

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
            ws_logger.debug("Removed 'Bearer ' prefix from token")

        ws_logger.debug(f"Validating token: {token[:20]}...")

        # Import User model here to avoid circular imports
        from models.user import User

        token_data = verify_token(token)
        ws_logger.info(
            f"✅ Token validation successful, user_id: {token_data.user_id}, username: {token_data.username}")

        if token_data and token_data.user_id:
            user = db.query(User).filter(User.id == token_data.user_id).first()
            if user:
                ws_logger.debug(f"User found: {user.username} (ID: {user.id})")
                return user
            else:
                ws_logger.error(
                    f"User not found in database for ID: {token_data.user_id}")
        else:
            ws_logger.error("Token data is missing user_id")
    except HTTPException as e:
        ws_logger.error(
            f"❌ HTTP Exception during token validation: {e.detail}")
        ws_logger.error(f"Status code: {e.status_code}")
        ws_logger.error(
            f"💡 Hint: Token may be expired or invalid. Please log out and log back in.")
    except Exception as e:
        ws_logger.error(f"❌ Token validation error: {e}")
        ws_logger.error(f"Error type: {type(e).__name__}")
        ws_logger.error(f"Error details: {str(e)}")
        import traceback
        ws_logger.error(f"Stack trace:\n{traceback.format_exc()}")

    ws_logger.error("Token validation failed")
    return None


# Test WebSocket endpoint (no authentication)
@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Simple test WebSocket endpoint"""
    print("Test WebSocket connection attempt")
    await websocket.accept()
    print("Test WebSocket connection accepted")

    try:
        await websocket.send_text(json.dumps({"type": "test", "message": "Connection successful"}))
        while True:
            data = await websocket.receive_text()
            print(f"Test WebSocket received: {data}")
            await websocket.send_text(json.dumps({"type": "echo", "data": data}))
    except WebSocketDisconnect:
        print("Test WebSocket disconnected")
    except Exception as e:
        print(f"Test WebSocket error: {e}")


@app.websocket("/ws/notifications/")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""

    # Get user_id from query parameters
    user_id_str = websocket.query_params.get("user_id")
    if not user_id_str:
        print("No user_id provided in query parameters")
        await websocket.close(code=4002, reason="No user_id provided")
        return

    try:
        user_id = int(user_id_str)
    except ValueError:
        print(f"Invalid user_id format: {user_id_str}")
        await websocket.close(code=4002, reason="Invalid user_id format")
        return

    print(f"WebSocket connection attempt for user_id: {user_id}")
    ws_logger.info(f"WebSocket connection attempt for user_id: {user_id}")

    # Accept connection first
    await websocket.accept()
    print("WebSocket connection accepted")
    ws_logger.debug("WebSocket connection accepted")

    try:
        # Get token from query parameters AFTER accepting connection
        token = websocket.query_params.get("token")
        print(f"Token from query params: {'Present' if token else 'Missing'}")
        ws_logger.debug(
            f"Token from query params: {'Present' if token else 'Missing'}")

        if not token:
            print("No token provided in query parameters")
            ws_logger.error("No token provided in query parameters")
            await websocket.close(code=4001, reason="No token provided")
            return

        # Create database session manually
        from database.connection import SessionLocal
        db = SessionLocal()

        try:
            # Validate user AFTER accepting connection
            print(f"Validating user for user_id: {user_id}")
            ws_logger.debug(f"Validating user for user_id: {user_id}")
            user = await get_user_from_token(token, db)

            if not user or user.id != user_id:
                print(
                    f"Authentication failed - User: {user}, Expected user_id: {user_id}")
                ws_logger.error(
                    f"Authentication failed - User: {user}, Expected user_id: {user_id}")
                await websocket.close(code=4003, reason="Access denied")
                return

            print(f"Authentication successful for user: {user.username}")
            ws_logger.info(
                f"Authentication successful for user: {user.username}")

            # Register connection with manager (don't call accept again)
            print("Registering with notification manager...")
            ws_logger.debug("Registering with notification manager...")
            if user_id not in manager.active_connections:
                manager.active_connections[user_id] = {}
            manager.active_connections[user_id]["notifications"] = websocket
            print(f"User {user_id} registered for notifications WebSocket")
            ws_logger.info(
                f"User {user_id} registered for notifications WebSocket")

            try:
                # Send welcome message
                welcome_message = {
                    "type": "connection",
                    "message": "Connected to notifications",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"Sending welcome message: {welcome_message}")
                ws_logger.debug(f"Sending welcome message: {welcome_message}")
                await websocket.send_text(json.dumps(welcome_message))
                print("Welcome message sent")
                ws_logger.debug("Welcome message sent")

                # Keep connection alive
                print("Starting message loop...")
                ws_logger.debug("Starting message loop...")
                while True:
                    data = await websocket.receive_text()
                    print(f"Received message: {data}")
                    ws_logger.debug(f"Received message: {data}")

                    try:
                        message = json.loads(data)
                        print(f"Parsed message: {message}")
                        ws_logger.debug(f"Parsed message: {message}")

                        if message.get("type") == "ping":
                            print("Received ping, sending pong")
                            ws_logger.debug("Received ping, sending pong")
                            await websocket.send_text(json.dumps({"type": "pong"}))
                            print("Pong sent")
                            ws_logger.debug("Pong sent")

                    except json.JSONDecodeError:
                        print("Received non-JSON message, ignoring")
                        ws_logger.warning(
                            "Received non-JSON message, ignoring")
                        pass

            except WebSocketDisconnect:
                print(f"User {user_id} disconnected from notifications")
                ws_logger.info(
                    f"User {user_id} disconnected from notifications")
                manager.disconnect(user_id, "notifications")
            except Exception as e:
                print(f"WebSocket error for user {user_id}: {e}")
                ws_logger.error(f"WebSocket error for user {user_id}: {e}")
                ws_logger.error(f"Error type: {type(e)}")
                manager.disconnect(user_id, "notifications")

        finally:
            db.close()

    except Exception as e:
        print(f"WebSocket connection error: {e}")
        ws_logger.error(f"WebSocket connection error: {e}")
        ws_logger.error(f"Error type: {type(e)}")
        ws_logger.error(f"Error details: {str(e)}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            print("Failed to close WebSocket connection")
            ws_logger.error("Failed to close WebSocket connection")
            pass


@app.websocket("/ws/processing/")
async def websocket_processing(websocket: WebSocket):
    """WebSocket endpoint for real-time processing updates"""

    # Get user_id from query parameters
    user_id_str = websocket.query_params.get("user_id")
    if not user_id_str:
        print("No user_id provided for processing WebSocket")
        await websocket.close(code=4002, reason="No user_id provided")
        return

    try:
        user_id = int(user_id_str)
    except ValueError:
        print(f"Invalid user_id format: {user_id_str}")
        await websocket.close(code=4002, reason="Invalid user_id format")
        return

    print(f"Processing WebSocket connection attempt for user_id: {user_id}")

    # Accept connection first
    await websocket.accept()
    print("Processing WebSocket connection accepted")

    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            print("No token provided for processing WebSocket")
            await websocket.close(code=4001, reason="No token provided")
            return

        # Create database session manually
        from database.connection import SessionLocal
        db = SessionLocal()

        try:
            # Validate user
            user = await get_user_from_token(token, db)
            if not user or user.id != user_id:
                print(
                    f"Processing WebSocket authentication failed - User: {user}, Expected user_id: {user_id}")
                await websocket.close(code=4003, reason="Access denied")
                return

            print(
                f"Processing WebSocket authentication successful for user: {user.username}")

            # Connect to processing updates
            await processing_ws_manager.connect(websocket, user_id)
            print(f"User {user_id} connected to processing WebSocket")

            try:
                # Send welcome message
                welcome_message = {
                    "type": "connection",
                    "message": "Connected to processing updates",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(welcome_message))
                print("Processing welcome message sent")

                # Keep connection alive and handle messages
                while True:
                    data = await websocket.receive_text()
                    print(f"Processing message received: {data}")

                    try:
                        message = json.loads(data)
                        if message.get("type") == "subscribe_task":
                            # Subscribe to specific task updates
                            task_id = message.get("task_id")
                            if task_id:
                                await processing_ws_manager.connect_to_task(websocket, task_id)
                                await websocket.send_text(json.dumps({
                                    "type": "subscribed",
                                    "task_id": task_id,
                                    "message": f"Subscribed to task {task_id}"
                                }))
                        elif message.get("type") == "ping":
                            await websocket.send_text(json.dumps({"type": "pong"}))
                    except json.JSONDecodeError:
                        print("Processing: Received non-JSON message, ignoring")

            except WebSocketDisconnect:
                print(f"User {user_id} disconnected from processing WebSocket")
                await processing_ws_manager.disconnect(websocket, user_id)
            except Exception as e:
                print(f"Processing WebSocket error: {e}")
                await processing_ws_manager.disconnect(websocket, user_id)

        finally:
            db.close()

    except Exception as e:
        print(f"Processing WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            print("Failed to close processing WebSocket connection")
            pass


@app.websocket("/ws/chat/")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""

    # Get conversation_id from query parameters
    conversation_id_str = websocket.query_params.get("conversation_id")
    if not conversation_id_str:
        print("No conversation_id provided in query parameters")
        await websocket.close(code=4002, reason="No conversation_id provided")
        return

    try:
        conversation_id = int(conversation_id_str)
    except ValueError:
        print(f"Invalid conversation_id format: {conversation_id_str}")
        await websocket.close(code=4002, reason="Invalid conversation_id format")
        return

    print(
        f"Chat WebSocket connection attempt for conversation_id: {conversation_id}")

    # Accept connection first
    await websocket.accept()
    print("Chat WebSocket connection accepted")

    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            print("No token provided for chat WebSocket")
            await websocket.close(code=4001, reason="No token provided")
            return

        # Create database session manually
        from database.connection import SessionLocal
        db = SessionLocal()

        try:
            # Validate user
            user = await get_user_from_token(token, db)
            if not user:
                print("Chat WebSocket authentication failed")
                await websocket.close(code=4003, reason="Access denied")
                return

            print(
                f"Chat WebSocket authentication successful for user: {user.username}")

            # Connect to conversation
            await manager.connect_to_conversation(websocket, conversation_id)
            print(
                f"User {user.id} connected to chat conversation {conversation_id}")

            try:
                # Send welcome message
                welcome_message = {
                    "type": "connection",
                    "message": "Connected to chat",
                    "conversation_id": conversation_id,
                    "user_id": user.id,
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(welcome_message))
                print("Chat welcome message sent")

                # Keep connection alive
                while True:
                    data = await websocket.receive_text()
                    print(f"Chat message received: {data}")

                    try:
                        message = json.loads(data)
                        if message.get("type") == "message":
                            # Broadcast message to all participants in conversation
                            await manager.broadcast_to_conversation(
                                json.dumps({
                                    "type": "message",
                                    "content": message.get("content"),
                                    "user_id": user.id,
                                    "username": user.username,
                                    "conversation_id": conversation_id,
                                    "timestamp": datetime.now().isoformat()
                                }),
                                conversation_id
                            )
                        elif message.get("type") == "ping":
                            await websocket.send_text(json.dumps({"type": "pong"}))
                    except json.JSONDecodeError:
                        print("Chat: Received non-JSON message, ignoring")

            except WebSocketDisconnect:
                print(
                    f"User {user.id} disconnected from chat conversation {conversation_id}")
                manager.disconnect_from_conversation(
                    conversation_id, websocket)
            except Exception as e:
                print(f"Chat WebSocket error: {e}")
                manager.disconnect_from_conversation(
                    conversation_id, websocket)

        finally:
            db.close()

    except Exception as e:
        print(f"Chat WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            print("Failed to close chat WebSocket connection")
            pass


# Helper functions for sending real-time messages
async def send_notification_to_user(user_id: int, notification_data: dict):
    """Send notification to specific user via WebSocket"""
    message = {
        "type": "notification",
        "data": notification_data
    }
    await manager.send_personal_message(json.dumps(message), user_id, "notifications")


async def send_message_to_conversation(conversation_id: int, message_data: dict):
    """Send message to conversation participants via WebSocket"""
    message = {
        "type": "new_message",
        "message": message_data
    }
    await manager.broadcast_to_conversation(json.dumps(message), conversation_id)


if __name__ == "__main__":
    print("", flush=True)
    print("=" * 70, flush=True)
    print("  Launching Uvicorn Server...", flush=True)
    print(f"  Host: {settings.HOST}", flush=True)
    print(f"  Port: {settings.PORT}", flush=True)
    print(f"  Debug: {settings.DEBUG}", flush=True)
    print("=" * 70, flush=True)
    print("", flush=True)

    try:
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user", flush=True)
    except Exception as e:
        print(f"\n\nERROR: Server failed to start: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
