"""Schemas for planning flow endpoints."""

from pydantic import BaseModel, Field


class PlanStartRequest(BaseModel):
    """Request body for starting planning."""

    additional_context: str | None = Field(
        None, description="Additional context or instructions for the planner"
    )


class PlanStartResponse(BaseModel):
    """Response for plan start."""

    status: str = "planning_started"
    task_id: int
    message: str


class ReviewStartResponse(BaseModel):
    """Response for review start."""

    status: str = "review_started"
    task_ids: list[int]
    message: str


class ApproveRequest(BaseModel):
    """Request body for approving a plan."""

    prd_content: str | None = Field(
        None, description="Final PRD content (if not provided, uses latest planner output)"
    )


class ApproveResponse(BaseModel):
    """Response for plan approval."""

    status: str = "approved"
    prd_path: str
    message: str


class FeedbackRequest(BaseModel):
    """Request body for providing feedback."""

    feedback: str = Field(..., min_length=1, description="Feedback content")


class FeedbackResponse(BaseModel):
    """Response for feedback submission."""

    status: str = "feedback_sent"
    task_id: int
    message: str
