"""
WebSocket support for FS Reconciliation Agents API v2.

This module provides real-time communication for:
- Live exception updates
- Real-time processing status
- Live dashboard updates
- Notification streaming
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel

from src.core.utils.security_utils.authentication import get_current_user_from_token
from src.core.services.caching.redis_cache import get_cache_service

logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(connection_id)
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        logger.info(f"WebSocket connected - ID: {connection_id}, User: {user_id}")
    
    def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from user connections
        for user_id, connections in self.user_connections.items():
            if connection_id in connections:
                connections.remove(connection_id)
                if not connections:
                    del self.user_connections[user_id]
        
        # Remove metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(f"WebSocket disconnected - ID: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(json.dumps(message))
                self.connection_metadata[connection_id]["last_activity"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
                self.connection_metadata[connection_id]["last_activity"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    async def broadcast_to_user(self, message: Dict[str, Any], user_id: str):
        """Broadcast a message to all connections of a specific user."""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_topic(self, message: Dict[str, Any], topic: str):
        """Broadcast a message to all connections subscribed to a topic."""
        # This could be enhanced with a topic subscription system
        await self.broadcast({
            **message,
            "topic": topic
        })
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about active connections."""
        return {
            "total_connections": len(self.active_connections),
            "user_connections": len(self.user_connections),
            "connections": list(self.connection_metadata.keys())
        }


# Global connection manager
manager = ConnectionManager()


# WebSocket message models
class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None


class ExceptionUpdateMessage(BaseModel):
    """Exception update message."""
    exception_id: str
    status: str
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class ProcessingStatusMessage(BaseModel):
    """Processing status message."""
    job_id: str
    status: str
    progress: float
    message: str


class DashboardUpdateMessage(BaseModel):
    """Dashboard update message."""
    metrics: Dict[str, Any]
    exceptions_count: int
    resolution_rate: float


class NotificationMessage(BaseModel):
    """Notification message."""
    title: str
    message: str
    level: str  # info, warning, error, success
    action_url: Optional[str] = None


# WebSocket router
websocket_router = APIRouter()


@websocket_router.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """Main WebSocket endpoint for real-time updates."""
    await manager.connect(websocket, connection_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            await handle_websocket_message(connection_id, message)
            
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        manager.disconnect(connection_id)


@websocket_router.websocket("/ws/authenticated/{connection_id}")
async def authenticated_websocket_endpoint(
    websocket: WebSocket, 
    connection_id: str,
    token: str
):
    """Authenticated WebSocket endpoint."""
    try:
        # Validate token
        user = await get_current_user_from_token(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        await manager.connect(websocket, connection_id, user.username)
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "welcome",
            "data": {
                "message": f"Welcome {user.username}!",
                "user_id": user.username,
                "connection_id": connection_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_websocket_message(connection_id, message)
            
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"Authenticated WebSocket error for {connection_id}: {e}")
        manager.disconnect(connection_id)


async def handle_websocket_message(connection_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping
        await manager.send_personal_message({
            "type": "pong",
            "data": {"timestamp": datetime.utcnow().isoformat()},
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
    
    elif message_type == "subscribe":
        # Handle subscription requests
        topic = message.get("data", {}).get("topic")
        if topic:
            await manager.send_personal_message({
                "type": "subscribed",
                "data": {"topic": topic},
                "timestamp": datetime.utcnow().isoformat()
            }, connection_id)
    
    elif message_type == "unsubscribe":
        # Handle unsubscription requests
        topic = message.get("data", {}).get("topic")
        if topic:
            await manager.send_personal_message({
                "type": "unsubscribed",
                "data": {"topic": topic},
                "timestamp": datetime.utcnow().isoformat()
            }, connection_id)
    
    else:
        # Unknown message type
        await manager.send_personal_message({
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"},
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)


# Broadcast functions for different types of updates
async def broadcast_exception_update(exception_update: ExceptionUpdateMessage):
    """Broadcast exception update to all connected clients."""
    message = {
        "type": "exception_update",
        "data": exception_update.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


async def broadcast_processing_status(processing_status: ProcessingStatusMessage):
    """Broadcast processing status update."""
    message = {
        "type": "processing_status",
        "data": processing_status.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


async def broadcast_dashboard_update(dashboard_update: DashboardUpdateMessage):
    """Broadcast dashboard update."""
    message = {
        "type": "dashboard_update",
        "data": dashboard_update.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


async def broadcast_notification(notification: NotificationMessage, user_id: Optional[str] = None):
    """Broadcast notification."""
    message = {
        "type": "notification",
        "data": notification.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_id:
        await manager.broadcast_to_user(message, user_id)
    else:
        await manager.broadcast(message)


# WebSocket management endpoints
@websocket_router.get("/ws/status")
async def get_websocket_status():
    """Get WebSocket connection status."""
    return {
        "status": "active",
        "connections": manager.get_connection_info(),
        "timestamp": datetime.utcnow().isoformat()
    }


@websocket_router.post("/ws/broadcast")
async def broadcast_message(message: WebSocketMessage):
    """Broadcast a message to all connected clients."""
    await manager.broadcast(message.dict())
    return {"status": "broadcasted", "message": "Message broadcasted successfully"}


@websocket_router.post("/ws/broadcast/user/{user_id}")
async def broadcast_to_user(user_id: str, message: WebSocketMessage):
    """Broadcast a message to a specific user."""
    await manager.broadcast_to_user(message.dict(), user_id)
    return {"status": "broadcasted", "message": f"Message broadcasted to user {user_id}"}


# Background task for periodic updates
async def periodic_dashboard_updates():
    """Send periodic dashboard updates to connected clients."""
    while True:
        try:
            # Get latest dashboard data
            cache_service = get_cache_service()
            dashboard_data = await cache_service.get("analytics:dashboard:main")
            
            if dashboard_data:
                await broadcast_dashboard_update(DashboardUpdateMessage(
                    metrics=dashboard_data.get("metrics", {}),
                    exceptions_count=dashboard_data.get("exceptions_count", 0),
                    resolution_rate=dashboard_data.get("resolution_rate", 0.0)
                ))
            
            # Wait for next update
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in periodic dashboard updates: {e}")
            await asyncio.sleep(60)  # Wait longer on error


# Start background task
@websocket_router.on_event("startup")
async def start_background_tasks():
    """Start background tasks for WebSocket updates."""
    asyncio.create_task(periodic_dashboard_updates())
    logger.info("WebSocket background tasks started")
