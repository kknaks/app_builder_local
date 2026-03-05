"""Schemas for project endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Request body for creating a project."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    idea_text: str = Field(..., min_length=1, description="Project idea description")


class ProjectResponse(BaseModel):
    """Response for a single project."""

    id: int
    name: str
    idea_text: str
    status: str
    project_path: str
    current_phase: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Response for project list."""

    projects: list[ProjectResponse]
    total: int


class ProjectDeleteResponse(BaseModel):
    """Response for project deletion."""

    status: str = "deleted"
    id: int
