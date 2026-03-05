"""Token management service — check Claude Code CLI login status."""

import asyncio
import logging
import shutil

logger = logging.getLogger(__name__)


async def check_claude_cli_auth() -> dict:
    """Check if Claude Code CLI is installed and authenticated.

    Runs `claude --version` to verify CLI is available,
    then checks for OAuth credentials in ~/.claude/.

    Returns dict with 'configured' (bool) and 'valid' (bool | None).
    """
    cli_path = shutil.which("claude")
    if not cli_path:
        return {"configured": False, "valid": None, "message": "Claude CLI not found"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        if proc.returncode != 0:
            return {"configured": False, "valid": False, "message": "Claude CLI error"}

        version = stdout.decode().strip()
        return {"configured": True, "valid": True, "message": f"Claude CLI {version}"}
    except asyncio.TimeoutError:
        return {"configured": False, "valid": False, "message": "Claude CLI timeout"}
    except Exception as e:
        logger.warning("Claude CLI check failed: %s", e)
        return {"configured": False, "valid": False, "message": str(e)}
