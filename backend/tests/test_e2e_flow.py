"""E2E integration tests — full project flow.

Tests the complete lifecycle:
  프로젝트 생성 → 기획 시작 → 검토 → 승인 → 스프린트 플랜 → 구현 → Docker 실행
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def temp_dirs():
    """Create temporary project and common directories."""
    project_dir = tempfile.mkdtemp(prefix="test_e2e_proj_")
    common_dir = tempfile.mkdtemp(prefix="test_e2e_common_")

    # Create plan_form.md and plan_phase.md in common
    Path(common_dir).joinpath("plan_form.md").write_text("# Plan Form\n## 기획 폼\n")
    Path(common_dir).joinpath("plan_phase.md").write_text("# Phase Plan\n## 스프린트 폼\n")

    yield {"project": Path(project_dir), "common": Path(common_dir)}

    shutil.rmtree(project_dir, ignore_errors=True)
    shutil.rmtree(common_dir, ignore_errors=True)


def _patch_project_dirs(temp_dirs):
    """Context manager helper for patching project/common dirs."""
    return (
        patch("app.services.project_service._get_projects_base_dir", return_value=temp_dirs["project"]),
        patch("app.services.project_service._get_common_dir", return_value=temp_dirs["common"]),
    )


class TestFullProjectLifecycle:
    """Complete project lifecycle E2E test."""

    @pytest.mark.asyncio
    async def test_create_project(self, client, temp_dirs):
        """Step 1: Create a new project."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            response = await client.post(
                "/api/projects",
                json={
                    "name": "Todo App",
                    "idea_text": "간단한 할일 관리 앱. 할일 추가/완료/삭제 기능.",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "created"
        assert data["name"] == "Todo App"
        return data

    @pytest.mark.asyncio
    async def test_full_flow_create_to_plan(self, client, temp_dirs):
        """Step 1-2: Create project → Start planning."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={
                    "name": "Todo App",
                    "idea_text": "할일 관리 앱",
                },
            )
        project_id = create_resp.json()["id"]

        # Start planning
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            response = await client.post(f"/api/projects/{project_id}/plan")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "planning_started"
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_full_flow_plan_to_review(self, client, temp_dirs, db_session):
        """Step 2-3: Plan → Review (BE/FE/Design 검토)."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Todo App", "idea_text": "할일 관리 앱"},
            )
        project_id = create_resp.json()["id"]

        # Move to planning status
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        # Start review
        with patch("app.services.planning_service._review_worker", new_callable=AsyncMock):
            response = await client.post(f"/api/projects/{project_id}/review")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "review_started"
        assert "task_ids" in data

    @pytest.mark.asyncio
    async def test_full_flow_review_to_approve(self, client, temp_dirs):
        """Step 3-4: Review → Approve (PRD.md 확정)."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Todo App", "idea_text": "할일 관리 앱"},
            )
        project_id = create_resp.json()["id"]
        project_path = create_resp.json()["project_path"]

        # Move to planning status
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        # Approve with PRD content
        prd_content = "# Todo App PRD\n\n## 기능\n- 할일 추가\n- 할일 완료\n- 할일 삭제\n"
        response = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": prd_content},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert "prd_path" in data

        # PRD.md should exist
        prd_path = Path(project_path) / "PRD.md"
        assert prd_path.exists()

    @pytest.mark.asyncio
    async def test_full_flow_approve_to_sprint(self, client, temp_dirs):
        """Step 4-5: Approve → Sprint planning."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Todo App", "idea_text": "할일 관리 앱"},
            )
        project_id = create_resp.json()["id"]

        # Move through planning → approve
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# PRD\n"},
        )

        # Start sprint planning
        with patch("app.services.sprint_service._sprint_planning_worker", new_callable=AsyncMock):
            response = await client.post(f"/api/projects/{project_id}/sprint")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "sprint_planning_started"

    @pytest.mark.asyncio
    async def test_full_flow_sprint_to_implement(self, client, temp_dirs):
        """Step 5-6: Sprint plan → Implementation."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Todo App", "idea_text": "할일 관리 앱"},
            )
        project_id = create_resp.json()["id"]

        # Move through planning → approve → sprint
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# PRD\n"},
        )

        with patch("app.services.sprint_service._sprint_planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/sprint")

        # Start implementation
        with patch("app.services.sprint_service._implementation_orchestrator", new_callable=AsyncMock):
            response = await client.post(f"/api/projects/{project_id}/implement")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "implementation_started"

    @pytest.mark.asyncio
    async def test_full_flow_implement_to_docker_run(self, client, temp_dirs):
        """Step 6-7: Implementation → Docker run."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Todo App", "idea_text": "할일 관리 앱"},
            )
        project_id = create_resp.json()["id"]
        project_path = create_resp.json()["project_path"]

        # Create backend/frontend dirs in project
        (Path(project_path) / "backend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "backend" / "pyproject.toml").write_text("[project]\n")
        (Path(project_path) / "frontend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "frontend" / "package.json").write_text("{}\n")

        # Mock Docker operations
        mock_up = AsyncMock(return_value={
            "status": "running",
            "output": "Started",
            "containers": [
                {
                    "name": "appbuilder_todo_app_backend",
                    "service": "backend",
                    "state": "running",
                    "status": "Up 5 seconds",
                    "ports": "0.0.0.0:31000->8000/tcp",
                },
                {
                    "name": "appbuilder_todo_app_frontend",
                    "service": "frontend",
                    "state": "running",
                    "status": "Up 3 seconds",
                    "ports": "0.0.0.0:31001->3000/tcp",
                },
            ],
            "urls": {
                "backend": "http://localhost:31000",
                "frontend": "http://localhost:31001",
            },
        })

        with patch("app.routers.docker.docker_compose_up", mock_up):
            response = await client.post(
                f"/api/projects/{project_id}/run",
                json={"backend_port": 31000, "frontend_port": 31001, "db_port": 31002},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "backend" in data["urls"]
        assert "frontend" in data["urls"]
        assert len(data["containers"]) == 2


class TestFeedbackLoop:
    """Test the feedback loop: user rejects plan → re-plan → re-review → approve."""

    @pytest.mark.asyncio
    async def test_feedback_loop(self, client, temp_dirs):
        """User sends feedback → Planner modifies → Re-review → Approve."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Feedback App", "idea_text": "피드백 테스트 앱"},
            )
        project_id = create_resp.json()["id"]

        # Start planning
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        # Send feedback (user rejects) — uses _planning_worker internally
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            feedback_resp = await client.post(
                f"/api/projects/{project_id}/feedback",
                json={"feedback": "결제 기능도 추가해주세요"},
            )

        assert feedback_resp.status_code == 200
        assert feedback_resp.json()["status"] == "feedback_sent"

        # Approve after revision
        approve_resp = await client.post(
            f"/api/projects/{project_id}/approve",
            json={"prd_content": "# Revised PRD\n"},
        )

        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"


class TestProjectManagement:
    """Test project listing, details, and deletion across lifecycle."""

    @pytest.mark.asyncio
    async def test_project_list_shows_status(self, client, temp_dirs):
        """Project list should reflect current status."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            await client.post(
                "/api/projects",
                json={"name": "App One", "idea_text": "First app"},
            )
            create_resp = await client.post(
                "/api/projects",
                json={"name": "App Two", "idea_text": "Second app"},
            )

        # Start planning for second project
        project_id = create_resp.json()["id"]
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        # List should show both projects
        list_resp = await client.get("/api/projects")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 2

        # Find the planning project
        statuses = {p["name"]: p["status"] for p in data["projects"]}
        assert statuses["App One"] == "created"
        assert statuses["App Two"] == "planning"

    @pytest.mark.asyncio
    async def test_delete_project_during_lifecycle(self, client, temp_dirs):
        """Should be able to delete a project at any stage."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Delete Me", "idea_text": "To be deleted"},
            )
        project_id = create_resp.json()["id"]

        # Start planning
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        # Delete during planning
        delete_resp = await client.delete(f"/api/projects/{project_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "deleted"

        # Verify gone
        get_resp = await client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_project_detail_shows_path_and_phase(self, client, temp_dirs):
        """Project detail should include project_path and current_phase."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Detail App", "idea_text": "Detail test"},
            )
        project_id = create_resp.json()["id"]

        detail_resp = await client.get(f"/api/projects/{project_id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert "project_path" in data
        assert data["current_phase"] is None  # Not started yet


class TestFlowNodes:
    """Test flow node creation and updates during lifecycle."""

    @pytest.mark.asyncio
    async def test_flow_nodes_created_on_plan(self, client, temp_dirs):
        """Planning should create initial flow nodes."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Flow App", "idea_text": "Flow node test"},
            )
        project_id = create_resp.json()["id"]

        # Start planning — this creates flow nodes
        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")

        # Check flow nodes
        flow_resp = await client.get(f"/api/projects/{project_id}/flow")
        assert flow_resp.status_code == 200
        data = flow_resp.json()
        assert len(data["nodes"]) > 0

        # Should have idea, planning, review, approval nodes
        node_types = {n["node_type"] for n in data["nodes"]}
        assert "idea" in node_types
        assert "planning" in node_types

    @pytest.mark.asyncio
    async def test_flow_nodes_idempotent(self, client, temp_dirs):
        """Calling plan twice should not duplicate flow nodes."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Idempotent App", "idea_text": "Test"},
            )
        project_id = create_resp.json()["id"]

        with patch("app.services.planning_service._planning_worker", new_callable=AsyncMock):
            await client.post(f"/api/projects/{project_id}/plan")
            # Call plan again (project is already in planning status)
            await client.post(f"/api/projects/{project_id}/plan")

        flow_resp = await client.get(f"/api/projects/{project_id}/flow")
        data = flow_resp.json()
        # Should not have duplicate nodes
        node_types = [n["node_type"] for n in data["nodes"]]
        assert node_types.count("idea") == 1


