"""Tests for chat API endpoints."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.chat_message import ChatMessage
from app.models.project import Project


@pytest.fixture
async def project_with_messages(db_engine):
    """Create a project with chat messages."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Chat Test", idea_text="test", status="created", project_path="/tmp/chat_test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        messages = [
            ChatMessage(project_id=project.id, agent="pm", role="user", content="Hello PM"),
            ChatMessage(project_id=project.id, agent="pm", role="assistant", content="Hi! I'm the PM agent."),
            ChatMessage(project_id=project.id, agent="backend", role="user", content="Hello Backend"),
            ChatMessage(project_id=project.id, agent="backend", role="assistant", content="Hi! Backend here."),
            ChatMessage(project_id=project.id, agent="pm", role="user", content="Another PM message"),
        ]
        db.add_all(messages)
        await db.commit()

    return project


@pytest.mark.asyncio
async def test_get_messages(client, project_with_messages):
    """Test getting all messages for a project."""
    project = project_with_messages
    response = await client.get(f"/api/projects/{project.id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["messages"]) == 5


@pytest.mark.asyncio
async def test_get_messages_filter_agent(client, project_with_messages):
    """Test filtering messages by agent."""
    project = project_with_messages
    response = await client.get(f"/api/projects/{project.id}/messages?agent=pm")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert all(m["agent"] == "pm" for m in data["messages"])


@pytest.mark.asyncio
async def test_get_messages_pagination(client, project_with_messages):
    """Test message pagination."""
    project = project_with_messages
    response = await client.get(f"/api/projects/{project.id}/messages?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["total"] == 5  # Total count should still be 5


@pytest.mark.asyncio
async def test_get_messages_empty_project(client, db_engine):
    """Test getting messages for project with no messages."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Empty", idea_text="test", status="created", project_path="/tmp/empty"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

    response = await client.get(f"/api/projects/{project.id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_get_messages_project_not_found(client):
    """Test getting messages for non-existent project."""
    response = await client.get("/api/projects/99999/messages")
    assert response.status_code == 404
