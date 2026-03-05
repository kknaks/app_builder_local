"""Cost router — token usage and cost tracking."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.cost import AgentCostBreakdown, ProjectCostResponse
from app.services.cost_service import get_project_cost
from app.services.project_service import get_project

router = APIRouter(prefix="/api/projects", tags=["cost"])


@router.get("/{project_id}/cost", response_model=ProjectCostResponse)
async def get_cost(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get token usage and cost for a project."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cost_data = await get_project_cost(db, project_id)
    return ProjectCostResponse(
        project_id=cost_data["project_id"],
        total_input_tokens=cost_data["total_input_tokens"],
        total_output_tokens=cost_data["total_output_tokens"],
        total_tokens=cost_data["total_tokens"],
        total_cost_usd=cost_data["total_cost_usd"],
        agent_breakdown=[AgentCostBreakdown(**a) for a in cost_data["agent_breakdown"]],
    )
