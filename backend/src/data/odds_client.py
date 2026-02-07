"""Client for The Odds API - fetches real bookmaker odds for match value detection.

Free tier: 500 requests/month. Results are cached aggressively in Redis (1 hour per competition).
Docs: https://the-odds-api.com/liveapi/guides/v4/

Usage:
    from src.data.odds_client import get_match_odds

    odds = await get_match_odds("Arsenal", "Chelsea", "PL")
    # Returns {"home": 2.10, "draw": 3.40, "away": 3.50, "bookmaker": "Pinnacle"} or None
"""

import json
import logging
from difflib import SequenceMatcher
from typing import Any

from src.core.cache import cache_get, cache_set
from src.core.config import settings
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

# Map our competition codes to The Odds API sport keys
ODDS_API_SPORT_MAP: dict[str, str] = {
    # Football
    "PL": "soccer_epl",
    "PD": "soccer_spain_la_liga",
    "BL1": "soccer_germany_bundesliga",
    "SA": "soccer_italy_serie_a",
    "FL1": "soccer_france_ligue_one",
    "CL": "soccer_uefa_champs_league",
    # Basketball
    "NBA": "basketball_nba",
    # Tennis
    "ATP": "tennis_atp_french_open",
    "WTA": "tennis_wta_french_open",
}

BASE_URL = "https://api.the-odds-api.com/v4"

# Cache TTL: 1 hour (aggressive caching to stay within 500 req/month)
ODDS_CACHE_TTL = 3600

# Minimum similarity ratio for fuzzy team name matching
MIN_SIMILARITY = 0.55


