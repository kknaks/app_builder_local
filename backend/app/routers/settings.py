"""Settings router — Claude CLI auth status endpoint."""

from fastapi import APIRouter

from app.schemas.settings import TokenStatusResponse
from app.services.token_service import check_claude_cli_auth

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/token/status", response_model=TokenStatusResponse)
async def check_token_status():
    """Check if Claude Code CLI is authenticated."""
    status = await check_claude_cli_auth()
    return TokenStatusResponse(**status)
