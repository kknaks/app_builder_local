"""Tests for service layer functions."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project
from app.services.agent_task_service import (
    cancel_task,
    cleanup_stale_tasks,
    create_task,
    get_agent_statuses,
    get_task,
    get_tasks_for_project,
    update_task_status,
)
from app.services.chat_service import get_message_count, get_messages, save_message
from app.services.cost_service import get_project_cost, record_token_usage


@pytest.fixture
async def db(db_engine):
    """Get a fresh DB session for service tests."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def project(db):
    """Create a test project."""
    p = Project(name="Svc Test", idea_text="test", status="created", project_path="/tmp/svc")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


class TestAgentTaskService:
    """Tests for agent_task_service functions."""

    @pytest.mark.asyncio
    async def test_create_task(self, db, project):
        task = await create_task(db, project.id, "pm", "Plan it")
        assert task.id is not None
        assert task.status == "pending"
        assert task.agent == "pm"
        assert task.command == "Plan it"

    @pytest.mark.asyncio
    async def test_update_task_to_running(self, db, project):
        task = await create_task(db, project.id, "backend", "Build API")
        updated = await update_task_status(db, task.id, "running")
        assert updated is not None
        assert updated.status == "running"
        assert updated.started_at is not None

    @pytest.mark.asyncio
    async def test_update_task_to_completed(self, db, project):
        task = await create_task(db, project.id, "backend", "Build API")
        await update_task_status(db, task.id, "running")
        updated = await update_task_status(db, task.id, "completed", result="Done!")
        assert updated.status == "completed"
        assert updated.result == "Done!"

    @pytest.mark.asyncio
    async def test_update_task_to_failed(self, db, project):
        task = await create_task(db, project.id, "frontend", "Build UI")
        await update_task_status(db, task.id, "running")
        updated = await update_task_status(db, task.id, "failed", error="Build error")
        assert updated.status == "failed"
        assert updated.error == "Build error"

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, db):
        result = await update_task_status(db, 99999, "running")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_task(self, db, project):
        task = await create_task(db, project.id, "pm", "cmd")
        found = await get_task(db, task.id)
        assert found is not None
        assert found.id == task.id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, db):
        found = await get_task(db, 99999)
        assert found is None

    @pytest.mark.asyncio
    async def test_get_tasks_for_project(self, db, project):
        await create_task(db, project.id, "pm", "cmd1")
        await create_task(db, project.id, "backend", "cmd2")

        tasks = await get_tasks_for_project(db, project.id)
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_get_tasks_filter_status(self, db, project):
        t1 = await create_task(db, project.id, "pm", "cmd1")
        await create_task(db, project.id, "backend", "cmd2")
        await update_task_status(db, t1.id, "running")

        running = await get_tasks_for_project(db, project.id, status="running")
        assert len(running) == 1
        assert running[0].id == t1.id

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, db, project):
        task = await create_task(db, project.id, "pm", "cmd")
        result = await cancel_task(db, task.id)
        assert result is True

        found = await get_task(db, task.id)
        assert found.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_task_fails(self, db, project):
        task = await create_task(db, project.id, "pm", "cmd")
        await update_task_status(db, task.id, "completed")

        result = await cancel_task(db, task.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_stale_tasks(self, db, project):
        t1 = await create_task(db, project.id, "pm", "cmd1")
        t2 = await create_task(db, project.id, "backend", "cmd2")
        await update_task_status(db, t1.id, "running")
        await update_task_status(db, t2.id, "running")

        count = await cleanup_stale_tasks(db)
        assert count == 2

        found1 = await get_task(db, t1.id)
        found2 = await get_task(db, t2.id)
        assert found1.status == "failed"
        assert found2.status == "failed"
        assert "Server restarted" in found1.error

    @pytest.mark.asyncio
    async def test_get_agent_statuses(self, db, project):
        await create_task(db, project.id, "pm", "cmd")
        await create_task(db, project.id, "backend", "cmd")

        statuses = await get_agent_statuses(db, project.id)
        assert len(statuses) == 5
        agents = {s["agent"]: s for s in statuses}
        assert agents["planner"]["status"] == "idle"


class TestChatService:
    """Tests for chat_service functions."""

    @pytest.mark.asyncio
    async def test_save_and_get_message(self, db, project):
        msg = await save_message(db, project.id, "pm", "user", "Hello!")
        assert msg.id is not None
        assert msg.content == "Hello!"

        messages = await get_messages(db, project.id)
        assert len(messages) == 1
        assert messages[0].content == "Hello!"

    @pytest.mark.asyncio
    async def test_get_messages_filter_agent(self, db, project):
        await save_message(db, project.id, "pm", "user", "msg1")
        await save_message(db, project.id, "backend", "user", "msg2")

        pm_msgs = await get_messages(db, project.id, agent="pm")
        assert len(pm_msgs) == 1
        assert pm_msgs[0].agent == "pm"

    @pytest.mark.asyncio
    async def test_get_message_count(self, db, project):
        await save_message(db, project.id, "pm", "user", "msg1")
        await save_message(db, project.id, "pm", "assistant", "msg2")
        await save_message(db, project.id, "backend", "user", "msg3")

        total = await get_message_count(db, project.id)
        assert total == 3

        pm_count = await get_message_count(db, project.id, agent="pm")
        assert pm_count == 2


class TestCostService:
    """Tests for cost_service functions."""

    @pytest.mark.asyncio
    async def test_record_token_usage(self, db, project):
        usage = await record_token_usage(
            db, project.id, "pm", 1000, 500, cost_usd=0.015
        )
        assert usage.id is not None
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cost_usd == Decimal("0.015")

    @pytest.mark.asyncio
    async def test_get_project_cost(self, db, project):
        await record_token_usage(db, project.id, "pm", 1000, 500, cost_usd=0.015)
        await record_token_usage(db, project.id, "backend", 2000, 1000, cost_usd=0.030)

        cost = await get_project_cost(db, project.id)
        assert cost["total_input_tokens"] == 3000
        assert cost["total_output_tokens"] == 1500
        assert cost["total_tokens"] == 4500
        assert len(cost["agent_breakdown"]) == 2

    @pytest.mark.asyncio
    async def test_get_project_cost_empty(self, db, project):
        cost = await get_project_cost(db, project.id)
        assert cost["total_input_tokens"] == 0
        assert cost["total_output_tokens"] == 0
        assert cost["total_tokens"] == 0
        assert len(cost["agent_breakdown"]) == 0

    @pytest.mark.asyncio
    async def test_record_usage_without_cost(self, db, project):
        usage = await record_token_usage(db, project.id, "pm", 500, 200)
        assert usage.cost_usd is None
