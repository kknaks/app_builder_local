"""Flow nodes router — flow node CRUD for dashboard visualization."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.flow_node import FlowNodeListResponse, FlowNodeResponse
from app.services.flow_node_service import get_flow_nodes
from app.services.project_service import get_project

router = APIRouter(prefix="/api/projects", tags=["flow-nodes"])


@router.get("/{project_id}/flow", response_model=FlowNodeListResponse)
async def get_project_flow(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all flow nodes for a project's dashboard visualization."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    nodes = await get_flow_nodes(db, project_id)
    return FlowNodeListResponse(
        nodes=[FlowNodeResponse.model_validate(n) for n in nodes],
        total=len(nodes),
    )
