"""Agent task management service.

Handles task lifecycle: create, update status, cancel, and cleanup on restart.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runner import process_manager
from app.models.agent_task import AgentTask

logger = logging.getLogger(__name__)

# Known agent names
AGENT_NAMES = ["pm", "planner", "backend", "frontend", "design"]


async def create_task(
    db: AsyncSession,
    project_id: int,
    agent: str,
    command: str,
) -> AgentTask:
    """Create a new agent task in pending status."""
    task = AgentTask(
        project_id=project_id,
        agent=agent,
        command=command,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task_status(
    db: AsyncSession,
    task_id: int,
    status: str,
    result: str | None = None,
    error: str | None = None,
) -> AgentTask | None:
    """Update task status and optional result/error."""
    stmt = select(AgentTask).where(AgentTask.id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()

    if not task:
        return None

    task.status = status
    task.updated_at = datetime.now(UTC)

    if status == "running" and task.started_at is None:
        task.started_at = datetime.now(UTC)

    if result is not None:
        task.result = result
    if error is not None:
        task.error = error

    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: int) -> AgentTask | None:
    """Get a task by ID."""
    result = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
    return result.scalar_one_or_none()


async def get_tasks_for_project(
    db: AsyncSession,
    project_id: int,
    status: str | None = None,
) -> list[AgentTask]:
    """Get all tasks for a project, optionally filtered by status."""
    stmt = select(AgentTask).where(AgentTask.project_id == project_id)
    if status:
        stmt = stmt.where(AgentTask.status == status)
    stmt = stmt.order_by(AgentTask.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def cancel_task(db: AsyncSession, task_id: int) -> bool:
    """Cancel a running task: kill process + update DB.

    Returns True if task was found and cancelled.
    """
    task = await get_task(db, task_id)
    if not task:
        return False

    if task.status not in ("pending", "running"):
        return False

    # Kill process if running
    if task.status == "running":
        await process_manager.cancel_task(task_id)

    task.status = "cancelled"
    task.updated_at = datetime.now(UTC)
    await db.commit()
    return True


async def cancel_project_tasks(db: AsyncSession, project_id: int) -> int:
    """Cancel all running/pending tasks for a project.

    Returns number of tasks cancelled.
    """
    # Kill running processes
    await process_manager.cancel_project(project_id)

    # Update DB
    stmt = (
        update(AgentTask)
        .where(
            AgentTask.project_id == project_id,
            AgentTask.status.in_(["pending", "running"]),
        )
        .values(status="cancelled", updated_at=datetime.now(UTC))
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount  # type: ignore[return-value]


async def cleanup_stale_tasks(db: AsyncSession) -> int:
    """Mark all running tasks as failed (for server restart).

    Returns number of tasks cleaned up.
    """
    stmt = (
        update(AgentTask)
        .where(AgentTask.status == "running")
        .values(
            status="failed",
            error="Server restarted while task was running",
            updated_at=datetime.now(UTC),
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount  # type: ignore[assignment]
    if count:
        logger.info("Cleaned up %d stale running tasks on startup", count)
    return count


async def get_agent_statuses(
    db: AsyncSession,
    project_id: int,
) -> list[dict]:
    """Get current status of each agent for a project."""
    statuses = []

    for agent_name in AGENT_NAMES:
        # Get latest task for this agent
        stmt = (
            select(AgentTask)
            .where(
                AgentTask.project_id == project_id,
                AgentTask.agent == agent_name,
            )
            .order_by(AgentTask.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest_task = result.scalar_one_or_none()

        # Check if process is currently running
        proc = process_manager.get_process(latest_task.id) if latest_task else None

        if proc and proc.is_alive():
            status = "running"
        elif latest_task:
            status = latest_task.status if latest_task.status in ("running", "completed", "failed") else "idle"
        else:
            status = "idle"

        statuses.append(
            {
                "agent": agent_name,
                "status": status,
                "current_task_id": latest_task.id if latest_task and status == "running" else None,
                "last_task_status": latest_task.status if latest_task else None,
            }
        )

    return statuses
