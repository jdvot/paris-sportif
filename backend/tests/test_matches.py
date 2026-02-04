"""Integration tests for match endpoints."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.data.sources.football_data import MatchData


class TestMatchEndpointsAuth:
    """Test suite for match endpoint authentication."""

    def test_get_matches_without_auth(self, client_no_auth: TestClient):
        """Test that matches endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/matches")
        assert response.status_code == 401

    def test_get_match_by_id_without_auth(self, client_no_auth: TestClient):
        """Test that single match endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/matches/12345")
        assert response.status_code == 401

    def test_get_upcoming_matches_without_auth(self, client_no_auth: TestClient):
        """Test that upcoming matches endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/matches/upcoming")
        assert response.status_code == 401

    def test_get_standings_without_auth(self, client_no_auth: TestClient):
        """Test that standings endpoint requires authentication."""
        response = client_no_auth.get("/api/v1/matches/standings/PL")
        assert response.status_code == 401


class TestGetMatches:
    """Test suite for GET /matches endpoint."""

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_matches_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test successful matches retrieval."""
        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(return_value=[MatchData(**sample_match_data)])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_matches_with_competition_filter(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test matches retrieval with competition filter."""
        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(return_value=[MatchData(**sample_match_data)])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches", params={"competition": "PL"})

        assert response.status_code == 200
        mock_client.get_matches.assert_called_once()

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_matches_pagination(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test matches pagination parameters."""
        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(return_value=[MatchData(**sample_match_data)])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches", params={"page": 2, "per_page": 10})

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 10

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_matches_api_error_fallback_to_mock(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test that API errors fallback to mock data."""
        from src.core.exceptions import FootballDataAPIError

        mock_client = AsyncMock()
        mock_client.get_matches = AsyncMock(side_effect=FootballDataAPIError("API Error"))
        mock_api_client.return_value = mock_client

        # Should still return 200 with mock data
        response = client.get("/api/v1/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data


class TestGetMatchById:
    """Test suite for GET /matches/{match_id} endpoint."""

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_match_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test successful single match retrieval."""
        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(return_value=MatchData(**sample_match_data))
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 12345
        assert "home_team" in data
        assert "away_team" in data
        assert "competition" in data

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_match_api_error_fallback(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test match retrieval fallback on API error."""
        from src.core.exceptions import FootballDataAPIError

        mock_client = AsyncMock()
        mock_client.get_match = AsyncMock(side_effect=FootballDataAPIError("API Error"))
        mock_api_client.return_value = mock_client

        # Should return mock match data
        response = client.get("/api/v1/matches/99999")

        assert response.status_code == 200


class TestGetUpcomingMatches:
    """Test suite for GET /matches/upcoming endpoint."""

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_upcoming_matches_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test successful upcoming matches retrieval."""
        mock_client = AsyncMock()
        mock_client.get_upcoming_matches = AsyncMock(return_value=[MatchData(**sample_match_data)])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/upcoming")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_upcoming_matches_with_days_param(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_match_data: dict[str, Any],
    ):
        """Test upcoming matches with days parameter."""
        mock_client = AsyncMock()
        mock_client.get_upcoming_matches = AsyncMock(return_value=[MatchData(**sample_match_data)])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/upcoming", params={"days": 5})

        assert response.status_code == 200
        mock_client.get_upcoming_matches.assert_called_once()


class TestGetStandings:
    """Test suite for GET /matches/standings/{competition_code} endpoint."""

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_standings_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test successful standings retrieval."""
        # Create mock standing entry
        mock_standing = MagicMock()
        mock_standing.position = 1
        mock_standing.team.id = 100
        mock_standing.team.name = "Manchester City"
        mock_standing.team.crest = "https://example.com/mci.png"
        mock_standing.playedGames = 25
        mock_standing.won = 18
        mock_standing.draw = 4
        mock_standing.lost = 3
        mock_standing.goalsFor = 55
        mock_standing.goalsAgainst = 20
        mock_standing.goalDifference = 35
        mock_standing.points = 58

        mock_client = AsyncMock()
        mock_client.get_standings = AsyncMock(return_value=[mock_standing])
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/standings/PL")

        assert response.status_code == 200
        data = response.json()
        assert data["competition_code"] == "PL"
        assert "standings" in data

    def test_get_standings_invalid_competition(self, client: TestClient):
        """Test standings with invalid competition code."""
        response = client.get("/api/v1/matches/standings/INVALID")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid competition" in data["detail"]


class TestHeadToHead:
    """Test suite for GET /matches/{match_id}/head-to-head endpoint."""

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_head_to_head_success(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_finished_match_data: dict[str, Any],
    ):
        """Test successful head-to-head retrieval."""
        mock_client = AsyncMock()
        mock_client.get_head_to_head = AsyncMock(
            return_value=[MatchData(**sample_finished_match_data)]
        )
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/12345/head-to-head")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "home_wins" in data
        assert "draws" in data
        assert "away_wins" in data
        assert "total_matches" in data

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_head_to_head_with_limit(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
        sample_finished_match_data: dict[str, Any],
    ):
        """Test head-to-head with limit parameter."""
        mock_client = AsyncMock()
        mock_client.get_head_to_head = AsyncMock(
            return_value=[MatchData(**sample_finished_match_data)]
        )
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/12345/head-to-head", params={"limit": 5})

        assert response.status_code == 200


class TestTeamForm:
    """Test suite for GET /matches/teams/{team_id}/form endpoint."""

    @patch("src.api.routes.matches.get_football_data_client")
    def test_get_team_form_api_fallback(
        self,
        mock_api_client: MagicMock,
        client: TestClient,
    ):
        """Test team form with API fallback to mock data."""
        from src.core.exceptions import FootballDataAPIError

        mock_client = AsyncMock()
        mock_client.get_team = AsyncMock(side_effect=FootballDataAPIError("API Error"))
        mock_api_client.return_value = mock_client

        response = client.get("/api/v1/matches/teams/100/form")

        # Should return mock form data
        assert response.status_code == 200
        data = response.json()
        assert "team_id" in data
        assert "form_string" in data
        assert "points_last_5" in data
