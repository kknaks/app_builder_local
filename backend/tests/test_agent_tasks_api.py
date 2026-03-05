"""Tests for agent tasks API endpoints."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_task import AgentTask
from app.models.project import Project


@pytest.fixture
async def project_with_tasks(db_session: AsyncSession):
    """Create a project with some agent tasks."""
    project = Project(
        name="Test Project",
        idea_text="Test idea",
        status="created",
        project_path="/tmp/test_project",
    )
    db_session.add(project)
    await db_session.flush()

    tasks = [
        AgentTask(
            project_id=project.id,
            agent="pm",
            command="Plan the project",
            status="completed",
            started_at=datetime.now(UTC),
        ),
        AgentTask(
            project_id=project.id,
            agent="backend",
            command="Build API",
            status="running",
            started_at=datetime.now(UTC),
        ),
        AgentTask(
            project_id=project.id,
            agent="frontend",
            command="Build UI",
            status="pending",
        ),
    ]
    db_session.add_all(tasks)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_list_tasks(client, db_engine):
    """Test listing tasks for a project."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        task = AgentTask(
            project_id=project.id, agent="pm", command="test cmd", status="pending"
        )
        db.add(task)
        await db.commit()

    response = await client.get(f"/api/projects/{project.id}/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["agent"] == "pm"
    assert data["tasks"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_tasks_filter_status(client, db_engine):
    """Test listing tasks with status filter."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        db.add_all([
            AgentTask(project_id=project.id, agent="pm", command="cmd1", status="running"),
            AgentTask(project_id=project.id, agent="backend", command="cmd2", status="pending"),
        ])
        await db.commit()

    response = await client.get(f"/api/projects/{project.id}/tasks?status=running")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_list_tasks_project_not_found(client):
    """Test listing tasks for non-existent project."""
    response = await client.get("/api/projects/99999/tasks")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_project_tasks(client, db_engine):
    """Test cancelling all project tasks."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        db.add_all([
            AgentTask(project_id=project.id, agent="pm", command="cmd1", status="running"),
            AgentTask(project_id=project.id, agent="backend", command="cmd2", status="pending"),
            AgentTask(project_id=project.id, agent="frontend", command="cmd3", status="completed"),
        ])
        await db.commit()

    response = await client.post(f"/api/projects/{project.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_count"] == 2  # running + pending

    # Verify tasks are now cancelled
    response = await client.get(f"/api/projects/{project.id}/tasks")
    data = response.json()
    statuses = {t["agent"]: t["status"] for t in data["tasks"]}
    assert statuses["pm"] == "cancelled"
    assert statuses["backend"] == "cancelled"
    assert statuses["frontend"] == "completed"  # should remain unchanged


@pytest.mark.asyncio
async def test_cancel_single_task(client, db_engine):
    """Test cancelling a single task."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        task = AgentTask(
            project_id=project.id, agent="pm", command="cmd", status="pending"
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.post(f"/api/projects/{project.id}/tasks/{task.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_count"] == 1


@pytest.mark.asyncio
async def test_cancel_completed_task_fails(client, db_engine):
    """Test that cancelling a completed task returns error."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        task = AgentTask(
            project_id=project.id, agent="pm", command="cmd", status="completed"
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.post(f"/api/projects/{project.id}/tasks/{task.id}/cancel")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_nonexistent_task(client, db_engine):
    """Test cancelling a non-existent task."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

    response = await client.post(f"/api/projects/{project.id}/tasks/99999/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_project_not_found(client):
    """Test cancelling tasks for non-existent project."""
    response = await client.post("/api/projects/99999/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agents_status(client, db_engine):
    """Test getting agent statuses for a project."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Test", idea_text="idea", status="created", project_path="/tmp/test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # Add some tasks for different agents
        db.add_all([
            AgentTask(project_id=project.id, agent="pm", command="cmd", status="completed"),
            AgentTask(project_id=project.id, agent="backend", command="cmd", status="failed"),
        ])
        await db.commit()

    response = await client.get(f"/api/projects/{project.id}/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project.id
    assert len(data["agents"]) == 5  # pm, planner, backend, frontend, design

    agents = {a["agent"]: a for a in data["agents"]}
    assert agents["pm"]["last_task_status"] == "completed"
    assert agents["backend"]["last_task_status"] == "failed"
    assert agents["planner"]["status"] == "idle"
    assert agents["planner"]["last_task_status"] is None


@pytest.mark.asyncio
async def test_get_agents_status_project_not_found(client):
    """Test getting agent statuses for non-existent project."""
    response = await client.get("/api/projects/99999/agents")
    assert response.status_code == 404
