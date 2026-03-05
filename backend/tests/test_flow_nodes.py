"""Tests for flow node service and API endpoints."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.project import Project
from app.services.flow_node_service import (
    create_flow_node,
    get_flow_node_by_type,
    get_flow_nodes,
    initialize_planning_flow,
    update_node_status,
)


@pytest.fixture
async def db(db_engine):
    """Get a fresh DB session for flow node tests."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def project(db):
    """Create a test project."""
    p = Project(name="Flow Test", idea_text="test flow", status="created", project_path="/tmp/flow_test")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


class TestFlowNodeService:
    """Tests for flow_node_service functions."""

    @pytest.mark.asyncio
    async def test_create_flow_node(self, db, project):
        node = await create_flow_node(
            db, project.id, "idea", "아이디어", status="completed",
            position_x=0, position_y=0,
        )
        assert node.id is not None
        assert node.node_type == "idea"
        assert node.label == "아이디어"
        assert node.status == "completed"
        assert node.position_x == 0

    @pytest.mark.asyncio
    async def test_get_flow_nodes_empty(self, db, project):
        nodes = await get_flow_nodes(db, project.id)
        assert nodes == []

    @pytest.mark.asyncio
    async def test_get_flow_nodes_with_data(self, db, project):
        await create_flow_node(db, project.id, "idea", "아이디어")
        await create_flow_node(db, project.id, "planning", "기획")
        nodes = await get_flow_nodes(db, project.id)
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_get_flow_node_by_type(self, db, project):
        await create_flow_node(db, project.id, "idea", "아이디어")
        node = await get_flow_node_by_type(db, project.id, "idea")
        assert node is not None
        assert node.node_type == "idea"

    @pytest.mark.asyncio
    async def test_get_flow_node_by_type_not_found(self, db, project):
        node = await get_flow_node_by_type(db, project.id, "nonexistent")
        assert node is None

    @pytest.mark.asyncio
    async def test_initialize_planning_flow(self, db, project):
        nodes = await initialize_planning_flow(db, project.id)
        assert len(nodes) == 6

        # Check node types
        node_types = {n.node_type for n in nodes}
        assert node_types == {"idea", "planning", "review_be", "review_fe", "review_design", "approval"}

        # Idea should be completed
        idea = next(n for n in nodes if n.node_type == "idea")
        assert idea.status == "completed"

        # Others should be pending
        planning = next(n for n in nodes if n.node_type == "planning")
        assert planning.status == "pending"

    @pytest.mark.asyncio
    async def test_initialize_planning_flow_idempotent(self, db, project):
        nodes1 = await initialize_planning_flow(db, project.id)
        nodes2 = await initialize_planning_flow(db, project.id)
        # Should return existing nodes, not create duplicates
        assert len(nodes1) == len(nodes2)

    @pytest.mark.asyncio
    async def test_initialize_planning_flow_parent_relationships(self, db, project):
        nodes = await initialize_planning_flow(db, project.id)
        nodes_by_type = {n.node_type: n for n in nodes}

        # planning should have idea as parent
        assert nodes_by_type["planning"].parent_node_id == nodes_by_type["idea"].id

        # review nodes should have planning as parent
        assert nodes_by_type["review_be"].parent_node_id == nodes_by_type["planning"].id
        assert nodes_by_type["review_fe"].parent_node_id == nodes_by_type["planning"].id
        assert nodes_by_type["review_design"].parent_node_id == nodes_by_type["planning"].id

    @pytest.mark.asyncio
    async def test_update_node_status(self, db, project):
        await create_flow_node(db, project.id, "planning", "기획")
        node = await update_node_status(db, project.id, "planning", "active", broadcast=False)
        assert node is not None
        assert node.status == "active"

    @pytest.mark.asyncio
    async def test_update_node_status_not_found(self, db, project):
        node = await update_node_status(db, project.id, "nonexistent", "active", broadcast=False)
        assert node is None

    @pytest.mark.asyncio
    async def test_update_node_status_transitions(self, db, project):
        await create_flow_node(db, project.id, "review_be", "BE 검토")

        # pending → active
        node = await update_node_status(db, project.id, "review_be", "active", broadcast=False)
        assert node.status == "active"

        # active → completed
        node = await update_node_status(db, project.id, "review_be", "completed", broadcast=False)
        assert node.status == "completed"

    @pytest.mark.asyncio
    async def test_update_node_status_to_failed(self, db, project):
        await create_flow_node(db, project.id, "planning", "기획")
        node = await update_node_status(db, project.id, "planning", "failed", broadcast=False)
        assert node.status == "failed"

    @pytest.mark.asyncio
    async def test_flow_nodes_isolated_by_project(self, db):
        """Nodes from different projects should not interfere."""
        p1 = Project(name="P1", idea_text="test", status="created", project_path="/tmp/p1")
        p2 = Project(name="P2", idea_text="test", status="created", project_path="/tmp/p2")
        db.add_all([p1, p2])
        await db.commit()
        await db.refresh(p1)
        await db.refresh(p2)

        await create_flow_node(db, p1.id, "idea", "P1 아이디어")
        await create_flow_node(db, p2.id, "idea", "P2 아이디어")
        await create_flow_node(db, p2.id, "planning", "P2 기획")

        nodes_p1 = await get_flow_nodes(db, p1.id)
        nodes_p2 = await get_flow_nodes(db, p2.id)
        assert len(nodes_p1) == 1
        assert len(nodes_p2) == 2


class TestFlowNodeAPI:
    """Tests for flow node API endpoints."""

    @pytest.mark.asyncio
    async def test_get_flow_empty(self, client):
        """Flow endpoint should return empty for new project."""
        # Create a project first
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        tmpdir = tempfile.mkdtemp()
        with patch("app.services.project_service._get_projects_base_dir", return_value=Path(tmpdir)):
            resp = await client.post(
                "/api/projects",
                json={"name": "Flow Test", "idea_text": "test"},
            )
        project_id = resp.json()["id"]

        response = await client.get(f"/api/projects/{project_id}/flow")
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_flow_not_found(self, client):
        """Flow endpoint should return 404 for non-existent project."""
        response = await client.get("/api/projects/999/flow")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_flow_with_nodes(self, client, db_engine):
        """Flow endpoint should return existing flow nodes."""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            p = Project(name="FlowAPI", idea_text="test", status="created", project_path="/tmp/flowapi")
            session.add(p)
            await session.commit()
            await session.refresh(p)

            await initialize_planning_flow(session, p.id)

        response = await client.get(f"/api/projects/{p.id}/flow")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6
        assert len(data["nodes"]) == 6

        # Verify node structure
        node_types = {n["node_type"] for n in data["nodes"]}
        assert "idea" in node_types
        assert "planning" in node_types
        assert "review_be" in node_types
