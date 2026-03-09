"""Tests for settings (token) API endpoints."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestTokenStatusAPI:
    """GET /api/settings/token/status tests."""

    @pytest.mark.asyncio
    @patch("app.services.token_service.asyncio.create_subprocess_exec")
    @patch("app.services.token_service.shutil.which", return_value="/usr/bin/claude")
    async def test_cli_found_and_auth_ok(self, mock_which, mock_exec, client):
        """CLI found and version check succeeds."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"1.0.0", b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["valid"] is True
        assert "1.0.0" in data["message"]

    @pytest.mark.asyncio
    @patch("app.services.token_service.shutil.which", return_value=None)
    async def test_cli_not_found(self, mock_which, client):
        """CLI not installed."""
        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False
        assert data["valid"] is None
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("app.services.token_service.asyncio.create_subprocess_exec")
    @patch("app.services.token_service.shutil.which", return_value="/usr/bin/claude")
    async def test_cli_error(self, mock_which, mock_exec, client):
        """CLI found but version check fails."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error")
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False
        assert data["valid"] is False

    @pytest.mark.asyncio
    @patch("app.services.token_service.asyncio.wait_for")
    @patch("app.services.token_service.asyncio.create_subprocess_exec")
    @patch("app.services.token_service.shutil.which", return_value="/usr/bin/claude")
    async def test_cli_timeout(self, mock_which, mock_exec, mock_wait_for, client):
        """CLI found but version check times out."""
        mock_proc = AsyncMock()
        mock_exec.return_value = mock_proc
        mock_wait_for.side_effect = asyncio.TimeoutError()

        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False
        assert data["valid"] is False
