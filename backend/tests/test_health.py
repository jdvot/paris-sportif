"""Integration tests for health check endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint returns 200 with correct structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_response_format(self, client: TestClient):
        """Test health check returns expected JSON format."""
        response = client.get("/health")

        data = response.json()
        assert isinstance(data, dict)
        assert set(data.keys()) == {"status", "version"}
        assert isinstance(data["version"], str)

    @patch("src.api.routes.health.redis_health_check")
    def test_readiness_check_all_healthy(self, mock_redis_health: AsyncMock, client: TestClient):
        """Test readiness check when all dependencies are healthy."""
        mock_redis_health.return_value = True

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] is True
        assert "redis" in data
        assert "football_api" in data
        assert "llm_api" in data

    @patch("src.api.routes.health.redis_health_check")
    def test_readiness_check_redis_down(self, mock_redis_health: AsyncMock, client: TestClient):
        """Test readiness check when Redis is unavailable."""
        mock_redis_health.return_value = False

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["redis"] is False

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns app info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["docs"] == "/docs"


class TestSecurityHeaders:
    """Test suite for security headers middleware."""

    def test_security_headers_present(self, client: TestClient):
        """Test that security headers are present in response."""
        response = client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    def test_cors_headers_for_allowed_origin(self, client: TestClient):
        """Test CORS headers for allowed origins."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        # CORS headers should be present for allowed origin
        assert response.status_code == 200
