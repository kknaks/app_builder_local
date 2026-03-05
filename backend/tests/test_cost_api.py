"""Tests for cost API endpoints."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project
from app.models.token_usage import TokenUsage


@pytest.fixture
async def project_with_usage(db_engine):
    """Create a project with token usage records."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Cost Test", idea_text="test", status="created", project_path="/tmp/cost_test"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # Add token usage records
        usages = [
            TokenUsage(
                project_id=project.id,
                agent="pm",
                input_tokens=1000,
                output_tokens=500,
                cost_usd=Decimal("0.0150"),
            ),
            TokenUsage(
                project_id=project.id,
                agent="pm",
                input_tokens=2000,
                output_tokens=800,
                cost_usd=Decimal("0.0280"),
            ),
            TokenUsage(
                project_id=project.id,
                agent="backend",
                input_tokens=3000,
                output_tokens=1500,
                cost_usd=Decimal("0.0450"),
            ),
        ]
        db.add_all(usages)
        await db.commit()

    return project


@pytest.mark.asyncio
async def test_get_cost(client, project_with_usage):
    """Test getting project cost."""
    project = project_with_usage
    response = await client.get(f"/api/projects/{project.id}/cost")
    assert response.status_code == 200
    data = response.json()

    assert data["project_id"] == project.id
    assert data["total_input_tokens"] == 6000
    assert data["total_output_tokens"] == 2800
    assert data["total_tokens"] == 8800
    # total_cost_usd is returned as string from Decimal
    assert Decimal(data["total_cost_usd"]) == Decimal("0.0880")

    # Check agent breakdown
    agents = {a["agent"]: a for a in data["agent_breakdown"]}
    assert len(agents) == 2  # pm and backend

    pm = agents["pm"]
    assert pm["input_tokens"] == 3000
    assert pm["output_tokens"] == 1300
    assert pm["total_tokens"] == 4300
    assert pm["task_count"] == 2

    be = agents["backend"]
    assert be["input_tokens"] == 3000
    assert be["output_tokens"] == 1500
    assert be["total_tokens"] == 4500
    assert be["task_count"] == 1


@pytest.mark.asyncio
async def test_get_cost_empty_project(client, db_engine):
    """Test getting cost for project with no usage."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        project = Project(
            name="Empty", idea_text="test", status="created", project_path="/tmp/empty"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

    response = await client.get(f"/api/projects/{project.id}/cost")
    assert response.status_code == 200
    data = response.json()
    assert data["total_input_tokens"] == 0
    assert data["total_output_tokens"] == 0
    assert data["total_tokens"] == 0
    assert len(data["agent_breakdown"]) == 0


@pytest.mark.asyncio
async def test_get_cost_project_not_found(client):
    """Test getting cost for non-existent project."""
    response = await client.get("/api/projects/99999/cost")
    assert response.status_code == 404
