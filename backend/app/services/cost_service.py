"""Cost/token usage tracking service."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_usage import TokenUsage


async def record_token_usage(
    db: AsyncSession,
    project_id: int,
    agent: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float | None = None,
    agent_task_id: int | None = None,
) -> TokenUsage:
    """Record token usage for an agent task."""
    usage = TokenUsage(
        project_id=project_id,
        agent=agent,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=Decimal(str(cost_usd)) if cost_usd is not None else None,
        agent_task_id=agent_task_id,
    )
    db.add(usage)
    await db.commit()
    await db.refresh(usage)
    return usage


async def get_project_cost(db: AsyncSession, project_id: int) -> dict:
    """Get aggregated cost/token usage for a project.

    Returns dict with total and per-agent breakdown.
    """
    # Overall totals
    total_stmt = select(
        func.coalesce(func.sum(TokenUsage.input_tokens), 0).label("total_input"),
        func.coalesce(func.sum(TokenUsage.output_tokens), 0).label("total_output"),
        func.coalesce(func.sum(TokenUsage.cost_usd), Decimal("0")).label("total_cost"),
    ).where(TokenUsage.project_id == project_id)

    total_result = await db.execute(total_stmt)
    total_row = total_result.one()

    # Per-agent breakdown
    agent_stmt = (
        select(
            TokenUsage.agent,
            func.coalesce(func.sum(TokenUsage.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(TokenUsage.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(TokenUsage.cost_usd), Decimal("0")).label("cost_usd"),
            func.count(TokenUsage.id).label("task_count"),
        )
        .where(TokenUsage.project_id == project_id)
        .group_by(TokenUsage.agent)
        .order_by(TokenUsage.agent)
    )

    agent_result = await db.execute(agent_stmt)
    agent_rows = agent_result.all()

    total_input = int(total_row.total_input)
    total_output = int(total_row.total_output)

    return {
        "project_id": project_id,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_cost_usd": total_row.total_cost or Decimal("0"),
        "agent_breakdown": [
            {
                "agent": row.agent,
                "input_tokens": int(row.input_tokens),
                "output_tokens": int(row.output_tokens),
                "total_tokens": int(row.input_tokens) + int(row.output_tokens),
                "cost_usd": row.cost_usd or Decimal("0"),
                "task_count": int(row.task_count),
            }
            for row in agent_rows
        ],
    }
