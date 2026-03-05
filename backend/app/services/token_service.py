"""Token management service — save, validate, check status."""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt, encrypt
from app.models.setting import Setting

TOKEN_KEY = "claude_api_token"


async def validate_claude_token(token: str) -> bool:
    """Validate a Claude API token by making a lightweight API call.

    Uses the Anthropic messages endpoint with minimal payload.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": token,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            # 200 = valid token; 401 = invalid token
            return response.status_code == 200
    except (httpx.HTTPError, Exception):
        return False


async def save_token(db: AsyncSession, token: str) -> bool:
    """Save an encrypted Claude API token to the database.

    Returns True if the token is valid (validation result).
    """
    is_valid = await validate_claude_token(token)

    encrypted = encrypt(token, settings.ENCRYPTION_KEY)

    # Upsert: update if exists, insert otherwise
    result = await db.execute(select(Setting).where(Setting.key == TOKEN_KEY))
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = encrypted
    else:
        setting = Setting(key=TOKEN_KEY, value=encrypted)
        db.add(setting)

    await db.commit()
    return is_valid


async def get_token_status(db: AsyncSession) -> dict:
    """Check if a Claude API token is configured.

    Returns dict with 'configured' (bool) and 'valid' (bool | None).
    """
    result = await db.execute(select(Setting).where(Setting.key == TOKEN_KEY))
    setting = result.scalar_one_or_none()

    if not setting:
        return {"configured": False, "valid": None}

    # Try to decrypt and validate
    try:
        token = decrypt(setting.value, settings.ENCRYPTION_KEY)
        is_valid = await validate_claude_token(token)
        return {"configured": True, "valid": is_valid}
    except Exception:
        return {"configured": True, "valid": False}
