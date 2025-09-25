"""
WebSocket Connection Manager
"""
import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: {connection_type: websocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        # Store conversation connections: {conversation_id: [websocket]}
        self.conversation_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, connection_type: str = "general"):
        # Note: WebSocket should already be accepted by the caller
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][connection_type] = websocket
        logger.info(
            f"User {user_id} connected with {connection_type} connection")

    def disconnect(self, user_id: int, connection_type: str = "general"):
        if user_id in self.active_connections:
            if connection_type in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_type]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from {connection_type}")

    async def send_personal_message(self, message: str, user_id: int, connection_type: str = "general"):
        """Send message to specific user"""
        if user_id in self.active_connections:
            if connection_type in self.active_connections[user_id]:
                try:
                    await self.active_connections[user_id][connection_type].send_text(message)
                except Exception as e:
                    logger.error(
                        f"Error sending message to user {user_id}: {e}")
                    # Remove broken connection
                    self.disconnect(user_id, connection_type)

    async def connect_to_conversation(self, websocket: WebSocket, conversation_id: int):
        """Connect to a conversation"""
        # Don't call websocket.accept() here - it's already accepted in main.py
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = []
        self.conversation_connections[conversation_id].append(websocket)
        logger.info(f"WebSocket connected to conversation {conversation_id}")

    def disconnect_from_conversation(self, websocket: WebSocket, conversation_id: int):
        """Disconnect from a conversation"""
        if conversation_id in self.conversation_connections:
            if websocket in self.conversation_connections[conversation_id]:
                self.conversation_connections[conversation_id].remove(
                    websocket)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
        logger.info(
            f"WebSocket disconnected from conversation {conversation_id}")

    async def broadcast_to_conversation(
        self,
        message: str,
        conversation_id: int,
        exclude_websocket: Optional[WebSocket] = None
    ):
        """Broadcast message to all participants in a conversation"""
        if conversation_id in self.conversation_connections:
            for connection in self.conversation_connections[conversation_id]:
                if connection != exclude_websocket:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        logger.error(
                            f"Error broadcasting to conversation {conversation_id}: {e}")
                        self.conversation_connections[conversation_id].remove(
                            connection)

    def disconnect_all(self):
        """Disconnect all active connections"""
        logger.info("Disconnecting all WebSocket connections...")

        # Clear all active connections
        self.active_connections.clear()

        # Clear all conversation connections
        self.conversation_connections.clear()

        logger.info("All WebSocket connections disconnected")


# Create global instance
manager = ConnectionManager()
