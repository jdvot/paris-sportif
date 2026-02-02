"""Data enrichment module - Integrates multiple data sources for improved predictions.

Sources:
1. Football-Data.org - Matches, standings, H2H (already integrated)
2. The Odds API - Bookmaker odds for value detection
3. OpenWeatherMap - Match day weather
4. Calculated stats - Form, xG approximation
"""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class OddsAPIClient:
    """Client for The Odds API - Free tier: 500 requests/month."""

    BASE_URL = "https://api.the-odds-api.com/v4"

    # Sport keys for football
    SPORT_KEYS = {
        "PL": "soccer_epl",
        "PD": "soccer_spain_la_liga",
        "BL1": "soccer_germany_bundesliga",
        "SA": "soccer_italy_serie_a",
        "FL1": "soccer_france_ligue_one",
        "CL": "soccer_uefa_champs_league",
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        if not self.api_key:
            logger.warning("ODDS_API_KEY not configured - odds features disabled")

    async def get_odds(
        self,
        competition: str,
        markets: str = "h2h",  # h2h, spreads, totals
        regions: str = "eu",
    ) -> list[dict]:
        """Get current odds for a competition."""
        if not self.api_key:
            return []

        sport_key = self.SPORT_KEYS.get(competition)
        if not sport_key:
            logger.warning(f"Unknown competition for odds: {competition}")
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/sports/{sport_key}/odds",
                    params={
                        "apiKey": self.api_key,
                        "regions": regions,
                        "markets": markets,
                        "oddsFormat": "decimal",
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Fetched odds for {len(data)} matches in {competition}")
                    return data
                elif response.status_code == 401:
                    logger.error("Invalid ODDS_API_KEY")
                elif response.status_code == 429:
                    logger.warning("Odds API rate limit reached")
                else:
                    logger.error(f"Odds API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching odds: {e}")

        return []

    def extract_best_odds(self, odds_data: list[dict], home_team: str, away_team: str) -> dict:
        """Extract best odds for a specific match."""
        result = {
            "home_win": None,
            "draw": None,
            "away_win": None,
            "bookmakers": [],
            "value_detected": False,
        }

        # Find the match
        for match in odds_data:
            match_home = match.get("home_team", "").lower()
            match_away = match.get("away_team", "").lower()

            if home_team.lower() in match_home or match_home in home_team.lower():
                if away_team.lower() in match_away or match_away in away_team.lower():
                    # Found the match - extract odds
                    bookmakers = match.get("bookmakers", [])

                    home_odds = []
                    draw_odds = []
                    away_odds = []

                    for bm in bookmakers[:5]:  # Top 5 bookmakers
                        for market in bm.get("markets", []):
                            if market.get("key") == "h2h":
                                outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                                if match.get("home_team") in outcomes:
                                    home_odds.append(outcomes[match.get("home_team")])
                                if "Draw" in outcomes:
                                    draw_odds.append(outcomes["Draw"])
                                if match.get("away_team") in outcomes:
                                    away_odds.append(outcomes[match.get("away_team")])
                                result["bookmakers"].append(bm.get("title"))

                    # Get best (highest) odds
                    if home_odds:
                        result["home_win"] = max(home_odds)
                    if draw_odds:
                        result["draw"] = max(draw_odds)
                    if away_odds:
                        result["away_win"] = max(away_odds)

                    break

        return result


class WeatherClient:
    """Client for OpenWeatherMap API - Free tier: 1000 requests/day."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    # Stadium coordinates for major teams
    STADIUM_COORDS = {
        # Premier League
        "Arsenal": (51.5549, -0.1084),
        "Chelsea": (51.4817, -0.1910),
        "Manchester United": (53.4631, -2.2913),
        "Manchester City": (53.4831, -2.2004),
        "Liverpool": (53.4308, -2.9609),
        "Tottenham": (51.6043, -0.0661),
        # La Liga
        "Real Madrid": (40.4530, -3.6883),
        "Barcelona": (41.3809, 2.1228),
        "Atletico Madrid": (40.4361, -3.5994),
        # Serie A
        "Juventus": (45.1096, 7.6413),
        "AC Milan": (45.4781, 9.1240),
        "Inter": (45.4781, 9.1240),
        # Bundesliga
        "Bayern Munich": (48.2188, 11.6247),
        "Borussia Dortmund": (51.4926, 7.4519),
        # Ligue 1
        "PSG": (48.8414, 2.2530),
        "Paris Saint-Germain": (48.8414, 2.2530),
        "Marseille": (43.2699, 5.3959),
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")
        if not self.api_key:
            logger.info("OPENWEATHER_API_KEY not configured - weather features disabled")

    async def get_match_weather(
        self,
        home_team: str,
        match_date: datetime
    ) -> dict[str, Any]:
        """Get weather forecast for match day at stadium location."""
        if not self.api_key:
            return {"available": False}

        # Find stadium coordinates
        coords = None
        for team_name, team_coords in self.STADIUM_COORDS.items():
            if team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower():
                coords = team_coords
                break

        if not coords:
            logger.info(f"No stadium coords for {home_team}")
            return {"available": False, "reason": "stadium_not_found"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use 5-day forecast API
                response = await client.get(
                    f"{self.BASE_URL}/forecast",
                    params={
                        "lat": coords[0],
                        "lon": coords[1],
                        "appid": self.api_key,
                        "units": "metric",
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    # Find forecast closest to match time
                    match_ts = match_date.timestamp()
                    closest_forecast = None
                    min_diff = float('inf')

                    for forecast in data.get("list", []):
                        forecast_ts = forecast.get("dt", 0)
                        diff = abs(forecast_ts - match_ts)
                        if diff < min_diff:
                            min_diff = diff
                            closest_forecast = forecast

                    if closest_forecast:
                        weather = closest_forecast.get("weather", [{}])[0]
                        main = closest_forecast.get("main", {})
                        wind = closest_forecast.get("wind", {})

                        return {
                            "available": True,
                            "temperature": main.get("temp"),
                            "feels_like": main.get("feels_like"),
                            "humidity": main.get("humidity"),
                            "description": weather.get("description"),
                            "wind_speed": wind.get("speed"),  # m/s
                            "rain_probability": closest_forecast.get("pop", 0) * 100,
                            "impact": self._assess_weather_impact(
                                main.get("temp", 15),
                                wind.get("speed", 0),
                                closest_forecast.get("pop", 0)
                            )
                        }

        except Exception as e:
            logger.error(f"Error fetching weather: {e}")

        return {"available": False}

    def _assess_weather_impact(self, temp: float, wind_speed: float, rain_prob: float) -> str:
        """Assess how weather might impact the match."""
        impacts = []

        if temp < 5:
            impacts.append("cold_conditions")
        elif temp > 30:
            impacts.append("hot_conditions")

        if wind_speed > 10:  # > 36 km/h
            impacts.append("strong_wind")

        if rain_prob > 0.6:
            impacts.append("likely_rain")

        if not impacts:
            return "favorable"
        return ",".join(impacts)


class FormCalculator:
    """Calculate team form from recent results."""

    @staticmethod
    def calculate_form(matches: list[dict], team_name: str) -> dict:
        """Calculate form stats from last N matches."""
        form = {
            "last_5": [],
            "points": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "clean_sheets": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "form_rating": 0.0,  # 0-100
        }

        for match in matches[:5]:
            home_team = match.get("homeTeam", {}).get("name", "")
            away_team = match.get("awayTeam", {}).get("name", "")
            score = match.get("score", {})

            if not score or not score.get("fullTime"):
                continue

            home_goals = score["fullTime"].get("home", 0) or 0
            away_goals = score["fullTime"].get("away", 0) or 0

            is_home = team_name.lower() in home_team.lower()

            if is_home:
                team_goals = home_goals
                opponent_goals = away_goals
            else:
                team_goals = away_goals
                opponent_goals = home_goals

            form["goals_scored"] += team_goals
            form["goals_conceded"] += opponent_goals

            if opponent_goals == 0:
                form["clean_sheets"] += 1

            if team_goals > opponent_goals:
                form["last_5"].append("W")
                form["wins"] += 1
                form["points"] += 3
            elif team_goals < opponent_goals:
                form["last_5"].append("L")
                form["losses"] += 1
            else:
                form["last_5"].append("D")
                form["draws"] += 1
                form["points"] += 1

        # Calculate form rating (0-100)
        max_points = len(form["last_5"]) * 3
        if max_points > 0:
            form["form_rating"] = (form["points"] / max_points) * 100

        return form


class XGApproximator:
    """Approximate xG from available stats when real xG isn't available."""

    @staticmethod
    def estimate_team_xg(
        goals_scored: float,
        goals_conceded: float,
        form_rating: float,
        is_home: bool = False,
    ) -> dict:
        """Estimate xG-like metrics from basic stats."""
        # Base xG approximation from goals
        base_xg = goals_scored * 0.9  # Regress slightly to mean

        # Adjust for form
        form_modifier = 1 + ((form_rating - 50) / 100) * 0.2

        # Home advantage
        home_modifier = 1.1 if is_home else 0.95

        estimated_xg = base_xg * form_modifier * home_modifier

        # Defensive strength (lower = better)
        defensive_xg = goals_conceded * 0.9

        return {
            "estimated_xg": round(estimated_xg, 2),
            "estimated_xga": round(defensive_xg, 2),
            "offensive_rating": min(100, max(0, estimated_xg * 50)),
            "defensive_rating": max(0, 100 - defensive_xg * 50),
        }


class DataEnrichmentService:
    """Main service that combines all data sources."""

    def __init__(self):
        self.odds_client = OddsAPIClient()
        self.weather_client = WeatherClient()
        self.form_calculator = FormCalculator()
        self.xg_approximator = XGApproximator()

    async def enrich_match_data(
        self,
        home_team: str,
        away_team: str,
        competition: str,
        match_date: datetime,
        home_recent_matches: list[dict] | None = None,
        away_recent_matches: list[dict] | None = None,
        h2h_matches: list[dict] | None = None,
        standings: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Get all enrichment data for a match."""
        enrichment = {
            "timestamp": datetime.now().isoformat(),
            "home_team": home_team,
            "away_team": away_team,
            "competition": competition,
        }

        # 1. Get bookmaker odds
        try:
            odds_data = await self.odds_client.get_odds(competition)
            enrichment["odds"] = self.odds_client.extract_best_odds(
                odds_data, home_team, away_team
            )
        except Exception as e:
            logger.error(f"Error getting odds: {e}")
            enrichment["odds"] = {"available": False}

        # 2. Get weather
        try:
            enrichment["weather"] = await self.weather_client.get_match_weather(
                home_team, match_date
            )
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            enrichment["weather"] = {"available": False}

        # 3. Calculate form
        if home_recent_matches:
            enrichment["home_form"] = self.form_calculator.calculate_form(
                home_recent_matches, home_team
            )
        if away_recent_matches:
            enrichment["away_form"] = self.form_calculator.calculate_form(
                away_recent_matches, away_team
            )

        # 4. H2H analysis
        if h2h_matches:
            enrichment["h2h"] = self._analyze_h2h(h2h_matches, home_team, away_team)

        # 5. Standings context
        if standings:
            enrichment["standings"] = self._extract_standings_context(
                standings, home_team, away_team
            )

        # 6. xG approximation
        if enrichment.get("home_form") and enrichment.get("away_form"):
            home_form = enrichment["home_form"]
            away_form = enrichment["away_form"]

            enrichment["home_xg_estimate"] = self.xg_approximator.estimate_team_xg(
                home_form["goals_scored"] / max(1, len(home_form["last_5"])),
                home_form["goals_conceded"] / max(1, len(home_form["last_5"])),
                home_form["form_rating"],
                is_home=True,
            )
            enrichment["away_xg_estimate"] = self.xg_approximator.estimate_team_xg(
                away_form["goals_scored"] / max(1, len(away_form["last_5"])),
                away_form["goals_conceded"] / max(1, len(away_form["last_5"])),
                away_form["form_rating"],
                is_home=False,
            )

        return enrichment

    def _analyze_h2h(
        self,
        matches: list[dict],
        home_team: str,
        away_team: str
    ) -> dict:
        """Analyze head-to-head history."""
        h2h = {
            "total_matches": len(matches),
            "home_wins": 0,
            "away_wins": 0,
            "draws": 0,
            "home_goals": 0,
            "away_goals": 0,
            "recent_results": [],
        }

        for match in matches[:10]:
            score = match.get("score", {})
            if not score or not score.get("fullTime"):
                continue

            home_goals = score["fullTime"].get("home", 0) or 0
            away_goals = score["fullTime"].get("away", 0) or 0
            match_home = match.get("homeTeam", {}).get("name", "")

            # Determine if our "home_team" was actually home in this match
            if home_team.lower() in match_home.lower():
                h2h["home_goals"] += home_goals
                h2h["away_goals"] += away_goals
                if home_goals > away_goals:
                    h2h["home_wins"] += 1
                    h2h["recent_results"].append(f"W {home_goals}-{away_goals}")
                elif home_goals < away_goals:
                    h2h["away_wins"] += 1
                    h2h["recent_results"].append(f"L {home_goals}-{away_goals}")
                else:
                    h2h["draws"] += 1
                    h2h["recent_results"].append(f"D {home_goals}-{away_goals}")
            else:
                # Teams were swapped
                h2h["home_goals"] += away_goals
                h2h["away_goals"] += home_goals
                if away_goals > home_goals:
                    h2h["home_wins"] += 1
                    h2h["recent_results"].append(f"W {away_goals}-{home_goals}")
                elif away_goals < home_goals:
                    h2h["away_wins"] += 1
                    h2h["recent_results"].append(f"L {away_goals}-{home_goals}")
                else:
                    h2h["draws"] += 1
                    h2h["recent_results"].append(f"D {away_goals}-{home_goals}")

        h2h["recent_results"] = h2h["recent_results"][:5]
        return h2h

    def _extract_standings_context(
        self,
        standings: list[dict],
        home_team: str,
        away_team: str,
    ) -> dict:
        """Extract standings context for both teams."""
        context = {
            "home_position": None,
            "away_position": None,
            "home_points": None,
            "away_points": None,
            "position_diff": None,
            "context_note": "",
        }

        for team in standings:
            team_name = team.get("team", {}).get("name", "")
            if home_team.lower() in team_name.lower() or team_name.lower() in home_team.lower():
                context["home_position"] = team.get("position")
                context["home_points"] = team.get("points")
            if away_team.lower() in team_name.lower() or team_name.lower() in away_team.lower():
                context["away_position"] = team.get("position")
                context["away_points"] = team.get("points")

        if context["home_position"] and context["away_position"]:
            context["position_diff"] = context["away_position"] - context["home_position"]

            # Generate context note
            if context["home_position"] <= 4 and context["away_position"] <= 4:
                context["context_note"] = "Top 4 clash"
            elif context["home_position"] <= 4 or context["away_position"] <= 4:
                context["context_note"] = "European spot battle"
            elif context["home_position"] >= 17 or context["away_position"] >= 17:
                context["context_note"] = "Relegation battle"

        return context


# Singleton instance
_data_enrichment: DataEnrichmentService | None = None


def get_data_enrichment() -> DataEnrichmentService:
    """Get data enrichment service singleton."""
    global _data_enrichment
    if _data_enrichment is None:
        _data_enrichment = DataEnrichmentService()
    return _data_enrichment
