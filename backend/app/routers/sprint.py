"""Sprint planning and implementation router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.sprint import (
    ImplementStartRequest,
    ImplementStartResponse,
    SprintStartRequest,
    SprintStartResponse,
)
from app.services.project_service import get_project
from app.services.sprint_service import start_implementation, start_sprint_planning

router = APIRouter(prefix="/api/projects", tags=["sprint"])


@router.post("/{project_id}/sprint", response_model=SprintStartResponse, status_code=202)
async def start_sprint_plan(
    project_id: int,
    request: SprintStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Start sprint planning: PM Agent creates Phase.md from PRD.

    Parses the resulting Phase.md into flow nodes for the dashboard.
    Broadcasts flow_update via WebSocket.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ("sprint_planning", "reviewing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start sprint planning in '{project.status}' status. "
            f"Expected 'sprint_planning' or 'reviewing'.",
        )

    additional = request.additional_instructions if request else None
    task_id = await start_sprint_planning(db, project, additional)

    return SprintStartResponse(
        status="sprint_planning_started",
        task_id=task_id,
        message="PM Agent가 스프린트 플랜을 작성합니다. Phase.md가 생성됩니다.",
    )


@router.post("/{project_id}/implement", response_model=ImplementStartResponse, status_code=202)
async def start_project_implementation(
    project_id: int,
    request: ImplementStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Start implementation: PM orchestrates BE/FE agents sequentially.

    Each agent runs implement→test→fix loop (max 3 retries).
    On repeated failure, PM escalates to user via chat WebSocket.
    Flow nodes are updated in real-time.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ("sprint_planning", "implementing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start implementation in '{project.status}' status. "
            f"Expected 'sprint_planning' or 'implementing'.",
        )

    max_retries = request.max_retries if request else 3
    task_id = await start_implementation(db, project, max_retries)

    return ImplementStartResponse(
        status="implementation_started",
        task_id=task_id,
        message="PM이 구현을 시작합니다. BE/FE 에이전트가 순차적으로 실행됩니다.",
    )
