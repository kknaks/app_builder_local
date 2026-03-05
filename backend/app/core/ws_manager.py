"""WebSocket connection manager.

Manages WebSocket connections for chat and log streaming per project.
"""

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by project.

    Supports two channel types: 'chat' and 'logs'.
    """

    def __init__(self) -> None:
        # {project_id: {channel: [websocket, ...]}}
        self._connections: dict[int, dict[str, list[WebSocket]]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, project_id: int, channel: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections[project_id][channel].append(websocket)
        logger.info("WS connected: project=%d channel=%s", project_id, channel)

    async def disconnect(self, websocket: WebSocket, project_id: int, channel: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            conns = self._connections[project_id][channel]
            if websocket in conns:
                conns.remove(websocket)
            # Cleanup empty entries
            if not conns:
                del self._connections[project_id][channel]
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info("WS disconnected: project=%d channel=%s", project_id, channel)

    async def broadcast(self, project_id: int, channel: str, data: dict) -> None:
        """Broadcast a message to all connections in a project/channel."""
        message = json.dumps(data)
        async with self._lock:
            connections = list(self._connections.get(project_id, {}).get(channel, []))

        dead = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Cleanup dead connections
        for ws in dead:
            await self.disconnect(ws, project_id, channel)

    async def send_personal(self, websocket: WebSocket, data: dict) -> None:
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            logger.warning("Failed to send personal message")

    def get_connection_count(self, project_id: int, channel: str) -> int:
        """Get number of active connections for a project/channel."""
        return len(self._connections.get(project_id, {}).get(channel, []))


# Global connection manager instance
ws_manager = ConnectionManager()
