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
from datetime import UTC, datetime, timedelta
from typing import Any

from src.data.sources.football_data import COMPETITIONS, get_football_data_client
from src.db.repositories import get_uow
from src.db.services import MatchService, PredictionService

logger = logging.getLogger(__name__)

# Cache expiration: 24 hours (next calculation at 6am)
CACHE_TTL_HOURS = 24


async def init_cache_table() -> None:
    """Initialize cache table - now handled by SQLAlchemy migrations."""
    logger.info("Cache table is managed by SQLAlchemy migrations")


async def get_cached_data(cache_key: str) -> dict[str, Any] | None:
    """Get cached data by key if not expired."""
    async with get_uow() as uow:
        from sqlalchemy import select

        from src.db.models import CachedData

        stmt = select(CachedData).where(
            CachedData.cache_key == cache_key,
            CachedData.expires_at > datetime.now(UTC),
        )
        result = await uow._session.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached and cached.data:
            return json.loads(cached.data)
        return None


async def set_cached_data(
    cache_key: str,
    cache_type: str,
    data: dict[str, Any],
    ttl_hours: int = CACHE_TTL_HOURS,
) -> None:
    """Store data in cache with expiration."""
    async with get_uow() as uow:
        from sqlalchemy import delete

        from src.db.models import CachedData

        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        json_data = json.dumps(data, default=str)
        now = datetime.now(UTC)

        # Delete existing entry if any
        del_stmt = delete(CachedData).where(CachedData.cache_key == cache_key)
        await uow._session.execute(del_stmt)

        # Insert new entry
        cached = CachedData(
            cache_key=cache_key,
            cache_type=cache_type,
            data=json_data,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        uow._session.add(cached)
        await uow.commit()

    logger.info(f"Cached {cache_key} until {expires_at}")


async def calculate_prediction_stats() -> dict[str, Any]:
    """Calculate prediction statistics using async service."""
    logger.info("Calculating prediction stats...")

    # Get stats for last 30 days (default)
    stats = await PredictionService.get_statistics(30)

    return {
        "total_predictions": stats.get("total_predictions", 0),
        "verified_predictions": stats.get("verified_predictions", 0),
        "correct_predictions": stats.get("correct_predictions", 0),
        "accuracy": stats.get("accuracy", 0.0),
        "roi_simulated": stats.get("roi_simulated", 0.0),
        "by_competition": stats.get("by_competition", {}),
        "by_bet_type": stats.get("by_bet_type", {}),
        "calculated_at": datetime.now(UTC).isoformat(),
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
            "calculated_at": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to calculate standings for {competition_code}: {e}")
        return None


async def calculate_upcoming_matches() -> dict[str, Any]:
    """Calculate upcoming matches for next 7 days using async service."""
    from datetime import date

    logger.info("Calculating upcoming matches...")

    # Get matches for next 7 days from database
    now = date.today()
    end_date = now + timedelta(days=7)

    db_matches = await MatchService.get_scheduled(
        date_from=now,
        date_to=end_date,
    )

    # Enrich matches with team names via UoW
    async with get_uow() as uow:
        enriched_matches = []
        for m in db_matches:
            home_team = await uow.teams.get_by_id(m.get("home_team_id"))
            away_team = await uow.teams.get_by_id(m.get("away_team_id"))

            enriched_matches.append(
                {
                    "id": m.get("id"),
                    "external_id": m.get("external_id"),
                    "home_team": home_team.name if home_team else "Unknown",
                    "away_team": away_team.name if away_team else "Unknown",
                    "home_logo": home_team.logo_url if home_team else None,
                    "away_logo": away_team.logo_url if away_team else None,
                    "competition": "Unknown",  # Would need competition lookup
                    "competition_code": None,
                    "match_date": m.get("match_date"),
                    "status": m.get("status"),
                }
            )

    return {
        "matches": enriched_matches,
        "total": len(enriched_matches),
        "calculated_at": datetime.now(UTC).isoformat(),
    }


async def calculate_teams() -> dict[str, Any]:
    """Calculate teams data with stats using async repository."""
    logger.info("Calculating teams data...")

    async with get_uow() as uow:
        teams = await uow.teams.get_all(limit=1000)

        teams_data = [
            {
                "id": t.id,
                "external_id": t.external_id,
                "name": t.name,
                "short_name": t.short_name,
                "tla": t.tla,
                "country": t.country,
                "logo_url": t.logo_url,
                "elo_rating": float(t.elo_rating) if t.elo_rating else 1500.0,
                "avg_goals_scored_home": (
                    float(t.avg_goals_scored_home) if t.avg_goals_scored_home else None
                ),
                "avg_goals_scored_away": (
                    float(t.avg_goals_scored_away) if t.avg_goals_scored_away else None
                ),
                "avg_goals_conceded_home": (
                    float(t.avg_goals_conceded_home) if t.avg_goals_conceded_home else None
                ),
                "avg_goals_conceded_away": (
                    float(t.avg_goals_conceded_away) if t.avg_goals_conceded_away else None
                ),
            }
            for t in teams
        ]

    return {
        "teams": teams_data,
        "total": len(teams_data),
        "calculated_at": datetime.now(UTC).isoformat(),
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

    logger.info("Pre-calculating predictions for upcoming matches...")

    # Get upcoming matches that don't have predictions yet

    async with get_uow() as uow:
        # Get scheduled matches
        from sqlalchemy import select

        from src.db.models import Match, Prediction

        stmt = (
            select(Match)
            .outerjoin(Prediction, Match.id == Prediction.match_id)
            .where(
                Match.match_date >= datetime.now(UTC),
                Match.match_date <= datetime.now(UTC) + timedelta(days=7),
                Match.status.in_(["scheduled", "SCHEDULED", "TIMED"]),
                Prediction.id.is_(None),
            )
            .order_by(Match.match_date)
            .limit(50)
        )
        result = await uow._session.execute(stmt)
        matches = result.scalars().all()

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
    except ImportError as e:
        logger.error(f"Failed to import prediction modules: {e}")
        return {"predicted": 0, "failed": len(matches), "error": str(e)}

    client = get_football_data_client()

    for match in matches:
        match_id = match.id
        external_id = match.external_id

        try:
            logger.info(f"Calculating prediction for match {match_id} (external: {external_id})")

            # Extract the numeric part from external_id (e.g., "PL_12345" -> 12345)
            numeric_id = external_id.split("_")[-1] if external_id else str(match_id)

            # Fetch match details from API
            api_match = await client.get_match(int(numeric_id))

            if api_match:
                # Generate full prediction with ML + LLM
                prediction = await _generate_prediction_from_api_match(
                    api_match=api_match,
                    include_model_details=True,
                    use_rag=True,  # Enable LLM analysis
                )

                if prediction:
                    predicted += 1
                    predicted_matches.append(
                        {
                            "match_id": match_id,
                            "external_id": external_id,
                            "home_prob": prediction.probabilities.home_win,
                            "away_prob": prediction.probabilities.away_win,
                            "recommended": prediction.recommended_bet,
                        }
                    )
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
        "calculated_at": datetime.now(UTC).isoformat(),
    }


async def run_daily_cache_calculation() -> dict[str, Any]:
    """Run all cache calculations. Called daily at 6am."""
    import asyncio

    logger.info("Starting daily cache calculation...")
    results: dict[str, list[str]] = {"success": [], "failed": []}

    # 1. Prediction stats
    try:
        stats = await calculate_prediction_stats()
        await set_cached_data("prediction_stats_30d", "prediction_stats", stats)
        results["success"].append("prediction_stats")
    except Exception as e:
        logger.error(f"Failed to calculate prediction stats: {e}")
        results["failed"].append(f"prediction_stats: {e}")

    # 2. Standings for all competitions (with delay to avoid rate limits)
    for code in COMPETITIONS.keys():
        try:
            standings = await calculate_standings(code)
            if standings:
                await set_cached_data(f"standings_{code}", "standings", standings)
                results["success"].append(f"standings_{code}")
            await asyncio.sleep(1)  # Rate limit protection
        except Exception as e:
            logger.error(f"Failed to calculate standings for {code}: {e}")
            results["failed"].append(f"standings_{code}: {e}")

    # 3. Teams data
    try:
        teams = await calculate_teams()
        await set_cached_data("teams_all", "teams", teams)
        results["success"].append("teams")
    except Exception as e:
        logger.error(f"Failed to calculate teams: {e}")
        results["failed"].append(f"teams: {e}")

    # 4. Upcoming matches
    try:
        matches = await calculate_upcoming_matches()
        await set_cached_data("upcoming_matches_7d", "upcoming_matches", matches)
        results["success"].append("upcoming_matches")
    except Exception as e:
        logger.error(f"Failed to calculate upcoming matches: {e}")
        results["failed"].append(f"upcoming_matches: {e}")

    # 5. Pre-calculate predictions with ML + LLM for upcoming matches
    try:
        predictions_result = await calculate_predictions_for_upcoming_matches()
        predicted = predictions_result.get("predicted", 0)
        failed_count = predictions_result.get("failed", 0)
        if predicted > 0:
            results["success"].append(f"predictions ({predicted} matches)")
        if failed_count > 0:
            results["failed"].append(f"predictions ({failed_count} failed)")
        logger.info(f"Predictions: {predicted} calculated, {failed_count} failed")
    except Exception as e:
        logger.error(f"Failed to calculate predictions: {e}")
        results["failed"].append(f"predictions: {e}")

    logger.info(
        f"Daily cache calculation complete. Success: {len(results['success'])}, Failed: {len(results['failed'])}"
    )

    return results
