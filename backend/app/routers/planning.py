"""Planning flow router — plan, review, approve, feedback endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.planning import (
    ApproveRequest,
    ApproveResponse,
    FeedbackRequest,
    FeedbackResponse,
    PlanStartRequest,
    PlanStartResponse,
    ReviewStartResponse,
)
from app.services.planning_service import (
    approve_plan,
    send_feedback,
    start_planning,
    start_review,
)
from app.services.project_service import get_project

router = APIRouter(prefix="/api/projects", tags=["planning"])


@router.post("/{project_id}/plan", response_model=PlanStartResponse, status_code=202)
async def start_project_planning(
    project_id: int,
    request: PlanStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Start planning phase: spawn Planner Agent to create detailed plan.

    The planner uses plan_form.md template and the project idea to
    generate a comprehensive project specification.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ("created", "planning"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start planning in '{project.status}' status. Expected 'created' or 'planning'.",
        )

    additional_context = request.additional_context if request else None
    task_id = await start_planning(db, project, additional_context)

    return PlanStartResponse(
        status="planning_started",
        task_id=task_id,
        message="Planner Agent가 기획을 시작했습니다. 채팅에서 결과를 확인하세요.",
    )


@router.post("/{project_id}/review", response_model=ReviewStartResponse, status_code=202)
async def start_project_review(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Start review phase: spawn BE/FE/Design agents for parallel review.

    Maximum 2 agents run concurrently (semaphore limited).
    PM collects results and sends summary to user.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ("planning", "reviewing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start review in '{project.status}' status. Expected 'planning'.",
        )

    task_ids = await start_review(db, project)

    return ReviewStartResponse(
        status="review_started",
        task_ids=task_ids,
        message="BE/FE/Design 에이전트가 기획 검토를 시작했습니다.",
    )


@router.post("/{project_id}/approve", response_model=ApproveResponse)
async def approve_project_plan(
    project_id: int,
    request: ApproveRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Approve the plan: finalize PRD.md and transition to sprint planning.

    Saves PRD.md to project directory and updates status to 'sprint_planning'.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ("planning", "reviewing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve in '{project.status}' status. Expected 'planning' or 'reviewing'.",
        )

    prd_content = request.prd_content if request else None
    prd_path = await approve_plan(db, project, prd_content)

    return ApproveResponse(
        status="approved",
        prd_path=prd_path,
        message="PRD가 승인되었습니다. 스프린트 플래닝으로 전환합니다.",
    )


@router.post("/{project_id}/feedback", response_model=FeedbackResponse)
async def send_project_feedback(
    project_id: int,
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send feedback to re-plan: Planner Agent modifies plan based on feedback.

    Resets review nodes and triggers a new planning iteration.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ("planning", "reviewing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send feedback in '{project.status}' status. Expected 'planning' or 'reviewing'.",
        )

    task_id = await send_feedback(db, project, request.feedback)

    return FeedbackResponse(
        status="feedback_sent",
        task_id=task_id,
        message="피드백이 전달되었습니다. Planner가 기획을 수정합니다.",
    )