class TestCostTracking:
    """Test cost API during lifecycle."""

    @pytest.mark.asyncio
    async def test_cost_initially_zero(self, client, temp_dirs):
        """New project should have zero cost."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Cost App", "idea_text": "Cost test"},
            )
        project_id = create_resp.json()["id"]

        cost_resp = await client.get(f"/api/projects/{project_id}/cost")
        assert cost_resp.status_code == 200
        data = cost_resp.json()
        assert data["total_input_tokens"] == 0
        assert data["total_output_tokens"] == 0


class TestDockerLifecycleE2E:
    """Test Docker run → status → stop → re-run lifecycle."""

    @pytest.mark.asyncio
    async def test_docker_lifecycle(self, client, temp_dirs):
        """Full Docker lifecycle: run → check status → stop → re-run."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Docker App", "idea_text": "Docker lifecycle test"},
            )
        project_id = create_resp.json()["id"]
        project_path = create_resp.json()["project_path"]

        # Setup project structure
        (Path(project_path) / "backend").mkdir(parents=True, exist_ok=True)
        (Path(project_path) / "backend" / "pyproject.toml").write_text("[project]\n")

        # Run
        with patch(
            "app.routers.docker.docker_compose_up",
            new_callable=AsyncMock,
            return_value={
                "status": "running",
                "output": "Started",
                "containers": [
                    {"name": "test_be", "service": "backend", "state": "running", "status": "Up", "ports": ""},
                ],
                "urls": {"backend": "http://localhost:31000"},
            },
        ):
            run_resp = await client.post(f"/api/projects/{project_id}/run")
        assert run_resp.json()["status"] == "running"

        # Check status
        with patch(
            "app.routers.docker.get_container_status",
            new_callable=AsyncMock,
            return_value={
                "status": "running",
                "containers": [
                    {"name": "test_be", "service": "backend", "state": "running", "status": "Up", "ports": ""},
                ],
                "urls": {"backend": "http://localhost:31000"},
            },
        ):
            status_resp = await client.get(f"/api/projects/{project_id}/run/status")
        assert status_resp.json()["status"] == "running"

        # Stop
        with patch(
            "app.routers.docker.docker_compose_down",
            new_callable=AsyncMock,
            return_value={"status": "stopped", "output": "Stopped"},
        ):
            stop_resp = await client.post(f"/api/projects/{project_id}/stop")
        assert stop_resp.json()["status"] == "stopped"

        # Re-run
        with patch(
            "app.routers.docker.docker_compose_up",
            new_callable=AsyncMock,
            return_value={
                "status": "running",
                "output": "Started again",
                "containers": [],
                "urls": {"backend": "http://localhost:31000"},
            },
        ):
            rerun_resp = await client.post(f"/api/projects/{project_id}/run")
        assert rerun_resp.json()["status"] == "running"


class TestStatusTransitions:
    """Test valid and invalid status transitions."""

    @pytest.mark.asyncio
    async def test_cannot_review_before_plan(self, client, temp_dirs):
        """Should not allow review before planning starts."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Bad Flow", "idea_text": "Invalid transition"},
            )
        project_id = create_resp.json()["id"]

        response = await client.post(f"/api/projects/{project_id}/review")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_implement_before_sprint(self, client, temp_dirs):
        """Should not allow implementation before sprint planning."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Bad Flow", "idea_text": "Invalid transition"},
            )
        project_id = create_resp.json()["id"]

        response = await client.post(f"/api/projects/{project_id}/implement")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_approve_before_plan(self, client, temp_dirs):
        """Should not allow approval before planning."""
        p1, p2 = _patch_project_dirs(temp_dirs)
        with p1, p2:
            create_resp = await client.post(
                "/api/projects",
                json={"name": "Bad Flow", "idea_text": "Invalid transition"},
            )
        project_id = create_resp.json()["id"]

        response = await client.post(f"/api/projects/{project_id}/approve")
        assert response.status_code == 400
