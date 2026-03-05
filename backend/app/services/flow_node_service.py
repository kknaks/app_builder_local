"""Flow node management service.

Handles CRUD + status updates for flow nodes (dashboard visualization).
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ws_manager import ws_manager
from app.models.flow_node import FlowNode

logger = logging.getLogger(__name__)

# Default flow nodes created when planning starts
PLANNING_FLOW_NODES = [
    {"node_type": "idea", "label": "아이디어", "position_x": 0, "position_y": 0},
    {"node_type": "planning", "label": "기획 구체화", "position_x": 200, "position_y": 0},
    {"node_type": "review_be", "label": "BE 검토", "position_x": 400, "position_y": -100},
    {"node_type": "review_fe", "label": "FE 검토", "position_x": 400, "position_y": 0},
    {"node_type": "review_design", "label": "Design 검토", "position_x": 400, "position_y": 100},
    {"node_type": "approval", "label": "승인", "position_x": 600, "position_y": 0},
]

# Parent relationships for planning nodes
PLANNING_PARENTS = {
    "planning": "idea",
    "review_be": "planning",
    "review_fe": "planning",
    "review_design": "planning",
    "approval": "review_be",  # Will link to all review nodes via frontend
}


async def get_flow_nodes(
    db: AsyncSession,
    project_id: int,
) -> list[FlowNode]:
    """Get all flow nodes for a project."""
    stmt = (
        select(FlowNode)
        .where(FlowNode.project_id == project_id)
        .order_by(FlowNode.id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_flow_node_by_type(
    db: AsyncSession,
    project_id: int,
    node_type: str,
) -> FlowNode | None:
    """Get a flow node by project and type."""
    stmt = select(FlowNode).where(
        FlowNode.project_id == project_id,
        FlowNode.node_type == node_type,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_flow_node(
    db: AsyncSession,
    project_id: int,
    node_type: str,
    label: str,
    status: str = "pending",
    parent_node_id: int | None = None,
    position_x: int | None = None,
    position_y: int | None = None,
) -> FlowNode:
    """Create a single flow node."""
    node = FlowNode(
        project_id=project_id,
        node_type=node_type,
        label=label,
        status=status,
        parent_node_id=parent_node_id,
        position_x=position_x,
        position_y=position_y,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def initialize_planning_flow(
    db: AsyncSession,
    project_id: int,
) -> list[FlowNode]:
    """Create the initial set of flow nodes for the planning phase.

    Creates: idea → planning → [BE review, FE review, Design review] → approval
    """
    # Check if nodes already exist
    existing = await get_flow_nodes(db, project_id)
    if existing:
        return existing

    created_nodes: dict[str, FlowNode] = {}

    for node_def in PLANNING_FLOW_NODES:
        node = FlowNode(
            project_id=project_id,
            node_type=node_def["node_type"],
            label=node_def["label"],
            status="completed" if node_def["node_type"] == "idea" else "pending",
            position_x=node_def["position_x"],
            position_y=node_def["position_y"],
        )
        db.add(node)
        await db.flush()  # Get the ID
        created_nodes[node_def["node_type"]] = node

    # Set parent relationships
    for child_type, parent_type in PLANNING_PARENTS.items():
        if child_type in created_nodes and parent_type in created_nodes:
            created_nodes[child_type].parent_node_id = created_nodes[parent_type].id

    await db.commit()

    # Refresh all nodes
    nodes = []
    for node in created_nodes.values():
        await db.refresh(node)
        nodes.append(node)

    return nodes


async def update_node_status(
    db: AsyncSession,
    project_id: int,
    node_type: str,
    status: str,
    broadcast: bool = True,
) -> FlowNode | None:
    """Update a flow node's status and optionally broadcast via WS.

    Status values: pending, active, completed, failed
    """
    node = await get_flow_node_by_type(db, project_id, node_type)
    if not node:
        return None

    node.status = status
    await db.commit()
    await db.refresh(node)

    if broadcast:
        await ws_manager.broadcast(
            project_id,
            "logs",
            {
                "type": "flow_update",
                "node_id": node.id,
                "node_type": node_type,
                "status": status,
                "label": node.label,
            },
        )

    return node
