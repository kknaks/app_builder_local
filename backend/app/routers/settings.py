"""Settings router — token management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.settings import TokenSaveRequest, TokenSaveResponse, TokenStatusResponse
from app.services.token_service import get_token_status, save_token

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.post("/token", response_model=TokenSaveResponse)
async def save_api_token(
    request: TokenSaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save Claude API token with AES-256 encryption.

    The token is validated against the Anthropic API before saving.
    """
    is_valid = await save_token(db, request.token)
    return TokenSaveResponse(status="saved", valid=is_valid)


@router.get("/token/status", response_model=TokenStatusResponse)
async def check_token_status(
    db: AsyncSession = Depends(get_db),
):
    """Check if a Claude API token is configured and valid."""
    status = await get_token_status(db)
    return TokenStatusResponse(**status)
