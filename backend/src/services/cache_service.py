"""Cache service for pre-calculating and storing stats.

This service runs daily at 6am to pre-calculate:
- Prediction statistics
- League standings for all competitions
- Teams data
- Upcoming matches

The cached data is stored in PostgreSQL/Supabase and served from there
instead of calculating in real-time on each API request.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from src.data.database import adapt_query, fetch_all_dict, fetch_one_dict, get_db_connection
from src.data.sources.football_data import COMPETITIONS, get_football_data_client

logger = logging.getLogger(__name__)

# Cache expiration: 24 hours (next calculation at 6am)
CACHE_TTL_HOURS = 24


def init_cache_table() -> None:
    """Create cached_data table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create table (PostgreSQL syntax, but works with SQLite too)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_data (
            id SERIAL PRIMARY KEY,
            cache_key VARCHAR(100) UNIQUE NOT NULL,
            cache_type VARCHAR(50) NOT NULL,
            data TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on cache_key if not exists
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_data_key ON cached_data (cache_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_data_expires ON cached_data (expires_at)")
    except Exception:
        pass  # Index might already exist

    conn.commit()
    conn.close()
    logger.info("Cache table initialized")


def get_cached_data(cache_key: str) -> dict[str, Any] | None:
    """Get cached data by key if not expired."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = adapt_query("""
        SELECT data FROM cached_data
        WHERE cache_key = ? AND expires_at > ?
    """)
    cursor.execute(query, (cache_key, datetime.utcnow()))
    result = fetch_one_dict(cursor)
    conn.close()

    if result:
        return json.loads(result.get("data", "{}"))
    return None


def set_cached_data(
    cache_key: str,
    cache_type: str,
    data: dict[str, Any],
    ttl_hours: int = CACHE_TTL_HOURS,
) -> None:
    """Store data in cache with expiration."""
    conn = get_db_connection()
    cursor = conn.cursor()

    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    json_data = json.dumps(data, default=str)
    now = datetime.utcnow()

    # Delete existing entry if any
    delete_query = adapt_query("DELETE FROM cached_data WHERE cache_key = ?")
    cursor.execute(delete_query, (cache_key,))

    # Insert new entry
    insert_query = adapt_query("""
        INSERT INTO cached_data (cache_key, cache_type, data, expires_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """)
    cursor.execute(insert_query, (cache_key, cache_type, json_data, expires_at, now, now))

    conn.commit()
    conn.close()
    logger.info(f"Cached {cache_key} until {expires_at}")


async def calculate_prediction_stats() -> dict[str, Any]:
    """Calculate prediction statistics."""
    from src.data.database import get_all_predictions_stats, get_prediction_statistics

    logger.info("Calculating prediction stats...")

    # Get stats for last 30 days (default)
    stats = get_prediction_statistics(30)

    # If no verified predictions, use unverified stats
    if stats["total_predictions"] == 0:
        stats = get_all_predictions_stats(30)

    return {
        "total_predictions": stats.get("total_predictions", 0),
        "verified_predictions": stats.get("verified_predictions", 0),
        "correct_predictions": stats.get("correct_predictions", 0),
        "accuracy": stats.get("accuracy", 0.0),
        "roi_simulated": stats.get("roi_simulated", 0.0),
        "by_competition": stats.get("by_competition", {}),
        "by_bet_type": stats.get("by_bet_type", {}),
        "calculated_at": datetime.utcnow().isoformat(),
    }


async def calculate_standings(competition_code: str) -> dict[str, Any] | None:
    """Calculate standings for a competition."""
    logger.info(f"Calculating standings for {competition_code}...")

    try:
        client = get_football_data_client()
        api_standings = await client.get_standings(competition_code)

        standings = []
        for team in api_standings:
            standings.append(
                {
                    "position": team.position,
                    "team_id": team.team.id,
                    "team_name": team.team.name,
                    "team_logo_url": team.team.crest,
                    "played": team.playedGames,
                    "won": team.won,
                    "drawn": team.draw,
                    "lost": team.lost,
                    "goals_for": team.goalsFor,
                    "goals_against": team.goalsAgainst,
                    "goal_difference": team.goalDifference,
                    "points": team.points,
                }
            )

        return {
            "competition_code": competition_code,
            "competition_name": COMPETITIONS.get(competition_code, competition_code),
            "standings": standings,
            "calculated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to calculate standings for {competition_code}: {e}")
        return None


async def calculate_upcoming_matches() -> dict[str, Any]:
    """Calculate upcoming matches for next 7 days."""
    from src.data.database import fetch_all_dict, get_db_connection, adapt_query

    logger.info("Calculating upcoming matches...")

    # Get matches for next 7 days from database
    conn = get_db_connection()
    cursor = conn.cursor()

    query = adapt_query("""
        SELECT
            m.id, m.external_id, m.match_date, m.status,
            ht.name as home_team, ht.logo_url as home_logo,
            at.name as away_team, at.logo_url as away_logo,
            c.name as competition, c.code as competition_code
        FROM matches m
        LEFT JOIN teams ht ON m.home_team_id = ht.id
        LEFT JOIN teams at ON m.away_team_id = at.id
        LEFT JOIN competitions c ON m.competition_id = c.id
        WHERE m.match_date >= ? AND m.match_date <= ?
        AND m.status IN ('scheduled', 'SCHEDULED', 'TIMED')
        ORDER BY m.match_date ASC
    """)

    now = datetime.utcnow()
    end_date = now + timedelta(days=7)
    cursor.execute(query, (now, end_date))
    matches = fetch_all_dict(cursor)
    conn.close()

    return {
        "matches": [
            {
                "id": m.get("id"),
                "external_id": m.get("external_id"),
                "home_team": m.get("home_team", "Unknown"),
                "away_team": m.get("away_team", "Unknown"),
                "home_logo": m.get("home_logo"),
                "away_logo": m.get("away_logo"),
                "competition": m.get("competition", "Unknown"),
                "competition_code": m.get("competition_code"),
                "match_date": m.get("match_date").isoformat() if m.get("match_date") else None,
                "status": m.get("status"),
            }
            for m in matches
        ],
        "total": len(matches),
        "calculated_at": datetime.utcnow().isoformat(),
    }


async def calculate_teams() -> dict[str, Any]:
    """Calculate teams data with stats."""
    from src.data.database import fetch_all_dict, get_db_connection, adapt_query

    logger.info("Calculating teams data...")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = adapt_query("""
        SELECT
            id, external_id, name, short_name, tla, country, logo_url,
            elo_rating, avg_goals_scored_home, avg_goals_scored_away,
            avg_goals_conceded_home, avg_goals_conceded_away
        FROM teams
        ORDER BY name ASC
    """)
    cursor.execute(query)
    teams = fetch_all_dict(cursor)
    conn.close()

    teams_data = [
        {
            "id": t.get("id"),
            "external_id": t.get("external_id"),
            "name": t.get("name"),
            "short_name": t.get("short_name"),
            "tla": t.get("tla"),
            "country": t.get("country"),
            "logo_url": t.get("logo_url"),
            "elo_rating": float(t.get("elo_rating")) if t.get("elo_rating") else 1500.0,
            "avg_goals_scored_home": float(t.get("avg_goals_scored_home")) if t.get("avg_goals_scored_home") else None,
            "avg_goals_scored_away": float(t.get("avg_goals_scored_away")) if t.get("avg_goals_scored_away") else None,
            "avg_goals_conceded_home": float(t.get("avg_goals_conceded_home")) if t.get("avg_goals_conceded_home") else None,
            "avg_goals_conceded_away": float(t.get("avg_goals_conceded_away")) if t.get("avg_goals_conceded_away") else None,
        }
        for t in teams
    ]

    return {
        "teams": teams_data,
        "total": len(teams_data),
        "calculated_at": datetime.utcnow().isoformat(),
    }


async def calculate_predictions_for_upcoming_matches() -> dict[str, Any]:
    """Pre-calculate predictions for all upcoming matches using ML + LLM.

    This runs the full prediction pipeline:
    1. Fetch upcoming matches (next 7 days)
    2. Run ML ensemble models (Poisson, ELO, XGBoost, etc.)
    3. Run LLM analysis for context adjustments (Groq)
    4. Store complete predictions in database
    """
    import asyncio
    from src.data.database import adapt_query, fetch_all_dict, get_db_connection

    logger.info("Pre-calculating predictions for upcoming matches...")

    # Get upcoming matches that don't have predictions yet
    conn = get_db_connection()
    cursor = conn.cursor()

    query = adapt_query("""
        SELECT m.id, m.external_id
        FROM matches m
        LEFT JOIN predictions p ON m.id = p.match_id
        WHERE m.match_date >= ?
        AND m.match_date <= ?
        AND m.status IN ('scheduled', 'SCHEDULED', 'TIMED')
        AND p.id IS NULL
        ORDER BY m.match_date ASC
        LIMIT 50
    """)

    now = datetime.utcnow()
    end_date = now + timedelta(days=7)
    cursor.execute(query, (now, end_date))
    matches = fetch_all_dict(cursor)
    conn.close()

    if not matches:
        logger.info("No new matches to predict")
        return {"predicted": 0, "failed": 0, "matches": []}

    logger.info(f"Found {len(matches)} matches to predict")

    predicted = 0
    failed = 0
    predicted_matches = []

    # Import prediction function
    try:
        from src.api.routes.predictions import _generate_prediction_from_api_match
        from src.data.sources.football_data import get_football_data_client
    except ImportError as e:
        logger.error(f"Failed to import prediction modules: {e}")
        return {"predicted": 0, "failed": len(matches), "error": str(e)}

    client = get_football_data_client()

    for match in matches:
        match_id = match.get("id")
        external_id = match.get("external_id")

        try:
            logger.info(f"Calculating prediction for match {match_id} (external: {external_id})")

            # Fetch match details from API
            api_match = await client.get_match(int(external_id))

            if api_match:
                # Generate full prediction with ML + LLM
                prediction = await _generate_prediction_from_api_match(
                    api_match=api_match,
                    include_model_details=True,
                    use_rag=True,  # Enable LLM analysis
                )

                if prediction:
                    predicted += 1
                    predicted_matches.append({
                        "match_id": match_id,
                        "external_id": external_id,
                        "home_prob": prediction.probabilities.home_win,
                        "away_prob": prediction.probabilities.away_win,
                        "recommended": prediction.recommended_bet,
                    })
                    logger.info(f"Prediction saved for match {match_id}")
                else:
                    failed += 1
                    logger.warning(f"No prediction generated for match {match_id}")
            else:
                failed += 1
                logger.warning(f"Could not fetch match {external_id} from API")

            # Rate limit protection (Groq: 30 req/min, football-data: 10 req/min)
            await asyncio.sleep(6)

        except Exception as e:
            failed += 1
            logger.error(f"Failed to predict match {match_id}: {e}")
            await asyncio.sleep(2)

    logger.info(f"Prediction calculation complete: {predicted} success, {failed} failed")

    return {
        "predicted": predicted,
        "failed": failed,
        "matches": predicted_matches,
        "calculated_at": datetime.utcnow().isoformat(),
    }


async def run_daily_cache_calculation() -> dict[str, Any]:
    """Run all cache calculations. Called daily at 6am."""
    import asyncio

    logger.info("Starting daily cache calculation...")
    results = {"success": [], "failed": []}

    # 1. Prediction stats
    try:
        stats = await calculate_prediction_stats()
        set_cached_data("prediction_stats_30d", "prediction_stats", stats)
        results["success"].append("prediction_stats")
    except Exception as e:
        logger.error(f"Failed to calculate prediction stats: {e}")
        results["failed"].append(f"prediction_stats: {e}")

    # 2. Standings for all competitions (with delay to avoid rate limits)
    for code in COMPETITIONS.keys():
        try:
            standings = await calculate_standings(code)
            if standings:
                set_cached_data(f"standings_{code}", "standings", standings)
                results["success"].append(f"standings_{code}")
            await asyncio.sleep(1)  # Rate limit protection
        except Exception as e:
            logger.error(f"Failed to calculate standings for {code}: {e}")
            results["failed"].append(f"standings_{code}: {e}")

    # 3. Teams data
    try:
        teams = await calculate_teams()
        set_cached_data("teams_all", "teams", teams)
        results["success"].append("teams")
    except Exception as e:
        logger.error(f"Failed to calculate teams: {e}")
        results["failed"].append(f"teams: {e}")

    # 4. Upcoming matches
    try:
        matches = await calculate_upcoming_matches()
        set_cached_data("upcoming_matches_7d", "upcoming_matches", matches)
        results["success"].append("upcoming_matches")
    except Exception as e:
        logger.error(f"Failed to calculate upcoming matches: {e}")
        results["failed"].append(f"upcoming_matches: {e}")

    # 5. Pre-calculate predictions with ML + LLM for upcoming matches
    try:
        predictions_result = await calculate_predictions_for_upcoming_matches()
        predicted = predictions_result.get("predicted", 0)
        failed = predictions_result.get("failed", 0)
        if predicted > 0:
            results["success"].append(f"predictions ({predicted} matches)")
        if failed > 0:
            results["failed"].append(f"predictions ({failed} failed)")
        logger.info(f"Predictions: {predicted} calculated, {failed} failed")
    except Exception as e:
        logger.error(f"Failed to calculate predictions: {e}")
        results["failed"].append(f"predictions: {e}")

    logger.info(
        f"Daily cache calculation complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}"
    )

    return results
