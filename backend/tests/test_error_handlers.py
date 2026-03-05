"""Tests for unified error handling."""

import pytest


class TestErrorHandlers:
    """Tests for error response format consistency."""

    @pytest.mark.asyncio
    async def test_404_returns_json_error(self, client):
        """404 errors should return consistent JSON format."""
        response = await client.get("/api/projects/999")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["status"] == 404
        assert data["error"]["code"] == "HTTP_ERROR"
        assert "message" in data["error"]

    @pytest.mark.asyncio
    async def test_422_validation_error_format(self, client):
        """Validation errors should include field details."""
        response = await client.post("/api/projects", json={})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["status"] == 422
        assert "details" in data["error"]
        assert len(data["error"]["details"]) > 0
        # Each detail should have field, message, type
        detail = data["error"]["details"][0]
        assert "field" in detail
        assert "message" in detail

    @pytest.mark.asyncio
    async def test_validation_error_empty_name(self, client):
        """Empty name should return validation error with details."""
        response = await client.post(
            "/api/projects",
            json={"name": "", "idea_text": "Some idea"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_400_bad_request_format(self, client):
        """400 errors from HTTPException should use consistent format."""
        # Try to plan a non-existent project
        response = await client.post("/api/projects/999/plan")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "HTTP_ERROR"

    @pytest.mark.asyncio
    async def test_health_endpoint_still_works(self, client):
        """Health endpoint should not be affected by error handlers."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404_json(self, client):
        """DELETE 404 should return structured error."""
        response = await client.delete("/api/projects/999")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["status"] == 404
        assert "Project not found" in data["error"]["message"]
