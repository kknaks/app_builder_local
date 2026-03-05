"""Schemas for flow node endpoints."""

from datetime import datetime

from pydantic import BaseModel


class FlowNodeResponse(BaseModel):
    """Response for a single flow node."""

    id: int
    project_id: int
    node_type: str
    label: str
    status: str
    parent_node_id: int | None = None
    position_x: int | None = None
    position_y: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlowNodeListResponse(BaseModel):
    """Response for flow node list."""

    nodes: list[FlowNodeResponse]
    total: int
