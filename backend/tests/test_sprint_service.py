"""Tests for sprint service internal functions.

Tests Phase.md parsing, prompt builders, and error detection.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project
from app.services.sprint_service import (
    _build_implement_prompt,
    _build_sprint_prompt,
    _detect_error_in_output,
    parse_phase_md,
)


class TestBuildSprintPrompt:
    """Tests for _build_sprint_prompt."""

    def test_basic_prompt(self):
        """Sprint prompt should include PRD and template."""
        prompt = _build_sprint_prompt("# My PRD\nFeatures...", "## 스프린트 폼")
        assert "My PRD" in prompt
        assert "스프린트 폼" in prompt
        assert "PM" in prompt

    def test_with_additional_instructions(self):
        """Sprint prompt should include additional instructions when provided."""
        prompt = _build_sprint_prompt("PRD", "template", additional="Focus on backend first")
        assert "Focus on backend first" in prompt
        assert "추가 지시사항" in prompt

    def test_without_additional_instructions(self):
        """Sprint prompt without additional should not include extra section."""
        prompt = _build_sprint_prompt("PRD", "template")
        assert "추가 지시사항" not in prompt

    def test_includes_rules(self):
        """Sprint prompt should include standard rules."""
        prompt = _build_sprint_prompt("PRD", "template")
        assert "FastAPI" in prompt
        assert "S1, S2, S3" in prompt
        assert "Phase.md" in prompt


class TestBuildImplementPrompt:
    """Tests for _build_implement_prompt."""

    def test_backend_prompt(self):
        """Backend implement prompt should include role description."""
        prompt = _build_implement_prompt(
            "backend", "Implement CRUD API", "PRD content", "Phase content"
        )
        assert "백엔드 개발자" in prompt
        assert "FastAPI" in prompt
        assert "Implement CRUD API" in prompt
        assert "PRD content" in prompt

    def test_frontend_prompt(self):
        """Frontend implement prompt should include role description."""
        prompt = _build_implement_prompt(
            "frontend", "Build UI", "PRD content", "Phase content"
        )
        assert "프론트엔드 개발자" in prompt
        assert "Next.js" in prompt

    def test_prompt_with_error_retry(self):
        """Retry prompt should include error log and retry count."""
        prompt = _build_implement_prompt(
            "backend", "Fix API", "PRD", "Phase",
            error_log="ImportError: No module named 'xyz'",
            retry_count=2,
        )
        assert "에러 발생" in prompt
        assert "재시도 2회차" in prompt
        assert "ImportError" in prompt

    def test_prompt_without_error(self):
        """First attempt prompt should not have error section."""
        prompt = _build_implement_prompt(
            "backend", "Implement API", "PRD", "Phase"
        )
        assert "에러 발생" not in prompt
        assert "재시도" not in prompt


class TestParsePhasemd:
    """Tests for parse_phase_md."""

    def test_parse_single_sprint(self):
        """Parse a single sprint with BE/FE tasks."""
        content = """# Test App — 스프린트 플랜

## 스프린트 개요
| 스프린트 | 기간 | 목표 |
|---------|------|------|
| S1 | 1주 | 기본 세팅 |

## 스프린트 상세

### S1: 기본 세팅
**백엔드 태스크:**
- [ ] DB 스키마 설계
- [ ] API 엔드포인트 구현

**프론트엔드 태스크:**
- [ ] 레이아웃 구성
- [ ] 컴포넌트 작성

**완료 조건:**
- [ ] 테스트 통과
"""
        nodes = parse_phase_md(content)

        # Should have: 1 sprint + 2 BE + 2 FE + 1 test = 6 nodes
        assert len(nodes) == 6

        # Sprint node
        sprint_nodes = [n for n in nodes if n["node_type"].startswith("sprint_")]
        assert len(sprint_nodes) == 1
        assert sprint_nodes[0]["sprint"] == "S1"
        assert "기본 세팅" in sprint_nodes[0]["label"]

        # Backend tasks
        be_nodes = [n for n in nodes if n["agent"] == "backend"]
        assert len(be_nodes) == 2
        assert any("DB 스키마" in n["label"] for n in be_nodes)
        assert any("API 엔드포인트" in n["label"] for n in be_nodes)

        # Frontend tasks
        fe_nodes = [n for n in nodes if n["agent"] == "frontend"]
        assert len(fe_nodes) == 2

    def test_parse_multiple_sprints(self):
        """Parse multiple sprints."""
        content = """## 스프린트 상세

