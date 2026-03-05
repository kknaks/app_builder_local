"""Tests for project CRUD API endpoints."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for project files."""
    tmpdir = tempfile.mkdtemp(prefix="test_projects_")
    yield tmpdir
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_common_dir():
    """Create a temporary common directory with template files."""
    tmpdir = tempfile.mkdtemp(prefix="test_common_")
    # Create sample template files
    agent_dir = Path(tmpdir) / ".claude" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "pm-agent.md").write_text("# PM Agent Template\n")
    (agent_dir / "planner-agent.md").write_text("# Planner Agent Template\n")

    skill_dir = Path(tmpdir) / ".claude" / "skills"
    skill_dir.mkdir(parents=True)
    (skill_dir / "pm.md").write_text("# PM Skill Template\n")

    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestCreateProject:
    """POST /api/projects tests."""

    @pytest.mark.asyncio
    async def test_create_project_success(self, client, temp_project_dir, temp_common_dir):
        """Creating a project should return 201 with project data."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            response = await client.post(
                "/api/projects",
                json={"name": "Test App", "idea_text": "A test application idea"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test App"
        assert data["idea_text"] == "A test application idea"
        assert data["status"] == "created"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_project_creates_directory(self, client, temp_project_dir, temp_common_dir):
        """Creating a project should create the project directory."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            await client.post(
                "/api/projects",
                json={"name": "My App", "idea_text": "An awesome idea"},
            )

        project_dir = Path(temp_project_dir) / "my_app"
        assert project_dir.exists()

    @pytest.mark.asyncio
    async def test_create_project_creates_idea_md(self, client, temp_project_dir, temp_common_dir):
        """Creating a project should create idea.md with the idea text."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            await client.post(
                "/api/projects",
                json={"name": "My App", "idea_text": "An awesome idea"},
            )

        idea_file = Path(temp_project_dir) / "my_app" / "idea.md"
        assert idea_file.exists()
        content = idea_file.read_text()
        assert "An awesome idea" in content

    @pytest.mark.asyncio
    async def test_create_project_creates_agent_files(self, client, temp_project_dir, temp_common_dir):
        """Creating a project should create agent definition files."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            await client.post(
                "/api/projects",
                json={"name": "My App", "idea_text": "An awesome idea"},
            )

        project_dir = Path(temp_project_dir) / "my_app"

        # Check agent files exist
        for agent in ["pm-agent.md", "planner-agent.md", "backend-agent.md", "frontend-agent.md", "design-agent.md"]:
            assert (project_dir / ".claude" / "agent" / agent).exists(), f"Missing agent file: {agent}"

        # Check skill files exist
        for skill in ["pm.md", "planner.md", "backend.md", "frontend.md", "design.md"]:
            assert (project_dir / ".claude" / "skills" / skill).exists(), f"Missing skill file: {skill}"

    @pytest.mark.asyncio
    async def test_create_project_copies_from_common(self, client, temp_project_dir, temp_common_dir):
        """Agent files should be copied from common/ when available."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            await client.post(
                "/api/projects",
                json={"name": "My App", "idea_text": "An awesome idea"},
            )

        project_dir = Path(temp_project_dir) / "my_app"
        # pm-agent.md was in common, should be copied
        content = (project_dir / ".claude" / "agent" / "pm-agent.md").read_text()
        assert "PM Agent Template" in content

        # pm.md skill was in common, should be copied
        skill_content = (project_dir / ".claude" / "skills" / "pm.md").read_text()
        assert "PM Skill Template" in skill_content

    @pytest.mark.asyncio
    async def test_create_project_generates_defaults_when_no_common(self, client, temp_project_dir):
        """When common/ templates don't exist, default content should be generated."""
        empty_common = Path(temp_project_dir) / "empty_common"
        empty_common.mkdir()

        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=empty_common),
        ):
            await client.post(
                "/api/projects",
                json={"name": "My App", "idea_text": "An idea"},
            )

        project_dir = Path(temp_project_dir) / "my_app"
        content = (project_dir / ".claude" / "agent" / "backend-agent.md").read_text()
        assert "Auto-generated" in content

    @pytest.mark.asyncio
    async def test_create_project_validation_empty_name(self, client):
        """Empty name should return 422."""
        response = await client.post(
            "/api/projects",
            json={"name": "", "idea_text": "An idea"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_project_validation_missing_fields(self, client):
        """Missing required fields should return 422."""
        response = await client.post("/api/projects", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_project_name_sanitization(self, client, temp_project_dir, temp_common_dir):
        """Project directory name should be sanitized."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            response = await client.post(
                "/api/projects",
                json={"name": "My Cool App!", "idea_text": "An idea"},
            )

        assert response.status_code == 201
        # Should sanitize to lowercase with underscores
        project_dir = Path(temp_project_dir) / "my_cool_app"
        assert project_dir.exists()


class TestListProjects:
    """GET /api/projects tests."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        """When no projects exist, should return empty list."""
        response = await client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_projects(self, client, temp_project_dir, temp_common_dir):
        """Should list all created projects."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            await client.post(
                "/api/projects",
                json={"name": "App One", "idea_text": "First idea"},
            )
            await client.post(
                "/api/projects",
                json={"name": "App Two", "idea_text": "Second idea"},
            )

        response = await client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["projects"]) == 2


class TestGetProject:
    """GET /api/projects/{id} tests."""

    @pytest.mark.asyncio
    async def test_get_existing_project(self, client, temp_project_dir, temp_common_dir):
        """Should return project details for valid ID."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            create_response = await client.post(
                "/api/projects",
                json={"name": "Test App", "idea_text": "Test idea"},
            )

        project_id = create_response.json()["id"]
        response = await client.get(f"/api/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test App"
        assert data["idea_text"] == "Test idea"

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, client):
        """Should return 404 for non-existent project."""
        response = await client.get("/api/projects/999")

        assert response.status_code == 404


class TestDeleteProject:
    """DELETE /api/projects/{id} tests."""

    @pytest.mark.asyncio
    async def test_delete_project(self, client, temp_project_dir, temp_common_dir):
        """Deleting a project should remove it from DB and filesystem."""
        with (
            patch("app.services.project_service._get_projects_base_dir", return_value=Path(temp_project_dir)),
            patch("app.services.project_service._get_common_dir", return_value=Path(temp_common_dir)),
        ):
            create_response = await client.post(
                "/api/projects",
                json={"name": "Delete Me", "idea_text": "To be deleted"},
            )

        project_id = create_response.json()["id"]
        project_path = Path(create_response.json()["project_path"])
        assert project_path.exists()

        response = await client.delete(f"/api/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["id"] == project_id

        # Directory should be removed
        assert not project_path.exists()

        # DB record should be gone
        get_response = await client.get(f"/api/projects/{project_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_project(self, client):
        """Deleting a non-existent project should return 404."""
        response = await client.delete("/api/projects/999")
        assert response.status_code == 404
