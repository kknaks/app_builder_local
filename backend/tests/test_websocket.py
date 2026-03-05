"""Tests for WebSocket endpoints."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.ws_manager import ConnectionManager
from app.database.session import get_db
from app.main import app
from app.models.project import Project


@pytest.fixture
async def ws_project(db_engine):
    """Create a project for WebSocket tests."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="WS Test", idea_text="test", status="created", project_path="/tmp/ws_test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


@pytest.fixture
def sync_client(db_engine):
    """Synchronous test client for WebSocket testing with proper DB override."""
    from starlette.testclient import TestClient

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    # Also override the module-level async_session used in websocket handler
    import app.database.session as db_module

    original_async_session = db_module.async_session

    # Override async_session at module level for WS handlers
    db_module.async_session = session_factory

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db_module.async_session = original_async_session


class TestChatWebSocket:
    """Tests for /ws/projects/{id}/chat."""

    def test_ping_pong(self, sync_client, ws_project):
        """Test ping/pong keepalive."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_send_message(self, sync_client, ws_project):
        """Test sending a chat message."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_json({
                "type": "message",
                "agent": "pm",
                "content": "Hello agent!",
            })
            data = ws.receive_json()
            assert data["type"] == "message"
            assert data["agent"] == "pm"
            assert data["content"] == "Hello agent!"
            assert data["role"] == "user"

    def test_switch_agent(self, sync_client, ws_project):
        """Test switching agents."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_json({"type": "switch_agent", "agent": "backend"})
            data = ws.receive_json()
            assert data["type"] == "agent_switched"
            assert data["agent"] == "backend"

    def test_switch_agent_missing_name(self, sync_client, ws_project):
        """Test switch_agent without agent name."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_json({"type": "switch_agent"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Missing agent name" in data["error"]

    def test_empty_message(self, sync_client, ws_project):
        """Test sending empty message content."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_json({"type": "message", "agent": "pm", "content": ""})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Empty message" in data["error"]

    def test_invalid_json(self, sync_client, ws_project):
        """Test sending invalid JSON."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_text("not json")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["error"]

    def test_unknown_type(self, sync_client, ws_project):
        """Test unknown message type."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/chat") as ws:
            ws.send_json({"type": "unknown_type"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Unknown message type" in data["error"]


class TestLogWebSocket:
    """Tests for /ws/projects/{id}/logs."""

    def test_ping_pong(self, sync_client, ws_project):
        """Test ping/pong on log endpoint."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/logs") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_read_only(self, sync_client, ws_project):
        """Test that log endpoint is read-only."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/logs") as ws:
            ws.send_json({"type": "message", "content": "test"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "read-only" in data["error"]

    def test_invalid_json(self, sync_client, ws_project):
        """Test invalid JSON on log endpoint."""
        with sync_client.websocket_connect(f"/ws/projects/{ws_project.id}/logs") as ws:
            ws.send_text("not json")
            data = ws.receive_json()
            assert data["type"] == "error"


class TestWSManager:
    """Tests for the WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_initial_count(self):
        """Test initial connection count is zero."""
        mgr = ConnectionManager()
        assert mgr.get_connection_count(1, "chat") == 0

    @pytest.mark.asyncio
    async def test_connection_count_nonexistent(self):
        """Test connection count for non-existent project."""
        mgr = ConnectionManager()
        assert mgr.get_connection_count(999, "chat") == 0
        assert mgr.get_connection_count(999, "logs") == 0

    @pytest.mark.asyncio
    async def test_broadcast_empty(self):
        """Test broadcasting to empty project doesn't error."""
        mgr = ConnectionManager()
        await mgr.broadcast(999, "chat", {"type": "test"})
