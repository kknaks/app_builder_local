"""Schemas for cost/token usage endpoints."""

from decimal import Decimal

from pydantic import BaseModel


class AgentCostBreakdown(BaseModel):
    """Cost breakdown for a single agent."""

    agent: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    task_count: int


class ProjectCostResponse(BaseModel):
    """Response for project cost/token usage."""

    project_id: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: Decimal
    agent_breakdown: list[AgentCostBreakdown]
