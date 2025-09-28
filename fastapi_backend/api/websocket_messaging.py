from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging

from database.connection import get_db
from services.websocket_messaging_service import websocket_messaging_manager
from services.audit_service import audit_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/messaging")
async def websocket_messaging_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time messaging"""
    user = None

    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication token required")
            return

        user = await websocket_messaging_manager.authenticate_websocket(websocket, token, db)
        if not user:
            return  # Authentication failed, connection already closed

        # Connect user
        await websocket_messaging_manager.connect_user(websocket, user, db)

        # Send initial connection data
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "server_time": "2025-09-28T04:00:00Z"
            }
        }))

        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle the message
                await websocket_messaging_manager.handle_message(websocket, message_data, db)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.id if user else 'unknown'}")
                break
            except json.JSONDecodeError:
                # Send error for invalid JSON
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error in WebSocket message handling: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Internal server error"
                }))

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass
    finally:
        # Clean up connection
        if user:
            await websocket_messaging_manager.disconnect_user(websocket, db)

@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time notifications"""
    user = None

    try:
        # Authenticate user
        if not token:
            await websocket.close(code=4001, reason="Authentication token required")
            return

        user = await websocket_messaging_manager.authenticate_websocket(websocket, token, db)
        if not user:
            return

        await websocket.accept()

        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "notifications_connected",
            "data": {
                "user_id": user.id,
                "server_time": "2025-09-28T04:00:00Z"
            }
        }))

        # Log notification connection
        audit_service.log_activity(
            db=db,
            user_id=user.id,
            action="notifications_websocket_connected",
            resource_type="websocket",
            details="Connected to notifications WebSocket",
            severity="info"
        )

        # Keep connection alive and handle ping/pong
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": "2025-09-28T04:00:00Z"
                    }))

            except WebSocketDisconnect:
                logger.info(f"Notifications WebSocket disconnected for user {user.id}")
                break
            except Exception as e:
                logger.error(f"Error in notifications WebSocket: {e}")
                break

    except Exception as e:
        logger.error(f"Notifications WebSocket error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass
    finally:
        if user:
            audit_service.log_activity(
                db=db,
                user_id=user.id,
                action="notifications_websocket_disconnected",
                resource_type="websocket",
                details="Disconnected from notifications WebSocket",
                severity="info"
            )

# WebSocket status endpoints

@router.get("/ws/status")
async def get_websocket_status():
    """Get WebSocket connection status"""
    try:
        active_users = websocket_messaging_manager.get_active_users()

        return {
            "websocket_service": "active",
            "active_connections": len(active_users),
            "active_users": active_users,
            "server_time": "2025-09-28T04:00:00Z"
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WebSocket status")

@router.get("/ws/conversations/{conversation_id}/subscribers")
async def get_conversation_subscribers(conversation_id: int):
    """Get users currently subscribed to a conversation's updates"""
    try:
        subscribers = websocket_messaging_manager.get_conversation_subscribers(conversation_id)

        return {
            "conversation_id": conversation_id,
            "subscriber_count": len(subscribers),
            "subscribers": subscribers
        }
    except Exception as e:
        logger.error(f"Error getting conversation subscribers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscribers")

# WebSocket testing endpoints (for development)

@router.post("/ws/test/broadcast")
async def test_broadcast_message(
    message: str,
    conversation_id: Optional[int] = None
):
    """Test endpoint to broadcast message (development only)"""
    try:
        if conversation_id:
            # Broadcast to specific conversation
            await websocket_messaging_manager._broadcast_to_conversation(
                conversation_id,
                {
                    "type": "test_message",
                    "data": {
                        "message": message,
                        "from": "server_test",
                        "timestamp": "2025-09-28T04:00:00Z"
                    }
                }
            )
        else:
            # Broadcast to all active users
            active_users = websocket_messaging_manager.get_active_users()
            for user_id in active_users:
                await websocket_messaging_manager._send_to_user(user_id, {
                    "type": "test_message",
                    "data": {
                        "message": message,
                        "from": "server_test",
                        "timestamp": "2025-09-28T04:00:00Z"
                    }
                })

        return {
            "success": True,
            "message": "Test message broadcasted",
            "recipients": len(websocket_messaging_manager.get_conversation_subscribers(conversation_id)) if conversation_id else len(websocket_messaging_manager.get_active_users())
        }
    except Exception as e:
        logger.error(f"Error broadcasting test message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast test message")