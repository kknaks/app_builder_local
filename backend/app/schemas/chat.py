"""Schemas for chat/WebSocket endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageResponse(BaseModel):
    """Response for a single chat message."""

    id: int
    project_id: int
    agent: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageListResponse(BaseModel):
    """Response for chat message list."""

    messages: list[ChatMessageResponse]
    total: int


class WSMessage(BaseModel):
    """WebSocket message protocol."""

    type: str = Field(..., description="Message type: message, switch_agent, ping")
    agent: str | None = Field(None, description="Target agent name")
    content: str | None = Field(None, description="Message content")


class WSResponse(BaseModel):
    """WebSocket response from server."""

    type: str = Field(..., description="Response type: message, error, agent_switched, pong")
    agent: str | None = None
    content: str | None = None
    role: str | None = None
    error: str | None = None


class WSLogMessage(BaseModel):
    """WebSocket log message."""

    type: str = Field(..., description="Log type: log, flow_update")
    agent: str | None = None
    text: str | None = None
    log_type: str = "info"
    node_id: str | None = None
    status: str | None = None
