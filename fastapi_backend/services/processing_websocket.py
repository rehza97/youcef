"""
WebSocket manager for real-time processing updates
"""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket
from services.background_processor import background_processor

logger = logging.getLogger(__name__)


class ProcessingWebSocketManager:
    """Manages WebSocket connections for processing updates"""

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.processing_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a user to processing updates"""
        # Note: WebSocket should already be accepted by the caller

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected to processing updates")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Disconnect a user from processing updates"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove from processing connections
        to_delete = []
        for task_id, connections in list(self.processing_connections.items()):
            connections.discard(websocket)
            if not connections:
                to_delete.append(task_id)
        for task_id in to_delete:
            del self.processing_connections[task_id]

        logger.info(f"User {user_id} disconnected from processing updates")

    async def connect_to_task(self, websocket: WebSocket, task_id: str):
        """Connect to specific task updates"""
        if task_id not in self.processing_connections:
            self.processing_connections[task_id] = set()

        self.processing_connections[task_id].add(websocket)
        logger.info(f"WebSocket connected to task {task_id}")

    async def send_task_update(self, task_id: str, update_data: dict):
        """Send update to all connections monitoring a specific task"""
        # Only log every 10th update to reduce spam
        if not hasattr(self, '_update_count'):
            self._update_count = {}
        self._update_count[task_id] = self._update_count.get(task_id, 0) + 1

        # Log every 10th update
        should_log = self._update_count[task_id] % 10 == 1

        if should_log:
            logger.info(
                f"📡 Sending task update #{self._update_count[task_id]} for task_id: {task_id}")

        message = {
            "type": "processing_update",
            "task_id": task_id,
            "data": update_data
        }

        # Send to task-specific connections
        if task_id in self.processing_connections:
            disconnected = set()
            for websocket in self.processing_connections[task_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to send to task-specific WebSocket: {e}")
                    disconnected.add(websocket)

            # Remove disconnected websockets
            for websocket in disconnected:
                self.processing_connections[task_id].discard(websocket)

        # Also send to all active user connections (fallback)
        total_sent = 0
        for user_id, connections in self.active_connections.items():
            disconnected = set()
            for websocket in connections:
                try:
                    await websocket.send_text(json.dumps(message))
                    total_sent += 1
                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to send to user {user_id} WebSocket: {e}")
                    disconnected.add(websocket)

            # Remove disconnected websockets
            for websocket in disconnected:
                connections.discard(websocket)

        # Only log summary every 10th update
        if should_log:
            logger.info(
                f"📡 Task update #{self._update_count[task_id]} completed - sent to {total_sent} connections")

        if total_sent == 0 and should_log:
            logger.warning(
                f"⚠️ No active connections found for task_id: {task_id}")

    async def send_user_update(self, user_id: int, update_data: dict):
        """Send update to a specific user"""
        if user_id in self.active_connections:
            message = {
                "type": "user_update",
                "data": update_data
            }

            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.add(websocket)

            # Remove disconnected websockets
            for websocket in disconnected:
                self.active_connections[user_id].discard(websocket)

    async def broadcast_processing_update(self, update_data: dict):
        """Broadcast processing update to all connected users"""
        message = {
            "type": "global_processing_update",
            "data": update_data
        }

        all_connections = set()
        for user_connections in self.active_connections.values():
            all_connections.update(user_connections)

        disconnected = set()
        for websocket in all_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.add(websocket)

        # Clean up disconnected connections
        empty_users = []
        for user_id, connections in list(self.active_connections.items()):
            connections -= disconnected
            if not connections:
                empty_users.append(user_id)
        for user_id in empty_users:
            del self.active_connections[user_id]


# Global WebSocket manager instance
processing_ws_manager = ProcessingWebSocketManager()
