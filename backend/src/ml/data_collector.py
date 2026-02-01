"""Historical match data collector for ML training.

Collects historical match data from football-data.org API for training
XGBoost and Random Forest models.

Free tier: 10 requests/minute, 5 major leagues supported.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
import os

logger = logging.getLogger(__name__)

# Football-data.org configuration
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Supported competitions (free tier)
COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}

# Data storage path
DATA_DIR = Path(__file__).parent / "data"
HISTORICAL_DATA_FILE = DATA_DIR / "historical_matches.json"
TEAM_STATS_FILE = DATA_DIR / "team_stats.json"


class HistoricalDataCollector:
    """Collects and processes historical match data for ML training."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize collector with optional API key.

        Args:
            api_key: football-data.org API key (optional but recommended)
        """
        self.api_key = api_key or os.getenv("FOOTBALL_DATA_API_KEY", "")
        self.headers = {"X-Auth-Token": self.api_key} if self.api_key else {}
        self.rate_limit_delay = 6.5  # seconds between requests (10 req/min limit)

        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    async def fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """Fetch URL with retry logic and rate limiting."""
        for attempt in range(max_retries):
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        logger.warning(f"Rate limited, waiting 60s...")
                        await asyncio.sleep(60)
                    else:
                        logger.error(f"HTTP {response.status} for {url}")
                        return None
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(5)
        return None

    async def collect_season_matches(
        self,
        session: aiohttp.ClientSession,
        competition: str,
        season: int
    ) -> List[Dict]:
        """
        Collect all matches for a specific competition and season.

        Args:
            session: aiohttp session
            competition: Competition code (e.g., 'PL', 'PD')
            season: Season year (e.g., 2023 for 2023-24 season)

        Returns:
            List of match dictionaries
        """
        url = f"{FOOTBALL_DATA_BASE_URL}/competitions/{competition}/matches?season={season}"

        logger.info(f"Fetching {COMPETITIONS.get(competition, competition)} {season}/{season+1}...")

        data = await self.fetch_with_retry(session, url)
        if not data or "matches" not in data:
            logger.warning(f"No data for {competition} {season}")
            return []

        matches = []
        for match in data["matches"]:
            if match.get("status") != "FINISHED":
                continue

            processed = {
                "id": match["id"],
                "competition": competition,
                "season": season,
                "matchday": match.get("matchday"),
                "date": match["utcDate"],
                "home_team": {
                    "id": match["homeTeam"]["id"],
                    "name": match["homeTeam"]["name"],
                },
                "away_team": {
                    "id": match["awayTeam"]["id"],
                    "name": match["awayTeam"]["name"],
                },
                "score": {
                    "home": match["score"]["fullTime"]["home"],
                    "away": match["score"]["fullTime"]["away"],
                },
                "result": self._determine_result(
                    match["score"]["fullTime"]["home"],
                    match["score"]["fullTime"]["away"]
                ),
            }
            matches.append(processed)

        logger.info(f"  -> {len(matches)} finished matches")
        await asyncio.sleep(self.rate_limit_delay)  # Rate limiting
        return matches

    def _determine_result(self, home_goals: int, away_goals: int) -> int:
        """
        Determine match result as classification label.

        Returns:
            0 = Home Win, 1 = Draw, 2 = Away Win
        """
        if home_goals > away_goals:
            return 0  # Home Win
        elif home_goals == away_goals:
            return 1  # Draw
        else:
            return 2  # Away Win

    async def collect_team_stats(
        self,
        session: aiohttp.ClientSession,
        competition: str
    ) -> Dict[int, Dict]:
        """
        Collect current team statistics for a competition.

        Args:
            session: aiohttp session
            competition: Competition code

        Returns:
            Dictionary mapping team_id to stats
        """
        url = f"{FOOTBALL_DATA_BASE_URL}/competitions/{competition}/standings"

        data = await self.fetch_with_retry(session, url)
        if not data or "standings" not in data:
            return {}

        team_stats = {}
        for standing in data["standings"]:
            if standing["type"] != "TOTAL":
                continue
            for entry in standing["table"]:
                team_id = entry["team"]["id"]
                played = entry["playedGames"] or 1
                team_stats[team_id] = {
                    "name": entry["team"]["name"],
                    "position": entry["position"],
                    "played": played,
                    "won": entry["won"],
                    "draw": entry["draw"],
                    "lost": entry["lost"],
                    "goals_for": entry["goalsFor"],
                    "goals_against": entry["goalsAgainst"],
                    "goal_difference": entry["goalDifference"],
                    "points": entry["points"],
                    # Calculated stats
                    "attack_strength": entry["goalsFor"] / played,
                    "defense_strength": entry["goalsAgainst"] / played,
                    "win_rate": entry["won"] / played,
                    "form_points": entry["points"] / played,
                }

        await asyncio.sleep(self.rate_limit_delay)
        return team_stats

    async def collect_all_historical_data(
        self,
        seasons: Optional[List[int]] = None,
        competitions: Optional[List[str]] = None
    ) -> Dict:
        """
        Collect historical data for multiple seasons and competitions.

        Args:
            seasons: List of season years (default: last 3 seasons)
            competitions: List of competition codes (default: all free tier)

        Returns:
            Dictionary with all collected data
        """
        if seasons is None:
            current_year = datetime.now().year
            # Get last 3 completed seasons
            seasons = [current_year - 3, current_year - 2, current_year - 1]

        if competitions is None:
            competitions = list(COMPETITIONS.keys())

        all_matches = []
        all_team_stats = {}

        async with aiohttp.ClientSession() as session:
            # Collect matches for each competition and season
            for competition in competitions:
                for season in seasons:
                    matches = await self.collect_season_matches(
                        session, competition, season
                    )
                    all_matches.extend(matches)

            # Collect current team stats
            logger.info("Collecting current team statistics...")
            for competition in competitions:
                stats = await self.collect_team_stats(session, competition)
                all_team_stats[competition] = stats

        result = {
            "collected_at": datetime.now().isoformat(),
            "seasons": seasons,
            "competitions": competitions,
            "total_matches": len(all_matches),
            "matches": all_matches,
            "team_stats": all_team_stats,
        }

        # Save to file
        self._save_data(result)

        logger.info(f"Collection complete: {len(all_matches)} matches from {len(seasons)} seasons")
        return result

    def _save_data(self, data: Dict) -> None:
        """Save collected data to JSON file."""
        with open(HISTORICAL_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {HISTORICAL_DATA_FILE}")

    def load_data(self) -> Optional[Dict]:
        """Load previously collected data."""
        if HISTORICAL_DATA_FILE.exists():
            with open(HISTORICAL_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_data_age_days(self) -> Optional[int]:
        """Get age of collected data in days."""
        data = self.load_data()
        if data and "collected_at" in data:
            collected = datetime.fromisoformat(data["collected_at"])
            return (datetime.now() - collected).days
        return None


async def collect_data_cli():
    """Command-line interface for data collection."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect historical football data")
    parser.add_argument("--seasons", type=int, nargs="+", help="Seasons to collect (e.g., 2022 2023)")
    parser.add_argument("--competitions", nargs="+", help="Competitions (e.g., PL PD)")
    parser.add_argument("--api-key", help="football-data.org API key")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    collector = HistoricalDataCollector(api_key=args.api_key)
    await collector.collect_all_historical_data(
        seasons=args.seasons,
        competitions=args.competitions
    )


if __name__ == "__main__":
    asyncio.run(collect_data_cli())
