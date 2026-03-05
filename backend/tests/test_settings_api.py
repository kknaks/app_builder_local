"""Tests for settings (token) API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


class TestTokenSaveAPI:
    """POST /api/settings/token tests."""

    @pytest.mark.asyncio
    @patch("app.services.token_service.validate_claude_token", new_callable=AsyncMock)
    async def test_save_token_valid(self, mock_validate, client):
        """Saving a valid token should return saved + valid=True."""
        mock_validate.return_value = True

        response = await client.post(
            "/api/settings/token",
            json={"token": "sk-ant-api03-valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"
        assert data["valid"] is True

    @pytest.mark.asyncio
    @patch("app.services.token_service.validate_claude_token", new_callable=AsyncMock)
    async def test_save_token_invalid(self, mock_validate, client):
        """Saving an invalid token should return saved + valid=False."""
        mock_validate.return_value = False

        response = await client.post(
            "/api/settings/token",
            json={"token": "invalid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"
        assert data["valid"] is False

    @pytest.mark.asyncio
    async def test_save_token_empty(self, client):
        """Empty token should return 422 validation error."""
        response = await client.post(
            "/api/settings/token",
            json={"token": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_save_token_missing(self, client):
        """Missing token field should return 422 validation error."""
        response = await client.post(
            "/api/settings/token",
            json={},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.services.token_service.validate_claude_token", new_callable=AsyncMock)
    async def test_save_token_upsert(self, mock_validate, client):
        """Saving a token twice should update the existing record."""
        mock_validate.return_value = True

        # Save first time
        await client.post(
            "/api/settings/token",
            json={"token": "first-token"},
        )

        # Save second time (update)
        response = await client.post(
            "/api/settings/token",
            json={"token": "second-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"


class TestTokenStatusAPI:
    """GET /api/settings/token/status tests."""

    @pytest.mark.asyncio
    async def test_status_not_configured(self, client):
        """When no token is saved, should return configured=False."""
        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False
        assert data["valid"] is None

    @pytest.mark.asyncio
    @patch("app.services.token_service.validate_claude_token", new_callable=AsyncMock)
    async def test_status_configured_valid(self, mock_validate, client):
        """When a valid token is saved, should return configured=True, valid=True."""
        mock_validate.return_value = True

        # Save a token first
        await client.post(
            "/api/settings/token",
            json={"token": "sk-ant-api03-valid-token"},
        )

        # Check status
        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["valid"] is True

    @pytest.mark.asyncio
    @patch("app.services.token_service.validate_claude_token", new_callable=AsyncMock)
    async def test_status_configured_invalid(self, mock_validate, client):
        """When an invalid token is saved, should return configured=True, valid=False."""
        # First call (save) returns True, second call (status check) returns False
        mock_validate.side_effect = [True, False]

        await client.post(
            "/api/settings/token",
            json={"token": "sk-ant-api03-was-valid-now-invalid"},
        )

        response = await client.get("/api/settings/token/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["valid"] is False