def _normalize_team_name(name: str) -> str:
    """Normalize a team name for comparison.

    Strips common suffixes and lowercases for better matching between
    our database names and The Odds API names.
    """
    name = name.lower().strip()
    # Remove common suffixes that differ between sources
    for suffix in [" fc", " cf", " sc", " ac", " afc"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


def _team_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two team names.

    Uses both substring matching and SequenceMatcher for fuzzy comparison.
    Returns a score between 0.0 and 1.0.
    """
    n1 = _normalize_team_name(name1)
    n2 = _normalize_team_name(name2)

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    # Substring containment (e.g., "Arsenal" in "Arsenal FC")
    if n1 in n2 or n2 in n1:
        return 0.9

    # Fuzzy matching via SequenceMatcher
    return SequenceMatcher(None, n1, n2).ratio()


def _find_matching_game(
    odds_data: list[dict[str, Any]],
    home_team: str,
    away_team: str,
) -> dict[str, Any] | None:
    """Find the game in odds data that best matches the given team names.

    Uses fuzzy matching to handle name differences between our DB
    and The Odds API (e.g., "Wolverhampton" vs "Wolves").
    """
    best_match: dict[str, Any] | None = None
    best_score = 0.0

    for game in odds_data:
        api_home = game.get("home_team", "")
        api_away = game.get("away_team", "")

        home_score = _team_name_similarity(home_team, api_home)
        away_score = _team_name_similarity(away_team, api_away)

        # Both teams must match reasonably well
        combined = (home_score + away_score) / 2
        if home_score >= MIN_SIMILARITY and away_score >= MIN_SIMILARITY:
            if combined > best_score:
                best_score = combined
                best_match = game

    return best_match


def _extract_h2h_odds(game: dict[str, Any]) -> dict[str, Any] | None:
    """Extract 1X2 odds from the best bookmaker in the game data.

    Prefers bookmakers in order: Pinnacle, Bet365, Unibet, then first available.
    Returns {"home": float, "draw": float, "away": float, "bookmaker": str} or None.
    """
    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return None

    # Prefer well-known bookmakers with sharp lines
    preferred = ["Pinnacle", "Bet365", "Unibet", "1xBet", "Betfair"]
    selected_bm = None

    for pref_name in preferred:
        for bm in bookmakers:
            if bm.get("title", "").lower() == pref_name.lower():
                selected_bm = bm
                break
        if selected_bm:
            break

    # Fallback to first bookmaker
    if selected_bm is None:
        selected_bm = bookmakers[0]

    # Find h2h market
    for market in selected_bm.get("markets", []):
        if market.get("key") == "h2h":
            outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
            home_team_name = game.get("home_team", "")
            away_team_name = game.get("away_team", "")

            home_odds = outcomes.get(home_team_name)
            draw_odds = outcomes.get("Draw")
            away_odds = outcomes.get(away_team_name)

            if home_odds and draw_odds and away_odds:
                return {
                    "home": float(home_odds),
                    "draw": float(draw_odds),
                    "away": float(away_odds),
                    "bookmaker": selected_bm.get("title", "Unknown"),
                }

    return None


def _extract_h2h_binary_odds(game: dict[str, Any]) -> dict[str, Any] | None:
    """Extract binary (no draw) h2h odds from the best bookmaker.

    Used for NBA and Tennis where draws don't exist.
    Returns {"home": float, "away": float, "bookmaker": str} or None.
    """
    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return None

    preferred = ["Pinnacle", "Bet365", "Unibet", "1xBet", "Betfair"]
    selected_bm = None

    for pref_name in preferred:
        for bm in bookmakers:
            if bm.get("title", "").lower() == pref_name.lower():
                selected_bm = bm
                break
        if selected_bm:
            break

    if selected_bm is None:
        selected_bm = bookmakers[0]

    for market in selected_bm.get("markets", []):
        if market.get("key") == "h2h":
            outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
            home_name = game.get("home_team", "")
            away_name = game.get("away_team", "")

            home_odds = outcomes.get(home_name)
            away_odds = outcomes.get(away_name)

            if home_odds and away_odds:
                return {
                    "home": float(home_odds),
                    "away": float(away_odds),
                    "bookmaker": selected_bm.get("title", "Unknown"),
                }

    return None


async def get_binary_match_odds(
    home_name: str,
    away_name: str,
    sport_code: str,
) -> dict[str, Any] | None:
    """Get binary (no draw) h2h odds for NBA or Tennis matches.

    Args:
        home_name: Home team/player name.
        away_name: Away team/player name.
        sport_code: Sport code ("NBA", "ATP", "WTA").

    Returns:
        Dict with "home" and "away" decimal odds, or None.
    """
    if not settings.odds_api_key:
        return None

    if sport_code not in ODDS_API_SPORT_MAP:
        return None

    odds_data = await _fetch_competition_odds(sport_code)
    if not odds_data:
        return None

    game = _find_matching_game(odds_data, home_name, away_name)
    if not game:
        return None

    result = _extract_h2h_binary_odds(game)
    if result:
        logger.info(
            f"Odds for {home_name} vs {away_name}: "
            f"H={result['home']:.2f} A={result['away']:.2f} "
            f"({result['bookmaker']})"
        )
    return result


async def _fetch_competition_odds(competition_code: str) -> list[dict[str, Any]]:
    """Fetch odds for a competition from The Odds API, with Redis caching.

    Caches the full response per competition for 1 hour to minimize API calls.
    Free tier = 500 requests/month, so this is critical.
    """
    sport_key = ODDS_API_SPORT_MAP.get(competition_code)
    if not sport_key:
        logger.warning(f"No Odds API sport key for competition: {competition_code}")
        return []

    # Check Redis cache first
    cache_key = f"odds_api:{competition_code}"
    cached = await cache_get(cache_key)
    if cached is not None:
        try:
            data: list[dict[str, Any]] = json.loads(cached)
            logger.debug(f"Odds cache HIT for {competition_code} ({len(data)} games)")
            return data
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid odds cache data for {competition_code}")

    # Fetch from API
    api_key = settings.odds_api_key
    if not api_key:
        return []

    try:
        client = get_http_client()
        response = await client.get(
            f"{BASE_URL}/sports/{sport_key}/odds",
            params={
                "apiKey": api_key,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
            timeout=15.0,
        )

        if response.status_code == 200:
            data = response.json()
            logger.info(
                f"Fetched odds for {len(data)} games in {competition_code} "
                f"(remaining: {response.headers.get('x-requests-remaining', '?')})"
            )

            # Cache the response for 1 hour
            await cache_set(cache_key, json.dumps(data), ODDS_CACHE_TTL)
            return data

        elif response.status_code == 401:
            logger.error("Invalid ODDS_API_KEY - check your API key")
        elif response.status_code == 429:
            logger.warning("Odds API rate limit reached (500 req/month)")
        elif response.status_code == 422:
            logger.warning(
                f"Odds API: sport key '{sport_key}' not available "
                f"(competition {competition_code})"
            )
        else:
            logger.error(f"Odds API error: HTTP {response.status_code}")

    except Exception as e:
        logger.error(f"Error fetching odds from The Odds API: {e}")

    return []


async def get_match_odds(
    home_team: str,
    away_team: str,
    competition_code: str,
) -> dict[str, Any] | None:
    """Get bookmaker odds for a specific match.

    Fetches odds from The Odds API (cached per competition for 1 hour),
    finds the matching game by fuzzy team name comparison, and returns
    the best available 1X2 odds.

    Args:
        home_team: Home team name (e.g., "Arsenal").
        away_team: Away team name (e.g., "Chelsea").
        competition_code: Our competition code (e.g., "PL", "PD", "BL1").

    Returns:
        Dict with keys "home", "draw", "away" (decimal odds) and "bookmaker",
        or None if odds are unavailable.
    """
    # Check if API key is configured
    if not settings.odds_api_key:
        logger.debug("ODDS_API_KEY not configured - skipping odds fetch")
        return None

    # Check if competition is supported
    if competition_code not in ODDS_API_SPORT_MAP:
        logger.debug(f"Competition {competition_code} not supported by Odds API")
        return None

    # Fetch odds for the competition (cached)
    odds_data = await _fetch_competition_odds(competition_code)
    if not odds_data:
        return None

    # Find matching game by team names
    game = _find_matching_game(odds_data, home_team, away_team)
    if not game:
        logger.debug(
            f"No odds match found for {home_team} vs {away_team} " f"in {competition_code}"
        )
        return None

    # Extract 1X2 odds from best bookmaker
    result = _extract_h2h_odds(game)
    if result:
        logger.info(
            f"Odds for {home_team} vs {away_team}: "
            f"H={result['home']:.2f} D={result['draw']:.2f} A={result['away']:.2f} "
            f"({result['bookmaker']})"
        )
    return result