### S1: 세팅
**백엔드 태스크:**
- [ ] DB 설계

**프론트엔드 태스크:**
- [ ] 레이아웃

### S2: 구현
**백엔드 태스크:**
- [ ] API 구현
- [ ] 테스트

**프론트엔드 태스크:**
- [ ] 화면 구현
"""
        nodes = parse_phase_md(content)

        sprint_nodes = [n for n in nodes if n["node_type"].startswith("sprint_")]
        assert len(sprint_nodes) == 2
        assert sprint_nodes[0]["sprint"] == "S1"
        assert sprint_nodes[1]["sprint"] == "S2"

    def test_parse_empty_content(self):
        """Empty content should return empty list."""
        nodes = parse_phase_md("")
        assert nodes == []

    def test_parse_no_tasks(self):
        """Content with sprint but no tasks should return sprint node only."""
        content = """### S1: 세팅
Some description without tasks.
"""
        nodes = parse_phase_md(content)
        assert len(nodes) == 1
        assert nodes[0]["node_type"] == "sprint_s1"

    def test_parse_parent_relationships(self):
        """Task nodes should reference their sprint as parent."""
        content = """### S1: 세팅
**백엔드 태스크:**
- [ ] DB 설계
"""
        nodes = parse_phase_md(content)
        task_nodes = [n for n in nodes if n["agent"] == "backend"]
        assert len(task_nodes) == 1
        assert task_nodes[0]["parent_node_type"] == "sprint_s1"

    def test_parse_design_tasks(self):
        """Should parse design tasks correctly."""
        content = """### S1: 디자인
**디자인 태스크:**
- [ ] 디자인 시스템 정의
- [ ] 컬러 팔레트
"""
        nodes = parse_phase_md(content)
        design_nodes = [n for n in nodes if n["agent"] == "design"]
        assert len(design_nodes) == 2

    def test_parse_completed_tasks(self):
        """Should handle [x] completed checkboxes."""
        content = """### S1: 세팅
**백엔드 태스크:**
- [x] 완료된 태스크
- [ ] 미완료 태스크
"""
        nodes = parse_phase_md(content)
        task_nodes = [n for n in nodes if n["agent"] == "backend"]
        assert len(task_nodes) == 2

    def test_parse_test_section_uses_pm_agent(self):
        """완료 조건 tasks should use 'pm' as agent."""
        content = """### S1: 세팅
**완료 조건:**
- [ ] 전체 테스트 통과
"""
        nodes = parse_phase_md(content)
        pm_tasks = [n for n in nodes if n["agent"] == "pm" and "sprint_" not in n["node_type"]]
        assert len(pm_tasks) == 1


class TestDetectErrorInOutput:
    """Tests for _detect_error_in_output."""

    def test_detect_failed(self):
        """Should detect FAILED keyword."""
        output = "Running tests...\nFAILED test_api.py::test_create\n1 failed"
        error = _detect_error_in_output(output)
        assert error is not None
        assert "FAILED" in error

    def test_detect_traceback(self):
        """Should detect Python traceback."""
        output = """Traceback (most recent call last):
  File "main.py", line 1, in <module>
    import nonexistent
