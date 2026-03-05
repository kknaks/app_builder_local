"""Tests for planning flow API endpoints.

Tests plan, review, approve, and feedback endpoints.
Agent spawning is mocked since we don't have real Claude Code in tests.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project
from app.services.flow_node_service import get_flow_nodes, initialize_planning_flow


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for project files."""
    tmpdir = tempfile.mkdtemp(prefix="test_plan_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_common_dir():
    """Create a temporary common directory with template files."""
    tmpdir = tempfile.mkdtemp(prefix="test_common_")
    # Create plan_form.md
    Path(tmpdir).joinpath("plan_form.md").write_text(
        "# Test Plan Form\n\n## 1. 개요\n## 2. 기능\n", encoding="utf-8"
    )
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
async def db(db_engine):
    """Get a fresh DB session."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def project_with_dir(db, temp_project_dir):
    """Create a test project with actual directory."""
    project_path = Path(temp_project_dir) / "test_app"
    project_path.mkdir(parents=True)
    # Create agent file directory
    agent_dir = project_path / ".claude" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "planner-agent.md").write_text("# Planner\n")
    (agent_dir / "backend-agent.md").write_text("# Backend\n")
    (agent_dir / "frontend-agent.md").write_text("# Frontend\n")
    (agent_dir / "design-agent.md").write_text("# Design\n")

    p = Project(
        name="Test App",
        idea_text="A test application for planning",
        status="created",
        project_path=str(project_path),
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


class TestPlanStartAPI:
    """POST /api/projects/{id}/plan tests."""

    @pytest.mark.asyncio
    async def test_plan_start_success(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Starting planning should return 202 with task ID."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "plan_test"
            project_path.mkdir(parents=True)
            (project_path / ".claude" / "agent").mkdir(parents=True)
            (project_path / ".claude" / "agent" / "planner-agent.md").write_text("# Planner\n")

            p = Project(
                name="Plan Test",
                idea_text="Test idea",
                status="created",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        # Mock the agent spawn (background task)
        with patch("app.services.planning_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.planning_service.asyncio.create_task") as mock_create_task:
                response = await client.post(f"/api/projects/{project_id}/plan")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "planning_started"
        assert "task_id" in data
        assert data["task_id"] > 0
        assert mock_create_task.called

    @pytest.mark.asyncio
    async def test_plan_start_with_additional_context(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Starting planning with additional context should work."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "ctx_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Context Test",
                idea_text="Test idea",
                status="created",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.planning_service.asyncio.create_task"):
                response = await client.post(
                    f"/api/projects/{project_id}/plan",
                    json={"additional_context": "Focus on mobile-first design"},
                )

        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_plan_start_creates_flow_nodes(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Starting planning should create flow nodes for the dashboard."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "flow_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Flow Test",
                idea_text="Test idea",
                status="created",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.planning_service.asyncio.create_task"):
                await client.post(f"/api/projects/{project_id}/plan")

        # Check flow nodes were created
        async with session_factory() as session:
            nodes = await get_flow_nodes(session, project_id)
            assert len(nodes) == 6

    @pytest.mark.asyncio
    async def test_plan_start_updates_project_status(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Starting planning should update project status to 'planning'."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "status_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Status Test",
                idea_text="Test idea",
                status="created",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.planning_service.asyncio.create_task"):
                await client.post(f"/api/projects/{project_id}/plan")

        # Check project status
        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.json()["status"] == "planning"

    @pytest.mark.asyncio
    async def test_plan_start_wrong_status(self, client, db_engine):
        """Starting planning from wrong status should return 400."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(
                name="Wrong Status",
                idea_text="Test",
                status="sprint_planning",
                project_path="/tmp/wrong",
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(f"/api/projects/{project_id}/plan")
        assert response.status_code == 400
        assert "sprint_planning" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_plan_start_not_found(self, client):
        """Planning non-existent project should return 404."""
        response = await client.post("/api/projects/999/plan")
        assert response.status_code == 404


class TestReviewAPI:
    """POST /api/projects/{id}/review tests."""

    @pytest.mark.asyncio
    async def test_review_start_success(self, client, db_engine, temp_project_dir):
        """Starting review should return 202 with task IDs."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "review_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Review Test",
                idea_text="Test idea",
                status="planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service.asyncio.create_task"):
            response = await client.post(f"/api/projects/{project_id}/review")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "review_started"
        assert len(data["task_ids"]) == 3

    @pytest.mark.asyncio
    async def test_review_creates_three_tasks(self, client, db_engine, temp_project_dir):
        """Review should create 3 tasks (backend, frontend, design)."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "tasks_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Tasks Test",
                idea_text="Test idea",
                status="planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service.asyncio.create_task"):
            response = await client.post(f"/api/projects/{project_id}/review")

        task_ids = response.json()["task_ids"]
        assert len(task_ids) == 3

        # Verify tasks were created in DB
        tasks_resp = await client.get(f"/api/projects/{project_id}/tasks")
        tasks = tasks_resp.json()["tasks"]
        agents = {t["agent"] for t in tasks}
        assert "backend" in agents
        assert "frontend" in agents
        assert "design" in agents

    @pytest.mark.asyncio
    async def test_review_updates_project_status(self, client, db_engine, temp_project_dir):
        """Review should update project status to 'reviewing'."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "review_status"
            project_path.mkdir(parents=True)
            p = Project(
                name="Review Status",
                idea_text="Test",
                status="planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service.asyncio.create_task"):
            await client.post(f"/api/projects/{project_id}/review")

        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.json()["status"] == "reviewing"

    @pytest.mark.asyncio
    async def test_review_wrong_status(self, client, db_engine):
        """Review from wrong status should return 400."""
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

        response = await client.post(f"/api/projects/{project_id}/review")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_review_not_found(self, client):
        """Review non-existent project should return 404."""
        response = await client.post("/api/projects/999/review")
        assert response.status_code == 404


class TestApproveAPI:
    """POST /api/projects/{id}/approve tests."""

    @pytest.mark.asyncio
    async def test_approve_with_content(self, client, db_engine, temp_project_dir):
        """Approving with explicit PRD content should save it."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "approve_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Approve Test",
                idea_text="Test idea",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        prd_content = "# My PRD\n\nThis is the final PRD."
        response = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": prd_content},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert "PRD.md" in data["prd_path"]

        # Verify PRD.md was created
        prd_path = Path(temp_project_dir) / "approve_test" / "PRD.md"
        assert prd_path.exists()
        assert prd_path.read_text() == prd_content

    @pytest.mark.asyncio
    async def test_approve_updates_status_to_sprint_planning(self, client, db_engine, temp_project_dir):
        """Approving should update project status to 'sprint_planning'."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "status_approve"
            project_path.mkdir(parents=True)
            p = Project(
                name="Status Approve",
                idea_text="Test",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# PRD\n"},
        )

        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.json()["status"] == "sprint_planning"

    @pytest.mark.asyncio
    async def test_approve_without_content_uses_task_result(self, client, db_engine, temp_project_dir):
        """Approving without explicit content should use latest planner output."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "auto_approve"
            project_path.mkdir(parents=True)
            p = Project(
                name="Auto Approve",
                idea_text="Test idea for auto",
                status="planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

            # Create a completed planner task with result
            from app.services.agent_task_service import create_task, update_task_status

            task = await create_task(session, p.id, "planner", "Plan it")
            await update_task_status(session, task.id, "running")
            await update_task_status(
                session, task.id, "completed",
                result="# Generated PRD\n\nThis was generated by planner.",
            )

        response = await client.post(f"/api/projects/{project_id}/approve")
        assert response.status_code == 200

        prd_path = Path(temp_project_dir) / "auto_approve" / "PRD.md"
        assert prd_path.exists()
        content = prd_path.read_text()
        assert "Generated PRD" in content

    @pytest.mark.asyncio
    async def test_approve_without_content_fallback(self, client, db_engine, temp_project_dir):
        """Approving without content or task result should use idea text as fallback."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "fallback_approve"
            project_path.mkdir(parents=True)
            p = Project(
                name="Fallback",
                idea_text="My fallback idea",
                status="planning",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(f"/api/projects/{project_id}/approve")
        assert response.status_code == 200

        prd_path = Path(temp_project_dir) / "fallback_approve" / "PRD.md"
        assert prd_path.exists()
        content = prd_path.read_text()
        assert "My fallback idea" in content

    @pytest.mark.asyncio
    async def test_approve_wrong_status(self, client, db_engine):
        """Approving from wrong status should return 400."""
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

        response = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# PRD\n"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_not_found(self, client):
        """Approving non-existent project should return 404."""
        response = await client.post(
            "/api/projects/999/approve",
            json={"prd_content": "# PRD\n"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_updates_flow_node(self, client, db_engine, temp_project_dir):
        """Approving should update the approval flow node to completed."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "node_approve"
            project_path.mkdir(parents=True)
            p = Project(
                name="Node Approve",
                idea_text="Test",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

            # Initialize flow nodes
            await initialize_planning_flow(session, p.id)

        await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# PRD\n"},
        )

        # Check approval node is completed
        flow_resp = await client.get(f"/api/projects/{project_id}/flow")
        nodes = flow_resp.json()["nodes"]
        approval_node = next(n for n in nodes if n["node_type"] == "approval")
        assert approval_node["status"] == "completed"


class TestFeedbackAPI:
    """POST /api/projects/{id}/feedback tests."""

    @pytest.mark.asyncio
    async def test_feedback_success(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Sending feedback should return 200 with new task ID."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "feedback_test"
            project_path.mkdir(parents=True)
            p = Project(
                name="Feedback Test",
                idea_text="Test idea",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service.asyncio.create_task"):
            response = await client.post(
                f"/api/projects/{project_id}/feedback",
                json={"feedback": "결제 기능도 추가해주세요"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "feedback_sent"
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_feedback_updates_status_back_to_planning(self, client, db_engine, temp_project_dir):
        """Feedback should update project status back to 'planning'."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "fb_status"
            project_path.mkdir(parents=True)
            p = Project(
                name="FB Status",
                idea_text="Test",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service.asyncio.create_task"):
            await client.post(
                f"/api/projects/{project_id}/feedback",
                json={"feedback": "More features please"},
            )

        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.json()["status"] == "planning"

    @pytest.mark.asyncio
    async def test_feedback_resets_review_nodes(self, client, db_engine, temp_project_dir):
        """Feedback should reset review nodes to pending."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "fb_nodes"
            project_path.mkdir(parents=True)
            p = Project(
                name="FB Nodes",
                idea_text="Test",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

            # Create and complete review nodes
            from app.services.flow_node_service import update_node_status

            await initialize_planning_flow(session, p.id)
            await update_node_status(session, p.id, "review_be", "completed", broadcast=False)
            await update_node_status(session, p.id, "review_fe", "completed", broadcast=False)
            await update_node_status(session, p.id, "review_design", "completed", broadcast=False)

        with patch("app.services.planning_service.asyncio.create_task"):
            await client.post(
                f"/api/projects/{project_id}/feedback",
                json={"feedback": "Changes needed"},
            )

        # Check review nodes are reset
        flow_resp = await client.get(f"/api/projects/{project_id}/flow")
        nodes = {n["node_type"]: n for n in flow_resp.json()["nodes"]}
        assert nodes["review_be"]["status"] == "pending"
        assert nodes["review_fe"]["status"] == "pending"
        assert nodes["review_design"]["status"] == "pending"
        assert nodes["approval"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_feedback_empty_content(self, client, db_engine):
        """Empty feedback should return 422."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(
                name="Empty FB",
                idea_text="Test",
                status="reviewing",
                project_path="/tmp/empty_fb",
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(
            f"/api/projects/{project_id}/feedback",
            json={"feedback": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_feedback_missing_content(self, client, db_engine):
        """Missing feedback field should return 422."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(
                name="Missing FB",
                idea_text="Test",
                status="reviewing",
                project_path="/tmp/missing_fb",
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(f"/api/projects/{project_id}/feedback", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_feedback_wrong_status(self, client, db_engine):
        """Feedback from wrong status should return 400."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(
                name="Wrong FB",
                idea_text="Test",
                status="created",
                project_path="/tmp/wrong_fb",
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        response = await client.post(
            f"/api/projects/{project_id}/feedback",
            json={"feedback": "Some feedback"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_feedback_not_found(self, client):
        """Feedback for non-existent project should return 404."""
        response = await client.post(
            "/api/projects/999/feedback",
            json={"feedback": "Some feedback"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_feedback_saves_chat_message(self, client, db_engine, temp_project_dir):
        """Feedback should save user message to chat history."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "chat_fb"
            project_path.mkdir(parents=True)
            p = Project(
                name="Chat FB",
                idea_text="Test",
                status="reviewing",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        with patch("app.services.planning_service.asyncio.create_task"):
            await client.post(
                f"/api/projects/{project_id}/feedback",
                json={"feedback": "검색 기능 추가해주세요"},
            )

        # Check chat messages
        resp = await client.get(f"/api/projects/{project_id}/messages", params={"agent": "pm"})
        messages = resp.json()["messages"]
        assert any("검색 기능 추가해주세요" in m["content"] for m in messages)


class TestPlanningFlowIntegration:
    """Integration tests for the full planning flow."""

    @pytest.mark.asyncio
    async def test_full_plan_approve_flow(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Test the full flow: create → plan → approve."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "full_flow"
            project_path.mkdir(parents=True)
            p = Project(
                name="Full Flow",
                idea_text="Build a todo app",
                status="created",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        # Step 1: Start planning
        with patch("app.services.planning_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.planning_service.asyncio.create_task"):
                plan_resp = await client.post(f"/api/projects/{project_id}/plan")
        assert plan_resp.status_code == 202

        # Step 2: Check flow nodes exist
        flow_resp = await client.get(f"/api/projects/{project_id}/flow")
        assert flow_resp.json()["total"] == 6

        # Step 3: Approve
        approve_resp = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# Todo App PRD\n\n## Features\n- CRUD todos"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # Step 4: Verify final state
        proj_resp = await client.get(f"/api/projects/{project_id}")
        assert proj_resp.json()["status"] == "sprint_planning"

        # Verify PRD file
        prd_path = Path(temp_project_dir) / "full_flow" / "PRD.md"
        assert prd_path.exists()

    @pytest.mark.asyncio
    async def test_plan_feedback_replan_approve_flow(self, client, db_engine, temp_project_dir, temp_common_dir):
        """Test the feedback loop: plan → review → feedback → re-plan → approve."""
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            project_path = Path(temp_project_dir) / "feedback_flow"
            project_path.mkdir(parents=True)
            p = Project(
                name="Feedback Flow",
                idea_text="Build a chat app",
                status="created",
                project_path=str(project_path),
            )
            session.add(p)
            await session.commit()
            await session.refresh(p)
            project_id = p.id

        # Step 1: Start planning
        with patch("app.services.planning_service._get_common_dir", return_value=Path(temp_common_dir)):
            with patch("app.services.planning_service.asyncio.create_task"):
                await client.post(f"/api/projects/{project_id}/plan")

        # Step 2: Start review (status should be planning)
        with patch("app.services.planning_service.asyncio.create_task"):
            review_resp = await client.post(f"/api/projects/{project_id}/review")
        assert review_resp.status_code == 202

        # Step 3: Send feedback
        with patch("app.services.planning_service.asyncio.create_task"):
            fb_resp = await client.post(
                f"/api/projects/{project_id}/feedback",
                json={"feedback": "Add voice messages support"},
            )
        assert fb_resp.status_code == 200

        # Step 4: Project should be back to planning
        proj_resp = await client.get(f"/api/projects/{project_id}")
        assert proj_resp.json()["status"] == "planning"

        # Step 5: Approve
        approve_resp = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# Chat App PRD v2\n\n## With voice messages"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"
