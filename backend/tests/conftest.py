"""Pytest configuration and fixtures for API integration tests."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.auth.supabase_auth import get_current_user, get_optional_user

# Mock user data for testing (matches JWT payload structure)
MOCK_USER: dict[str, Any] = {
    "sub": "test-user-123",
    "email": "test@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "app_metadata": {"role": "user"},
    "user_metadata": {},
    "iat": int(datetime.now(UTC).timestamp()),
    "exp": int(datetime.now(UTC).timestamp()) + 3600,
}

MOCK_ADMIN_USER: dict[str, Any] = {
    "sub": "admin-user-456",
    "email": "admin@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "app_metadata": {"role": "admin"},
    "user_metadata": {},
    "iat": int(datetime.now(UTC).timestamp()),
    "exp": int(datetime.now(UTC).timestamp()) + 3600,
}

MOCK_PREMIUM_USER: dict[str, Any] = {
    "sub": "premium-user-789",
    "email": "premium@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "app_metadata": {"role": "premium"},
    "user_metadata": {},
    "iat": int(datetime.now(UTC).timestamp()),
    "exp": int(datetime.now(UTC).timestamp()) + 3600,
}


def get_mock_user() -> dict[str, Any]:
    """Override for get_current_user dependency."""
    return MOCK_USER


def get_mock_admin_user() -> dict[str, Any]:
    """Override for get_current_user dependency (admin)."""
    return MOCK_ADMIN_USER


def get_mock_premium_user() -> dict[str, Any]:
    """Override for get_current_user dependency (premium)."""
    return MOCK_PREMIUM_USER


def get_mock_optional_user() -> dict[str, Any] | None:
    """Override for get_optional_user dependency."""
    return MOCK_USER


@pytest.fixture
def client() -> TestClient:
    """Create a test client with mocked auth for synchronous tests."""
    # Override auth dependencies
    app.dependency_overrides[get_current_user] = get_mock_user
    app.dependency_overrides[get_optional_user] = get_mock_optional_user

    yield TestClient(app)

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth() -> TestClient:
    """Create a test client without auth override (for 401 tests)."""
    # Clear any existing overrides
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture
def client_admin() -> TestClient:
    """Create a test client with admin auth."""
    app.dependency_overrides[get_current_user] = get_mock_admin_user
    app.dependency_overrides[get_optional_user] = get_mock_optional_user

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def client_premium() -> TestClient:
    """Create a test client with premium auth."""
    app.dependency_overrides[get_current_user] = get_mock_premium_user
    app.dependency_overrides[get_optional_user] = get_mock_optional_user

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked auth for async tests."""
    app.dependency_overrides[get_current_user] = get_mock_user
    app.dependency_overrides[get_optional_user] = get_mock_optional_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return mock authorization headers."""
    return {"Authorization": "Bearer test-jwt-token"}


@pytest.fixture
def mock_redis():
    """Mock Redis client for cache tests."""
    with patch("src.core.cache.redis_client") as mock:
        mock_instance = MagicMock()
        mock_instance.get = AsyncMock(return_value=None)
        mock_instance.set = AsyncMock(return_value=True)
        mock_instance.ping = AsyncMock(return_value=True)
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_football_api():
    """Mock football-data.org API client."""
    with patch("src.data.sources.football_data.get_football_data_client") as mock:
        client_mock = MagicMock()
        mock.return_value = client_mock
        yield client_mock


@pytest.fixture
def sample_match_data() -> dict[str, Any]:
    """Sample match data for testing."""
    return {
        "id": 12345,
        "utcDate": "2026-02-05T20:00:00Z",
        "status": "SCHEDULED",
        "matchday": 25,
        "homeTeam": {
            "id": 100,
            "name": "Manchester City",
            "shortName": "Man City",
            "tla": "MCI",
            "crest": "https://example.com/mci.png",
        },
        "awayTeam": {
            "id": 101,
            "name": "Liverpool",
            "shortName": "Liverpool",
            "tla": "LIV",
            "crest": "https://example.com/liv.png",
        },
        "competition": {
            "id": 1,
            "name": "Premier League",
            "code": "PL",
        },
        "score": {
            "fullTime": {"home": None, "away": None},
            "halfTime": {"home": None, "away": None},
        },
    }


@pytest.fixture
def sample_finished_match_data(sample_match_data: dict[str, Any]) -> dict[str, Any]:
    """Sample finished match data for testing."""
    data = sample_match_data.copy()
    data["status"] = "FINISHED"
    data["score"] = {
        "fullTime": {"home": 2, "away": 1},
        "halfTime": {"home": 1, "away": 0},
    }
    return data


@pytest.fixture
def sample_standings_data() -> list[dict[str, Any]]:
    """Sample standings data for testing."""
    return [
        {
            "position": 1,
            "team": {"id": 100, "name": "Manchester City", "crest": "https://example.com/mci.png"},
            "playedGames": 25,
            "won": 18,
            "draw": 4,
            "lost": 3,
            "goalsFor": 55,
            "goalsAgainst": 20,
            "goalDifference": 35,
            "points": 58,
        },
        {
            "position": 2,
            "team": {"id": 101, "name": "Liverpool", "crest": "https://example.com/liv.png"},
            "playedGames": 25,
            "won": 17,
            "draw": 5,
            "lost": 3,
            "goalsFor": 52,
            "goalsAgainst": 22,
            "goalDifference": 30,
            "points": 56,
        },
    ]
