"""Tests for sprint planning and implementation API endpoints.

Agent spawning is mocked since we don't have real Claude Code in tests.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for project files."""
    tmpdir = tempfile.mkdtemp(prefix="test_sprint_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_common_dir():
    """Create a temporary common directory with template files."""
    tmpdir = tempfile.mkdtemp(prefix="test_common_")
    Path(tmpdir).joinpath("plan_phase.md").write_text(
        "# Sprint Plan Template\n\n## 스프린트 개요\n| 스프린트 | 기간 | 목표 |\n",
        encoding="utf-8",
    )
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestSprintPlanAPI:
    """POST /api/projects/{id}/sprint tests."""

    @pytest.mark.asyncio
    async def test_sprint_start_success(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Starting sprint planning should return 202 with task ID."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "sprint_test"
            project_path.mkdir(parents=True)
            (project_path / "PRD.md").write_text("# PRD\n\nTest project PRD.", encoding="utf-8")
            (project_path / ".claude" / "agent").mkdir(parents=True)
            (project_path / ".claude" / "agent" / "pm-agent.md").write_text("# PM\n")

            p = Project(
                name="Sprint Test",
                idea_text="Test idea",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.sprint_service.asyncio.create_task") as mock_task:
                response = await client.post(f"/api/projects/{project_id}/sprint")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "sprint_planning_started"
        assert "task_id" in data
        assert data["task_id"] > 0
        assert mock_task.called

    @pytest.mark.asyncio
    async def test_sprint_with_additional_instructions(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Sprint planning with additional instructions should work."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "sprint_add"
            project_path.mkdir(parents=True)
            (project_path / "PRD.md").write_text("# PRD\n", encoding="utf-8")

            p = Project(
                name="Sprint Additional",
                idea_text="Test",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.sprint_service.asyncio.create_task"):
                response = await client.post(
                    f"/api/projects/{project_id}/sprint",
                    json={"additional_instructions": "Backend first approach"},
                )

        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_sprint_wrong_status(self, client, db_engine):
        """Sprint from wrong status should return 400."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(
                name="Wrong",
                idea_text="Test",
                status="created",
                project_path="/tmp/wrong",
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(f"/api/projects/{project_id}/sprint")
        assert response.status_code == 400
        assert "created" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_sprint_not_found(self, client):
        """Sprint for non-existent project should return 404."""
        response = await client.post("/api/projects/999/sprint")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_sprint_updates_project_status(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Sprint planning should keep project status as 'sprint_planning'."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "sprint_status"
            project_path.mkdir(parents=True)
            (project_path / "PRD.md").write_text("# PRD\n", encoding="utf-8")

            p = Project(
                name="Sprint Status",
                idea_text="Test",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.sprint_service.asyncio.create_task"):
                await client.post(f"/api/projects/{project_id}/sprint")

        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.json()["status"] == "sprint_planning"

    @pytest.mark.asyncio
    async def test_sprint_from_reviewing_status(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Sprint planning should also be allowed from 'reviewing' status."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "sprint_review"
            project_path.mkdir(parents=True)
            (project_path / "PRD.md").write_text("# PRD\n", encoding="utf-8")

            p = Project(
                name="Sprint Review",
                idea_text="Test",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.sprint_service.asyncio.create_task"):
                response = await client.post(f"/api/projects/{project_id}/sprint")

        assert response.status_code == 202


class TestImplementAPI:
    """POST /api/projects/{id}/implement tests."""

    @pytest.mark.asyncio
    async def test_implement_start_success(self, client, db_engine, temp_project_dir):
        """Starting implementation should return 202 with task ID."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "impl_test"
            project_path.mkdir(parents=True)
            (project_path / "PRD.md").write_text("# PRD\n", encoding="utf-8")
            (project_path / "Phase.md").write_text("# Phase\n### S1: Setup\n", encoding="utf-8")

            p = Project(
                name="Impl Test",
                idea_text="Test idea",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service.asyncio.create_task") as mock_task:
            response = await client.post(f"/api/projects/{project_id}/implement")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "implementation_started"
        assert "task_id" in data
        assert data["task_id"] > 0
        assert mock_task.called

    @pytest.mark.asyncio
    async def test_implement_with_custom_retries(self, client, db_engine, temp_project_dir):
        """Implementation with custom max retries should work."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "impl_retries"
            project_path.mkdir(parents=True)

            p = Project(
                name="Retries Test",
                idea_text="Test",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service.asyncio.create_task"):
            response = await client.post(
                f"/api/projects/{project_id}/implement",
                json={"max_retries": 5},
            )

        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_implement_invalid_retries(self, client, db_engine, temp_project_dir):
        """Implementation with invalid max_retries should return 422."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "impl_invalid"
            project_path.mkdir(parents=True)

            p = Project(
                name="Invalid Retries",
                idea_text="Test",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(
            f"/api/projects/{project_id}/implement",
            json={"max_retries": 0},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_implement_wrong_status(self, client, db_engine):
        """Implementation from wrong status should return 400."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(
                name="Wrong Impl",
                idea_text="Test",
                status="created",
                project_path="/tmp/wrong_impl",
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(f"/api/projects/{project_id}/implement")
        assert response.status_code == 400
        assert "created" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_implement_not_found(self, client):
        """Implementation for non-existent project should return 404."""
        response = await client.post("/api/projects/999/implement")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_implement_updates_status(self, client, db_engine, temp_project_dir):
        """Implementation should update project status to 'implementing'."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "impl_status"
            project_path.mkdir(parents=True)

            p = Project(
                name="Status Impl",
                idea_text="Test",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service.asyncio.create_task"):
            await client.post(f"/api/projects/{project_id}/implement")

        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.json()["status"] == "implementing"

    @pytest.mark.asyncio
    async def test_implement_from_implementing_status(self, client, db_engine, temp_project_dir):
        """Implementation should be allowed to restart from 'implementing' status."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "impl_restart"
            project_path.mkdir(parents=True)

            p = Project(
                name="Restart Impl",
                idea_text="Test",
                status="implementing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service.asyncio.create_task"):
            response = await client.post(f"/api/projects/{project_id}/implement")

        assert response.status_code == 202


class TestSprintImplementIntegration:
    """Integration tests for the full sprint → implement flow."""

    @pytest.mark.asyncio
    async def test_full_sprint_implement_flow(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Test the full flow: approve → sprint plan → implement."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "full_flow"
            project_path.mkdir(parents=True)
            (project_path / ".claude" / "agent").mkdir(parents=True)

            p = Project(
                name="Full Flow",
                idea_text="Build a todo app",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        # Step 1: Approve plan
        approve_resp = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# Todo App PRD\n\n## Features\n- CRUD todos"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # Verify PRD.md created
        assert (Path(temp_project_dir) / "full_flow" / "PRD.md").exists()

        # Step 2: Start sprint planning
        with patch("app.services.sprint_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.sprint_service.asyncio.create_task"):
                sprint_resp = await client.post(f"/api/projects/{project_id}/sprint")
        assert sprint_resp.status_code == 202

        # Step 3: Start implementation
        with patch("app.services.sprint_service.asyncio.create_task"):
            impl_resp = await client.post(f"/api/projects/{project_id}/implement")
        assert impl_resp.status_code == 202

        # Verify final status
        proj_resp = await client.get(f"/api/projects/{project_id}")
        assert proj_resp.json()["status"] == "implementing"

    @pytest.mark.asyncio
    async def test_sprint_creates_tasks_in_db(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Sprint planning should create a PM task in database."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "tasks_flow"
            project_path.mkdir(parents=True)
            (project_path / "PRD.md").write_text("# PRD\n", encoding="utf-8")

            p = Project(
                name="Tasks Flow",
                idea_text="Test",
                status="sprint_planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.sprint_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.sprint_service.asyncio.create_task"):
                sprint_resp = await client.post(f"/api/projects/{project_id}/sprint")

        task_id = sprint_resp.json()["task_id"]

        # Verify task in DB
        tasks_resp = await client.get(f"/api/projects/{project_id}/tasks")
        tasks = tasks_resp.json()["tasks"]
        pm_tasks = [t for t in tasks if t["agent"] == "pm"]
        assert len(pm_tasks) >= 1
        assert any(t["id"] == task_id for t in pm_tasks)
