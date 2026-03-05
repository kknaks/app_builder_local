"""Schemas for agent task endpoints."""

from datetime import datetime

from pydantic import BaseModel


class AgentTaskResponse(BaseModel):
    """Response for a single agent task."""

    id: int
    project_id: int
    agent: str
    command: str
    status: str
    result: str | None
    error: str | None
    started_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentTaskListResponse(BaseModel):
    """Response for agent task list."""

    tasks: list[AgentTaskResponse]
    total: int


class CancelResponse(BaseModel):
    """Response for cancel operations."""

    status: str
    cancelled_count: int = 0
    message: str


class AgentStatusResponse(BaseModel):
    """Status of a single agent."""

    agent: str
    status: str  # idle, running, completed, failed
    current_task_id: int | None = None
    last_task_status: str | None = None


class AgentStatusListResponse(BaseModel):
    """Response for all agents status."""

    project_id: int
    agents: list[AgentStatusResponse]
