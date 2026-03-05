"""Agent tasks router — task management, cancel, agent status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.agent_task import (
    AgentStatusListResponse,
    AgentStatusResponse,
    AgentTaskListResponse,
    AgentTaskResponse,
    CancelResponse,
)
from app.services.agent_task_service import (
    cancel_project_tasks,
    cancel_task,
    get_agent_statuses,
    get_task,
    get_tasks_for_project,
)
from app.services.project_service import get_project

router = APIRouter(prefix="/api/projects", tags=["agent-tasks"])


@router.get("/{project_id}/tasks", response_model=AgentTaskListResponse)
async def list_project_tasks(
    project_id: int,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all tasks for a project."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = await get_tasks_for_project(db, project_id, status=status)
    return AgentTaskListResponse(
        tasks=[AgentTaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )


@router.post("/{project_id}/cancel", response_model=CancelResponse)
async def cancel_all_project_tasks(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancel all running/pending tasks for a project."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    count = await cancel_project_tasks(db, project_id)
    return CancelResponse(
        status="cancelled",
        cancelled_count=count,
        message=f"Cancelled {count} task(s) for project {project_id}",
    )


@router.post("/{project_id}/tasks/{task_id}/cancel", response_model=CancelResponse)
async def cancel_single_task(
    project_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a specific task."""
    task = await get_task(db, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("pending", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in '{task.status}' status",
        )

    cancelled = await cancel_task(db, task_id)
    return CancelResponse(
        status="cancelled" if cancelled else "not_found",
        cancelled_count=1 if cancelled else 0,
        message=f"Task {task_id} cancelled" if cancelled else f"Task {task_id} not found or already finished",
    )


@router.get("/{project_id}/agents", response_model=AgentStatusListResponse)
async def get_agents_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get current status of all agents for a project."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    statuses = await get_agent_statuses(db, project_id)
    return AgentStatusListResponse(
        project_id=project_id,
        agents=[AgentStatusResponse(**s) for s in statuses],
    )
