"""Chat message service — save and retrieve chat messages."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage


async def save_message(
    db: AsyncSession,
    project_id: int,
    agent: str,
    role: str,
    content: str,
) -> ChatMessage:
    """Save a chat message to the database."""
    message = ChatMessage(
        project_id=project_id,
        agent=agent,
        role=role,
        content=content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(
    db: AsyncSession,
    project_id: int,
    agent: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ChatMessage]:
    """Get chat messages for a project, optionally filtered by agent."""
    stmt = select(ChatMessage).where(ChatMessage.project_id == project_id)
    if agent:
        stmt = stmt.where(ChatMessage.agent == agent)
    stmt = stmt.order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_message_count(
    db: AsyncSession,
    project_id: int,
    agent: str | None = None,
) -> int:
    """Get total message count for a project."""
    from sqlalchemy import func

    stmt = select(func.count(ChatMessage.id)).where(ChatMessage.project_id == project_id)
    if agent:
        stmt = stmt.where(ChatMessage.agent == agent)
    result = await db.execute(stmt)
    return result.scalar_one()
