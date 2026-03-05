"""Schemas for sprint planning and implementation endpoints."""

from pydantic import BaseModel, Field


class SprintStartRequest(BaseModel):
    """Request body for starting sprint planning."""

    additional_instructions: str | None = Field(
        None, description="Additional instructions for sprint planning"
    )


class SprintStartResponse(BaseModel):
    """Response for sprint plan start."""

    status: str = "sprint_planning_started"
    task_id: int
    message: str


class ImplementStartRequest(BaseModel):
    """Request body for starting implementation."""

    max_retries: int = Field(
        3, ge=1, le=5, description="Maximum error auto-fix retries per agent"
    )


class ImplementStartResponse(BaseModel):
    """Response for implementation start."""

    status: str = "implementation_started"
    task_id: int
    message: str


class SprintFlowNode(BaseModel):
    """A flow node parsed from Phase.md."""

    node_type: str
    label: str
    agent: str  # "backend", "frontend", "design", "test"
    sprint: str  # e.g., "S1"
    parent_node_type: str | None = None
