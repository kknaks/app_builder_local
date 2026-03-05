"""Tests for Docker run/stop/status API endpoints."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with backend/frontend structure."""
    tmpdir = tempfile.mkdtemp(prefix="test_docker_api_")
    path = Path(tmpdir)

    # Create backend structure
    backend = path / "test_project" / "backend"
    backend.mkdir(parents=True)
    (backend / "pyproject.toml").write_text("[project]\nname='test'\n")
    (backend / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")

    # Create frontend structure
    frontend = path / "test_project" / "frontend"
    frontend.mkdir(parents=True)
    (frontend / "package.json").write_text('{"name": "test-frontend"}\n')

    yield path
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_common_dir():
    """Create a temporary common directory."""
    tmpdir = tempfile.mkdtemp(prefix="test_common_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


async def _create_test_project(client, temp_project_dir, temp_common_dir):
    """Helper to create a test project."""
    with (
        patch(
            "app.services.project_service._get_projects_base_dir",
            return_value=temp_project_dir,
        ),
        patch(
            "app.services.project_service._get_common_dir",
            return_value=Path(temp_common_dir),
        ),
    ):
        response = await client.post(
            "/api/projects",
            json={"name": "Test Project", "idea_text": "A test project"},
        )
    return response.json()


class TestRunProject:
    """POST /api/projects/{id}/run tests."""

    @pytest.mark.asyncio
    async def test_run_nonexistent_project(self, client):
        """Should return 404 for non-existent project."""
        response = await client.post("/api/projects/999/run")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_run_project_generates_compose(self, client, temp_project_dir, temp_common_dir):
        """Run should generate docker-compose.yml and attempt docker up."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]
        project_path = project_data["project_path"]

        # Create backend/frontend dirs in the project path
        (Path(project_path) / "backend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "backend" / "pyproject.toml").write_text("[project]\n")
        (Path(project_path) / "frontend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "frontend" / "package.json").write_text("{}\n")

        # Mock docker_compose_up to avoid actual Docker calls
        mock_result = {
            "status": "running",
            "output": "Container started",
            "containers": [
                {
                    "name": "test_backend",
                    "service": "backend",
                    "state": "running",
                    "status": "Up 5 seconds",
                    "ports": "0.0.0.0:31000->8000/tcp",
                },
            ],
            "urls": {"backend": "http://localhost:31000"},
        }

        with patch("app.routers.docker.docker_compose_up", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(
                f"/api/projects/{project_id}/run",
                json={"backend_port": 31000, "frontend_port": 31001, "db_port": 31002},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "urls" in data

        # Verify docker-compose.yml was created
        compose_path = Path(project_path) / "docker-compose.yml"
        assert compose_path.exists()

    @pytest.mark.asyncio
    async def test_run_project_docker_error(self, client, temp_project_dir, temp_common_dir):
        """Should return error status when Docker fails."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]
        project_path = project_data["project_path"]

        # Create minimal project structure
        (Path(project_path) / "backend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "backend" / "pyproject.toml").write_text("[project]\n")

        mock_result = {
            "status": "error",
            "error": "Docker daemon not running",
        }

        with patch("app.routers.docker.docker_compose_up", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(f"/api/projects/{project_id}/run")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data

    @pytest.mark.asyncio
    async def test_run_project_with_custom_ports(self, client, temp_project_dir, temp_common_dir):
        """Should use custom ports when specified."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]
        project_path = project_data["project_path"]

        (Path(project_path) / "backend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "backend" / "pyproject.toml").write_text("[project]\n")

        mock_result = {
            "status": "running",
            "output": "Started",
            "containers": [],
            "urls": {"backend": "http://localhost:35000"},
        }

        with patch("app.routers.docker.docker_compose_up", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(
                f"/api/projects/{project_id}/run",
                json={"backend_port": 35000, "db_port": 35001},
            )

        assert response.status_code == 200


class TestStopProject:
    """POST /api/projects/{id}/stop tests."""

    @pytest.mark.asyncio
    async def test_stop_nonexistent_project(self, client):
        """Should return 404 for non-existent project."""
        response = await client.post("/api/projects/999/stop")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stop_project_success(self, client, temp_project_dir, temp_common_dir):
        """Should stop containers successfully."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]

        mock_result = {
            "status": "stopped",
            "output": "Containers stopped",
        }

        with patch("app.routers.docker.docker_compose_down", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(f"/api/projects/{project_id}/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_stop_project_docker_error(self, client, temp_project_dir, temp_common_dir):
        """Should handle Docker stop errors gracefully."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]

        mock_result = {
            "status": "error",
            "error": "Docker daemon not running",
        }

        with patch("app.routers.docker.docker_compose_down", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(f"/api/projects/{project_id}/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestRunStatus:
    """GET /api/projects/{id}/run/status tests."""

    @pytest.mark.asyncio
    async def test_status_nonexistent_project(self, client):
        """Should return 404 for non-existent project."""
        response = await client.get("/api/projects/999/run/status")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_status_running_project(self, client, temp_project_dir, temp_common_dir):
        """Should return running status with container info."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]

        mock_result = {
            "status": "running",
            "containers": [
                {
                    "name": "test_backend",
                    "service": "backend",
                    "state": "running",
                    "status": "Up 30 seconds",
                    "ports": "0.0.0.0:31000->8000/tcp",
                },
                {
                    "name": "test_db",
                    "service": "db",
                    "state": "running",
                    "status": "Up 35 seconds (healthy)",
                    "ports": "0.0.0.0:31002->5432/tcp",
                },
            ],
            "urls": {
                "backend": "http://localhost:31000",
                "db": "http://localhost:31002",
            },
        }

        with patch("app.routers.docker.get_container_status", new_callable=AsyncMock, return_value=mock_result):
            response = await client.get(f"/api/projects/{project_id}/run/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert len(data["containers"]) == 2
        assert "backend" in data["urls"]

    @pytest.mark.asyncio
    async def test_status_stopped_project(self, client, temp_project_dir, temp_common_dir):
        """Should return stopped status when no containers are running."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]

        mock_result = {
            "status": "stopped",
            "containers": [],
            "urls": {},
        }

        with patch("app.routers.docker.get_container_status", new_callable=AsyncMock, return_value=mock_result):
            response = await client.get(f"/api/projects/{project_id}/run/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["containers"] == []

    @pytest.mark.asyncio
    async def test_status_not_configured(self, client, temp_project_dir, temp_common_dir):
        """Should return not_configured when no docker-compose.yml exists."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]

        mock_result = {
            "status": "not_configured",
            "containers": [],
            "urls": {},
        }

        with patch("app.routers.docker.get_container_status", new_callable=AsyncMock, return_value=mock_result):
            response = await client.get(f"/api/projects/{project_id}/run/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_configured"


class TestReRun:
    """Tests for project re-run (stop then run again)."""

    @pytest.mark.asyncio
    async def test_rerun_project(self, client, temp_project_dir, temp_common_dir):
        """Should support stopping and re-running a project."""
        project_data = await _create_test_project(client, temp_project_dir, temp_common_dir)
        project_id = project_data["id"]
        project_path = project_data["project_path"]

        (Path(project_path) / "backend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "backend" / "pyproject.toml").write_text("[project]\n")

        # Stop first
        with patch(
            "app.routers.docker.docker_compose_down",
            new_callable=AsyncMock,
            return_value={"status": "stopped"},
        ):
            stop_response = await client.post(f"/api/projects/{project_id}/stop")
        assert stop_response.json()["status"] == "stopped"

        # Re-run
        with patch(
            "app.routers.docker.docker_compose_up",
            new_callable=AsyncMock,
            return_value={"status": "running", "output": "", "containers": [], "urls": {}},
        ):
            run_response = await client.post(f"/api/projects/{project_id}/run")
        assert run_response.json()["status"] == "running"
