"""Schemas for settings endpoints."""

from pydantic import BaseModel, Field


class TokenSaveRequest(BaseModel):
    """Request body for saving Claude API token."""

    token: str = Field(..., min_length=1, description="Claude API token")


class TokenSaveResponse(BaseModel):
    """Response after saving token."""

    status: str = "saved"
    valid: bool


class TokenStatusResponse(BaseModel):
    """Response for token status check."""

    configured: bool
    valid: bool | None = None  # None when not configured
