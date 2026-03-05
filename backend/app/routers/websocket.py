"""WebSocket router — chat and log streaming endpoints."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import ws_manager
from app.services.chat_service import save_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _get_ws_db():
    """Dependency for WebSocket DB session (not using Depends in WS)."""
    from app.database.session import async_session

    async with async_session() as session:
        yield session


@router.websocket("/ws/projects/{project_id}/chat")
async def websocket_chat(
    websocket: WebSocket,
    project_id: int,
):
    """WebSocket endpoint for user↔agent chat.

    Message protocol:
    - Client sends: {"type": "message", "agent": "pm", "content": "..."}
    - Client sends: {"type": "switch_agent", "agent": "backend"}
    - Client sends: {"type": "ping"}
    - Server sends: {"type": "message", "agent": "pm", "content": "...", "role": "user|assistant"}
    - Server sends: {"type": "agent_switched", "agent": "backend"}
    - Server sends: {"type": "pong"}
    - Server sends: {"type": "error", "error": "..."}
    """
    await ws_manager.connect(websocket, project_id, "chat")
    current_agent = "pm"  # Default agent

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws_manager.send_personal(
                    websocket,
                    {"type": "error", "error": "Invalid JSON"},
                )
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})
                continue

            if msg_type == "switch_agent":
                new_agent = data.get("agent", "")
                if new_agent:
                    current_agent = new_agent
                    await ws_manager.send_personal(
                        websocket,
                        {"type": "agent_switched", "agent": current_agent},
                    )
                else:
                    await ws_manager.send_personal(
                        websocket,
                        {"type": "error", "error": "Missing agent name"},
                    )
                continue

            if msg_type == "message":
                agent = data.get("agent", current_agent)
                content = data.get("content", "")

                if not content:
                    await ws_manager.send_personal(
                        websocket,
                        {"type": "error", "error": "Empty message content"},
                    )
                    continue

                # Save user message to DB
                async for db in _get_ws_db():
                    await save_message(db, project_id, agent, "user", content)

                # Broadcast user message to all chat connections
                await ws_manager.broadcast(
                    project_id,
                    "chat",
                    {
                        "type": "message",
                        "agent": agent,
                        "content": content,
                        "role": "user",
                    },
                )
                continue

            # Unknown message type
            await ws_manager.send_personal(
                websocket,
                {"type": "error", "error": f"Unknown message type: {msg_type}"},
            )

    except WebSocketDisconnect:
        logger.debug("WebSocket chat disconnected gracefully: project=%d", project_id)
    except RuntimeError as e:
        # Handle "Unexpected ASGI message" when client disconnects mid-send
        if "disconnect" in str(e).lower() or "closed" in str(e).lower():
            logger.debug("WebSocket chat connection closed: project=%d", project_id)
        else:
            logger.error("WebSocket chat runtime error: %s", e)
    except Exception as e:
        logger.error("WebSocket chat error: %s", e)
    finally:
        await ws_manager.disconnect(websocket, project_id, "chat")


@router.websocket("/ws/projects/{project_id}/logs")
async def websocket_logs(
    websocket: WebSocket,
    project_id: int,
):
    """WebSocket endpoint for agent execution log streaming.

    Server pushes:
    - {"type": "log", "agent": "pm", "text": "...", "log_type": "info"}
    - {"type": "flow_update", "node_id": "...", "status": "active"}

    Client can send:
    - {"type": "ping"} → receives {"type": "pong"}
    """
    await ws_manager.connect(websocket, project_id, "logs")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws_manager.send_personal(
                    websocket,
                    {"type": "error", "error": "Invalid JSON"},
                )
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})
                continue

            # Logs endpoint is primarily server→client
            await ws_manager.send_personal(
                websocket,
                {"type": "error", "error": "Logs endpoint is read-only (except ping)"},
            )

    except WebSocketDisconnect:
        logger.debug("WebSocket logs disconnected gracefully: project=%d", project_id)
    except RuntimeError as e:
        if "disconnect" in str(e).lower() or "closed" in str(e).lower():
            logger.debug("WebSocket logs connection closed: project=%d", project_id)
        else:
            logger.error("WebSocket logs runtime error: %s", e)
    except Exception as e:
        logger.error("WebSocket logs error: %s", e)
    finally:
        await ws_manager.disconnect(websocket, project_id, "logs")


@router.websocket("/ws/projects/{project_id}/flow")
async def websocket_flow(
    websocket: WebSocket,
    project_id: int,
):
    """WebSocket endpoint for flow node status updates.

    Server pushes:
    - {"type": "flow_update", "nodes": [...], "edges": [...]}

    Client can send:
    - {"type": "ping"} → receives {"type": "pong"}
    """
    await ws_manager.connect(websocket, project_id, "flow")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws_manager.send_personal(
                    websocket,
                    {"type": "error", "error": "Invalid JSON"},
                )
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})
                continue

            await ws_manager.send_personal(
                websocket,
                {"type": "error", "error": "Flow endpoint is read-only (except ping)"},
            )

    except WebSocketDisconnect:
        logger.debug("WebSocket flow disconnected gracefully: project=%d", project_id)
    except RuntimeError as e:
        if "disconnect" in str(e).lower() or "closed" in str(e).lower():
            logger.debug("WebSocket flow connection closed: project=%d", project_id)
        else:
            logger.error("WebSocket flow runtime error: %s", e)
    except Exception as e:
        logger.error("WebSocket flow error: %s", e)
    finally:
        await ws_manager.disconnect(websocket, project_id, "flow")
