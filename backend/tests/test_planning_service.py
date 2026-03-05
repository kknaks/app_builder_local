"""Tests for planning service internal functions."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project
from app.services.planning_service import (
    _build_feedback_prompt,
    _build_planner_prompt,
    _build_review_prompt,
)


class TestPromptBuilders:
    """Tests for prompt building functions."""

    def test_build_planner_prompt_basic(self):
        """Planner prompt should include idea and plan form."""
        prompt = _build_planner_prompt("Build a todo app", "## 1. 개요\n## 2. 기능\n")
        assert "Build a todo app" in prompt
        assert "## 1. 개요" in prompt
        assert "기획 전문가" in prompt

    def test_build_planner_prompt_with_context(self):
        """Planner prompt should include additional context when provided."""
        prompt = _build_planner_prompt(
            "Build a todo app",
            "## 1. 개요\n",
            additional_context="Focus on mobile-first",
        )
        assert "Focus on mobile-first" in prompt
        assert "추가 컨텍스트" in prompt

    def test_build_planner_prompt_without_context(self):
        """Planner prompt without context should not have context section."""
        prompt = _build_planner_prompt("Build a todo app", "## 1. 개요\n")
        assert "추가 컨텍스트" not in prompt

    def test_build_planner_prompt_includes_rules(self):
        """Planner prompt should include standard rules."""
        prompt = _build_planner_prompt("test", "form")
        assert "MVP" in prompt
        assert "FastAPI" in prompt
        assert "plan_form.md" in prompt

    def test_build_review_prompt_backend(self):
        """Backend review prompt should focus on API/DB/security."""
        prompt = _build_review_prompt("backend", "Build a todo app")
        assert "백엔드 개발자" in prompt
        assert "API" in prompt
        assert "Build a todo app" in prompt

    def test_build_review_prompt_frontend(self):
        """Frontend review prompt should focus on UI/UX."""
        prompt = _build_review_prompt("frontend", "Build a todo app")
        assert "프론트엔드 개발자" in prompt
        assert "UI/UX" in prompt

    def test_build_review_prompt_design(self):
        """Design review prompt should focus on design aspects."""
        prompt = _build_review_prompt("design", "Build a todo app")
        assert "디자이너" in prompt
        assert "사용성" in prompt

    def test_build_review_prompt_structure(self):
        """All review prompts should include standard review sections."""
        for agent in ["backend", "frontend", "design"]:
            prompt = _build_review_prompt(agent, "test idea")
            assert "장점" in prompt
            assert "개선 필요" in prompt
            assert "리스크" in prompt
            assert "제안" in prompt

    def test_build_feedback_prompt(self):
        """Feedback prompt should include feedback and idea."""
        prompt = _build_feedback_prompt("결제 기능 추가", "Build a shop app")
        assert "결제 기능 추가" in prompt
        assert "Build a shop app" in prompt
        assert "피드백" in prompt

    def test_build_feedback_prompt_rules(self):
        """Feedback prompt should include modification rules."""
        prompt = _build_feedback_prompt("changes", "idea")
        assert "구조를 유지" in prompt
        assert "MVP" in prompt


class TestPlanningServiceHelpers:
    """Tests for planning service helper functions."""

    @pytest.fixture
    async def db(self, db_engine):
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            yield session

    @pytest.fixture
    async def project(self, db):
        p = Project(name="Helper Test", idea_text="test", status="created", project_path="/tmp/helper")
        db.add(p)
        await db.commit()
        await db.refresh(p)
        return p

    @pytest.mark.asyncio
    async def test_approve_plan_creates_prd_file(self, db, project):
        """approve_plan should create PRD.md in project directory."""
        tmpdir = tempfile.mkdtemp()
        project.project_path = tmpdir
        await db.commit()

        try:
            from app.services.planning_service import approve_plan

            prd_path = await approve_plan(db, project, "# Test PRD\n\nContent here.")
            assert Path(prd_path).exists()
            assert Path(prd_path).read_text() == "# Test PRD\n\nContent here."
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_approve_plan_updates_status(self, db, project):
        """approve_plan should change project status to sprint_planning."""
        tmpdir = tempfile.mkdtemp()
        project.project_path = tmpdir
        project.status = "reviewing"
        await db.commit()

        try:
            from app.services.planning_service import approve_plan

            await approve_plan(db, project, "# PRD\n")
            assert project.status == "sprint_planning"
            assert project.current_phase == "sprint_planning"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_send_feedback_creates_task(self, db, project):
        """send_feedback should create a new planner task."""
        project.status = "reviewing"
        await db.commit()

        from app.services.planning_service import send_feedback

        with patch("app.services.planning_service.asyncio.create_task"):
            task_id = await send_feedback(db, project, "Add search feature")

        assert task_id > 0

        # Verify task was created
        from app.services.agent_task_service import get_task

        task = await get_task(db, task_id)
        assert task is not None
        assert task.agent == "planner"

    @pytest.mark.asyncio
    async def test_send_feedback_saves_user_message(self, db, project):
        """send_feedback should save feedback as user chat message."""
        project.status = "reviewing"
        await db.commit()

        from app.services.planning_service import send_feedback

        with patch("app.services.planning_service.asyncio.create_task"):
            await send_feedback(db, project, "Add auth")

        from app.services.chat_service import get_messages

        messages = await get_messages(db, project.id, agent="pm")
        assert any("Add auth" in m.content for m in messages)

    @pytest.mark.asyncio
    async def test_send_feedback_resets_status(self, db, project):
        """send_feedback should reset project status to planning."""
        project.status = "reviewing"
        await db.commit()

        from app.services.planning_service import send_feedback

        with patch("app.services.planning_service.asyncio.create_task"):
            await send_feedback(db, project, "Changes needed")

        assert project.status == "planning"
        assert project.current_phase == "planning"

    @pytest.mark.asyncio
    async def test_start_planning_creates_flow_nodes(self, db, project):
        """start_planning should initialize flow nodes."""
        tmpdir = tempfile.mkdtemp()
        project.project_path = tmpdir
        await db.commit()

        try:
            from app.services.planning_service import start_planning

            with patch("app.services.planning_service._get_common_dir", return_value=Path(tmpdir)):
                with patch("app.services.planning_service.asyncio.create_task"):
                    task_id = await start_planning(db, project)

            assert task_id > 0

            from app.services.flow_node_service import get_flow_nodes

            nodes = await get_flow_nodes(db, project.id)
            assert len(nodes) == 6
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_start_planning_updates_status(self, db, project):
        """start_planning should update project status to planning."""
        tmpdir = tempfile.mkdtemp()
        project.project_path = tmpdir
        await db.commit()

        try:
            from app.services.planning_service import start_planning

            with patch("app.services.planning_service._get_common_dir", return_value=Path(tmpdir)):
                with patch("app.services.planning_service.asyncio.create_task"):
                    await start_planning(db, project)

            assert project.status == "planning"
            assert project.current_phase == "planning"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_start_review_creates_tasks(self, db, project):
        """start_review should create 3 review tasks."""
        project.status = "planning"
        await db.commit()

        from app.services.planning_service import start_review

        with patch("app.services.planning_service.asyncio.create_task"):
            task_ids = await start_review(db, project)

        assert len(task_ids) == 3

        from app.services.agent_task_service import get_task

        agents = set()
        for tid in task_ids:
            task = await get_task(db, tid)
            assert task is not None
            agents.add(task.agent)
        assert agents == {"backend", "frontend", "design"}

    @pytest.mark.asyncio
    async def test_start_review_updates_status(self, db, project):
        """start_review should update project status to reviewing."""
        project.status = "planning"
        await db.commit()

        from app.services.planning_service import start_review

        with patch("app.services.planning_service.asyncio.create_task"):
            await start_review(db, project)

        assert project.status == "reviewing"
        assert project.current_phase == "reviewing"
