"""Data enrichment API endpoints - All additional data for predictions.

Premium endpoints - require premium or admin role.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from src.data.data_enrichment import get_data_enrichment
from src.data.sources.football_data import get_football_data_client
from src.auth import PremiumUser, PREMIUM_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter()


class FormData(BaseModel):
    """Team form data."""
    last_5: list[str] = []
    points: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    clean_sheets: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    form_rating: float = 0.0


class XGEstimate(BaseModel):
    """Estimated xG metrics."""
    estimated_xg: float = 0.0
    estimated_xga: float = 0.0
    offensive_rating: float = 0.0
    defensive_rating: float = 0.0


class OddsData(BaseModel):
    """Bookmaker odds data."""
    home_win: Optional[float] = None
    draw: Optional[float] = None
    away_win: Optional[float] = None
    bookmakers: list[str] = []
    value_detected: bool = False


class WeatherData(BaseModel):
    """Match weather data."""
    available: bool = False
    temperature: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[int] = None
    description: Optional[str] = None
    wind_speed: Optional[float] = None
    rain_probability: Optional[float] = None
    impact: Optional[str] = None


class H2HData(BaseModel):
    """Head-to-head data."""
    total_matches: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    home_goals: int = 0
    away_goals: int = 0
    recent_results: list[str] = []


class StandingsContext(BaseModel):
    """Standings context."""
    home_position: Optional[int] = None
    away_position: Optional[int] = None
    home_points: Optional[int] = None
    away_points: Optional[int] = None
    position_diff: Optional[int] = None
    context_note: str = ""


class FullEnrichmentResponse(BaseModel):
    """Full enrichment data for a match."""
    home_team: str
    away_team: str
    competition: str
    timestamp: str

    # Form data
    home_form: Optional[FormData] = None
    away_form: Optional[FormData] = None

    # xG estimates
    home_xg_estimate: Optional[XGEstimate] = None
    away_xg_estimate: Optional[XGEstimate] = None

    # External data
    odds: Optional[OddsData] = None
    weather: Optional[WeatherData] = None
    h2h: Optional[H2HData] = None
    standings: Optional[StandingsContext] = None


@router.get("/full", response_model=FullEnrichmentResponse, responses=PREMIUM_RESPONSES)
async def get_full_enrichment(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code"),
    match_date: Optional[str] = Query(None, description="Match date YYYY-MM-DD"),
) -> FullEnrichmentResponse:
    """
    Get full enrichment data for a match including:
    - Team form (last 5 matches)
    - xG estimates
    - Bookmaker odds
    - Weather forecast
    - H2H history
    - Standings context
    """
    try:
        # Parse match date
        if match_date:
            parsed_date = datetime.strptime(match_date, "%Y-%m-%d")
        else:
            parsed_date = datetime.now() + timedelta(days=1)

        # Get services
        enrichment_service = get_data_enrichment()
        football_client = get_football_data_client()

        # Fetch data from Football-Data.org
        home_matches = []
        away_matches = []
        h2h_matches = []
        standings_data = []

        try:
            # Get standings
            standings_raw = await football_client.get_standings(competition)
            standings_data = [s.model_dump() for s in standings_raw]
        except Exception as e:
            logger.warning(f"Could not fetch standings: {e}")

        # Get recent matches for both teams (from last 30 days)
        try:
            from datetime import date
            today = date.today()
            date_from = today - timedelta(days=60)

            all_matches = await football_client.get_matches(
                competition=competition,
                date_from=date_from,
                date_to=today,
                status="FINISHED",
            )

            # Filter matches for each team
            for match in all_matches:
                match_dict = match.model_dump()
                home_name = match.homeTeam.name.lower()
                away_name = match.awayTeam.name.lower()

                if home_team.lower() in home_name or home_name in home_team.lower():
                    home_matches.append(match_dict)
                elif home_team.lower() in away_name or away_name in home_team.lower():
                    home_matches.append(match_dict)

                if away_team.lower() in home_name or home_name in away_team.lower():
                    away_matches.append(match_dict)
                elif away_team.lower() in away_name or away_name in away_team.lower():
                    away_matches.append(match_dict)

                # Check for H2H
                if (home_team.lower() in home_name or home_name in home_team.lower()) and \
                   (away_team.lower() in away_name or away_name in away_team.lower()):
                    h2h_matches.append(match_dict)
                elif (away_team.lower() in home_name or home_name in away_team.lower()) and \
                     (home_team.lower() in away_name or away_name in home_team.lower()):
                    h2h_matches.append(match_dict)

            logger.info(f"Found {len(home_matches)} home matches, {len(away_matches)} away matches, {len(h2h_matches)} H2H")

        except Exception as e:
            logger.warning(f"Could not fetch matches: {e}")

        # Get full enrichment
        enrichment = await enrichment_service.enrich_match_data(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            match_date=parsed_date,
            home_recent_matches=home_matches[:10],
            away_recent_matches=away_matches[:10],
            h2h_matches=h2h_matches,
            standings=standings_data,
        )

        # Build response
        return FullEnrichmentResponse(
            home_team=home_team,
            away_team=away_team,
            competition=competition,
            timestamp=enrichment.get("timestamp", datetime.now().isoformat()),
            home_form=FormData(**enrichment["home_form"]) if enrichment.get("home_form") else None,
            away_form=FormData(**enrichment["away_form"]) if enrichment.get("away_form") else None,
            home_xg_estimate=XGEstimate(**enrichment["home_xg_estimate"]) if enrichment.get("home_xg_estimate") else None,
            away_xg_estimate=XGEstimate(**enrichment["away_xg_estimate"]) if enrichment.get("away_xg_estimate") else None,
            odds=OddsData(**enrichment["odds"]) if enrichment.get("odds") else None,
            weather=WeatherData(**enrichment["weather"]) if enrichment.get("weather") else None,
            h2h=H2HData(**enrichment["h2h"]) if enrichment.get("h2h") else None,
            standings=StandingsContext(**enrichment["standings"]) if enrichment.get("standings") else None,
        )

    except Exception as e:
        logger.error(f"Enrichment error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enrich match data: {str(e)}"
        )


@router.get("/odds", responses=PREMIUM_RESPONSES)
async def get_match_odds(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code"),
) -> dict:
    """Get bookmaker odds for a specific match."""
    try:
        enrichment_service = get_data_enrichment()
        odds_data = await enrichment_service.odds_client.get_odds(competition)
        return enrichment_service.odds_client.extract_best_odds(odds_data, home_team, away_team)
    except Exception as e:
        logger.error(f"Odds error: {e}")
        return {"error": str(e), "available": False}


@router.get("/weather", responses=PREMIUM_RESPONSES)
async def get_match_weather(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    match_date: Optional[str] = Query(None, description="Match date YYYY-MM-DD"),
) -> dict:
    """Get weather forecast for match day."""
    try:
        if match_date:
            parsed_date = datetime.strptime(match_date, "%Y-%m-%d")
        else:
            parsed_date = datetime.now() + timedelta(days=1)

        enrichment_service = get_data_enrichment()
        return await enrichment_service.weather_client.get_match_weather(home_team, parsed_date)
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return {"error": str(e), "available": False}


@router.get("/h2h", responses=PREMIUM_RESPONSES)
async def get_h2h(
    user: PremiumUser,
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name"),
    competition: str = Query("PL", description="Competition code"),
) -> dict:
    """Get head-to-head history between two teams."""
    try:
        football_client = get_football_data_client()
        from datetime import date

        # Get matches from last 2 years
        today = date.today()
        date_from = today - timedelta(days=730)

        all_matches = await football_client.get_matches(
            competition=competition,
            date_from=date_from,
            date_to=today,
            status="FINISHED",
        )

        # Filter H2H matches
        h2h_matches = []
        for match in all_matches:
            home_name = match.homeTeam.name.lower()
            away_name = match.awayTeam.name.lower()

            is_h2h = False
            if (home_team.lower() in home_name or home_name in home_team.lower()) and \
               (away_team.lower() in away_name or away_name in away_team.lower()):
                is_h2h = True
            elif (away_team.lower() in home_name or home_name in away_team.lower()) and \
                 (home_team.lower() in away_name or away_name in home_team.lower()):
                is_h2h = True

            if is_h2h:
                h2h_matches.append(match.model_dump())

        # Analyze
        enrichment_service = get_data_enrichment()
        return enrichment_service._analyze_h2h(h2h_matches, home_team, away_team)

    except Exception as e:
        logger.error(f"H2H error: {e}")
        return {"error": str(e), "total_matches": 0}


@router.get("/form/{team_name}", responses=PREMIUM_RESPONSES)
async def get_team_form(
    team_name: str,
    user: PremiumUser,
    competition: str = Query("PL", description="Competition code"),
) -> dict:
    """Get recent form for a team."""
    try:
        football_client = get_football_data_client()
        from datetime import date

        today = date.today()
        date_from = today - timedelta(days=60)

        all_matches = await football_client.get_matches(
            competition=competition,
            date_from=date_from,
            date_to=today,
            status="FINISHED",
        )

        # Filter matches for the team
        team_matches = []
        for match in all_matches:
            home_name = match.homeTeam.name.lower()
            away_name = match.awayTeam.name.lower()

            if team_name.lower() in home_name or home_name in team_name.lower():
                team_matches.append(match.model_dump())
            elif team_name.lower() in away_name or away_name in team_name.lower():
                team_matches.append(match.model_dump())

        # Calculate form
        enrichment_service = get_data_enrichment()
        return enrichment_service.form_calculator.calculate_form(team_matches, team_name)

    except Exception as e:
        logger.error(f"Form error: {e}")
        return {"error": str(e)}


@router.get("/status", responses=PREMIUM_RESPONSES)
async def get_enrichment_status(user: PremiumUser) -> dict:
    """Get status of all enrichment data sources."""
    import os

    return {
        "football_data": {
            "configured": bool(os.getenv("FOOTBALL_DATA_API_KEY")),
            "description": "Matches, standings, H2H"
        },
        "odds_api": {
            "configured": bool(os.getenv("ODDS_API_KEY")),
            "description": "Bookmaker odds (500 req/month free)"
        },
        "open_meteo": {
            "configured": True,  # Open-Meteo is always available, no API key needed
            "description": "Match day weather (free, unlimited)"
        },
        "groq_llm": {
            "configured": bool(os.getenv("GROQ_API_KEY")),
            "description": "News analysis, sentiment"
        },
        "calculated": {
            "form": "From recent matches",
            "xg_estimate": "Approximated from goals/form",
            "h2h": "From historical matches"
        }
    }