ModuleNotFoundError: No module named 'nonexistent'"""
        error = _detect_error_in_output(output)
        assert error is not None
        assert "Traceback" in error
        assert "ModuleNotFoundError" in error

    def test_detect_syntax_error(self):
        """Should detect SyntaxError."""
        output = "SyntaxError: invalid syntax at line 42"
        error = _detect_error_in_output(output)
        assert error is not None
        assert "SyntaxError" in error

    def test_detect_build_failed(self):
        """Should detect build failures."""
        output = "Compiling...\nBuild failed with 3 errors"
        error = _detect_error_in_output(output)
        assert error is not None
        assert "Build failed" in error

    def test_no_error_in_clean_output(self):
        """Should return None for clean output."""
        output = "All tests passed!\n5 passed in 2.1s\nBuild successful"
        error = _detect_error_in_output(output)
        assert error is None

    def test_detect_exit_code(self):
        """Should detect non-zero exit codes."""
        output = "Process finished with exit code 1"
        error = _detect_error_in_output(output)
        assert error is not None

    def test_detect_import_error(self):
        """Should detect ImportError."""
        output = "ImportError: cannot import name 'xyz' from 'abc'"
        error = _detect_error_in_output(output)
        assert error is not None

    def test_empty_output(self):
        """Empty output should return None."""
        error = _detect_error_in_output("")
        assert error is None

    def test_caps_error(self):
        """Should detect ERROR in output."""
        output = "2024-01-01 ERROR: Database connection failed"
        error = _detect_error_in_output(output)
        assert error is not None


class TestSprintServiceHelpers:
    """Tests for sprint service helper functions."""

    @pytest.fixture
    async def db(self, db_engine):
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            yield session

    @pytest.fixture
    async def project(self, db):
        p = Project(
            name="Sprint Test",
            idea_text="Build a todo app",
            status="sprint_planning",
            project_path="/tmp/sprint_test",
        )
        db.add(p)
        await db.commit()
        await db.refresh(p)
        return p

    @pytest.mark.asyncio
    async def test_start_sprint_planning_creates_task(self, db, project):
        """start_sprint_planning should create a PM task."""
        tmpdir = tempfile.mkdtemp()
        project.project_path = tmpdir
        await db.commit()

        try:
            from app.services.sprint_service import start_sprint_planning

            with patch("app.services.sprint_service._get_common_dir", return_value=Path(tmpdir)):
                with patch("app.services.sprint_service.asyncio.create_task"):
                    task_id = await start_sprint_planning(db, project)

            assert task_id > 0

            from app.services.agent_task_service import get_task
            task = await get_task(db, task_id)
            assert task is not None
            assert task.agent == "pm"
            assert "스프린트 플랜" in task.command
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_start_sprint_planning_updates_status(self, db, project):
        """start_sprint_planning should update project status."""
        tmpdir = tempfile.mkdtemp()
        project.project_path = tmpdir
        await db.commit()

        try:
            from app.services.sprint_service import start_sprint_planning

            with patch("app.services.sprint_service._get_common_dir", return_value=Path(tmpdir)):
                with patch("app.services.sprint_service.asyncio.create_task"):
                    await start_sprint_planning(db, project)

            assert project.status == "sprint_planning"
            assert project.current_phase == "sprint_planning"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_start_implementation_creates_task(self, db, project):
        """start_implementation should create PM orchestration task."""
        from app.services.sprint_service import start_implementation

        with patch("app.services.sprint_service.asyncio.create_task"):
            task_id = await start_implementation(db, project, max_retries=3)

        assert task_id > 0

        from app.services.agent_task_service import get_task
        task = await get_task(db, task_id)
        assert task is not None
        assert task.agent == "pm"
        assert "오케스트레이션" in task.command

    @pytest.mark.asyncio
    async def test_start_implementation_updates_status(self, db, project):
        """start_implementation should update project status to implementing."""
        from app.services.sprint_service import start_implementation

        with patch("app.services.sprint_service.asyncio.create_task"):
            await start_implementation(db, project, max_retries=3)

        assert project.status == "implementing"
        assert project.current_phase == "implementing"

    @pytest.mark.asyncio
    async def test_create_sprint_flow_nodes(self, db, project):
        """_create_sprint_flow_nodes should create nodes from parsed data."""
        from app.services.sprint_service import _create_sprint_flow_nodes

        parsed = [
            {
                "node_type": "sprint_s1",
                "label": "S1: 세팅",
                "agent": "pm",
                "sprint": "S1",
                "parent_node_type": "sprint_plan",
            },
            {
                "node_type": "impl_s1_backend_1",
                "label": "DB 설계",
                "agent": "backend",
                "sprint": "S1",
                "parent_node_type": "sprint_s1",
            },
        ]

        node_ids = await _create_sprint_flow_nodes(db, project.id, parsed)

        # Should create sprint_plan + sprint_s1 + impl node = 3
        assert len(node_ids) == 3

        from app.services.flow_node_service import get_flow_nodes
        nodes = await get_flow_nodes(db, project.id)
        assert len(nodes) == 3

        # Check sprint_plan node
        plan_node = next(n for n in nodes if n.node_type == "sprint_plan")
        assert plan_node.status == "completed"

        # Check sprint_s1 is pending
        sprint_node = next(n for n in nodes if n.node_type == "sprint_s1")
        assert sprint_node.status == "pending"
        assert sprint_node.parent_node_id == plan_node.id
