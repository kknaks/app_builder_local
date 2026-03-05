"""Schemas for settings endpoints."""

from pydantic import BaseModel


class TokenStatusResponse(BaseModel):
    """Response for Claude CLI auth status check."""

    configured: bool
    valid: bool | None = None
    message: str | None = None
