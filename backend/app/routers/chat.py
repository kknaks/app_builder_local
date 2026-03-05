"""Chat router — chat message history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.chat import ChatMessageListResponse, ChatMessageResponse
from app.services.chat_service import get_message_count, get_messages
from app.services.project_service import get_project

router = APIRouter(prefix="/api/projects", tags=["chat"])


@router.get("/{project_id}/messages", response_model=ChatMessageListResponse)
async def get_chat_messages(
    project_id: int,
    agent: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get chat messages for a project, optionally filtered by agent."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    messages = await get_messages(db, project_id, agent=agent, limit=limit, offset=offset)
    total = await get_message_count(db, project_id, agent=agent)
    return ChatMessageListResponse(
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        total=total,
    )
