"""Data prefill service for automatic data enrichment.

This service runs during sync to ensure all database fields are populated.
It handles:
- Team data: country, form, rest_days, fixture_congestion, xG
- Match data: half-time scores, xG, odds (when available)
- Predictions: pre-generate for upcoming matches
- Cache: pre-warm Redis and DB cache
- News: fetch and store from RSS feeds
- Sync logs: track all operations
"""

import asyncio
import hashlib
import json
import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.db import async_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_async_session():
    """Context manager for async database sessions."""
    async with async_session_factory() as session:
        yield session


async def log_sync_operation(
    sync_type: str,
    status: str,
    records_synced: int = 0,
    error_message: str | None = None,
    triggered_by: str = "startup",
) -> int:
    """Log a sync operation to the sync_log table."""
    async with get_async_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO sync_log (sync_type, status, records_synced, started_at, completed_at, error_message, triggered_by)
                VALUES (:sync_type, :status, :records_synced, NOW(), NOW(), :error_message, :triggered_by)
                RETURNING id
            """),
            {
                "sync_type": sync_type,
                "status": status,
                "records_synced": records_synced,
                "error_message": error_message,
                "triggered_by": triggered_by,
            }
        )
        await session.commit()
        row = result.fetchone()
        return row[0] if row else 0


class DataPrefillService:
    """Service for automatic data prefilling and enrichment."""

    @staticmethod
    async def fill_all_team_data() -> dict[str, int]:
        """Fill all team data fields. Returns counts of updated fields."""
        results = {
            "country": 0,
            "form": 0,
            "rest_days": 0,
            "avg_goals": 0,
            "elo": 0,
        }

        async with get_async_session() as session:
            # 1. Fill country from competition
            country_result = await session.execute(text("""
                WITH team_leagues AS (
                    SELECT team_id, competition_code, SUM(cnt) as total_matches
                    FROM (
                        SELECT home_team_id as team_id, competition_code, COUNT(*) as cnt
                        FROM matches WHERE competition_code IN ('PL', 'PD', 'BL1', 'SA', 'FL1')
                        GROUP BY home_team_id, competition_code
                        UNION ALL
                        SELECT away_team_id as team_id, competition_code, COUNT(*) as cnt
                        FROM matches WHERE competition_code IN ('PL', 'PD', 'BL1', 'SA', 'FL1')
                        GROUP BY away_team_id, competition_code
                    ) m
                    GROUP BY team_id, competition_code
                ),
                primary_league AS (
                    SELECT DISTINCT ON (team_id) team_id, competition_code
                    FROM team_leagues
                    ORDER BY team_id, total_matches DESC
                )
                UPDATE teams t
                SET country = CASE pl.competition_code
                    WHEN 'PL' THEN 'England'
                    WHEN 'PD' THEN 'Spain'
                    WHEN 'BL1' THEN 'Germany'
                    WHEN 'SA' THEN 'Italy'
                    WHEN 'FL1' THEN 'France'
                END,
                updated_at = NOW()
                FROM primary_league pl
                WHERE t.id = pl.team_id AND (t.country IS NULL OR t.country = '')
            """))
            results["country"] = country_result.rowcount
            await session.commit()

            # 2. Fill form from last 5 matches
            form_result = await session.execute(text("""
                WITH recent_matches AS (
                    SELECT
                        team_id,
                        match_date,
                        CASE
                            WHEN goals_for > goals_against THEN 'W'
                            WHEN goals_for = goals_against THEN 'D'
                            ELSE 'L'
                        END as result,
                        ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY match_date DESC) as rn
                    FROM (
                        SELECT home_team_id as team_id, match_date, home_score as goals_for, away_score as goals_against
                        FROM matches WHERE status = 'FINISHED' AND home_score IS NOT NULL
                        UNION ALL
                        SELECT away_team_id as team_id, match_date, away_score as goals_for, home_score as goals_against
                        FROM matches WHERE status = 'FINISHED' AND away_score IS NOT NULL
                    ) all_matches
                ),
                team_form AS (
                    SELECT team_id, STRING_AGG(result, '' ORDER BY match_date DESC) as form
                    FROM recent_matches
                    WHERE rn <= 5
                    GROUP BY team_id
                )
                UPDATE teams t
                SET
                    form = tf.form,
                    form_score = (
                        (LENGTH(tf.form) - LENGTH(REPLACE(tf.form, 'W', ''))) * 3 +
                        (LENGTH(tf.form) - LENGTH(REPLACE(tf.form, 'D', ''))) * 1
                    ) / 15.0,
                    updated_at = NOW()
                FROM team_form tf
                WHERE t.id = tf.team_id
            """))
            results["form"] = form_result.rowcount
            await session.commit()

            # 3. Fill rest_days and fixture_congestion
            rest_result = await session.execute(text("""
                WITH last_match AS (
                    SELECT team_id, MAX(match_date) as last_date
                    FROM (
                        SELECT home_team_id as team_id, match_date FROM matches WHERE status = 'FINISHED'
                        UNION ALL
                        SELECT away_team_id as team_id, match_date FROM matches WHERE status = 'FINISHED'
                    ) all_matches
                    GROUP BY team_id
                ),
                congestion AS (
                    SELECT team_id, COUNT(*) as matches_14d
                    FROM (
                        SELECT home_team_id as team_id FROM matches
                        WHERE status = 'FINISHED' AND match_date >= NOW() - INTERVAL '14 days'
                        UNION ALL
                        SELECT away_team_id as team_id FROM matches
                        WHERE status = 'FINISHED' AND match_date >= NOW() - INTERVAL '14 days'
                    ) recent
                    GROUP BY team_id
                )
                UPDATE teams t
                SET
                    last_match_date = lm.last_date,
                    rest_days = COALESCE(EXTRACT(DAY FROM NOW() - lm.last_date)::INTEGER, 7),
                    fixture_congestion = LEAST(1.0, COALESCE(c.matches_14d, 0) / 4.0),
                    updated_at = NOW()
                FROM last_match lm
                LEFT JOIN congestion c ON lm.team_id = c.team_id
                WHERE t.id = lm.team_id
            """))
            results["rest_days"] = rest_result.rowcount
            await session.commit()

            # 4. Fill avg_goals from match history
            goals_result = await session.execute(text("""
                WITH home_stats AS (
                    SELECT
                        home_team_id as team_id,
                        AVG(home_score) as avg_scored,
                        AVG(away_score) as avg_conceded
                    FROM matches
                    WHERE status = 'FINISHED' AND home_score IS NOT NULL
                    GROUP BY home_team_id
                ),
                away_stats AS (
                    SELECT
                        away_team_id as team_id,
                        AVG(away_score) as avg_scored,
                        AVG(home_score) as avg_conceded
                    FROM matches
                    WHERE status = 'FINISHED' AND away_score IS NOT NULL
                    GROUP BY away_team_id
                )
                UPDATE teams t
                SET
                    avg_goals_scored_home = COALESCE(h.avg_scored, 1.0),
                    avg_goals_conceded_home = COALESCE(h.avg_conceded, 1.0),
                    avg_goals_scored_away = COALESCE(a.avg_scored, 1.0),
                    avg_goals_conceded_away = COALESCE(a.avg_conceded, 1.0),
                    updated_at = NOW()
                FROM home_stats h
                FULL OUTER JOIN away_stats a ON h.team_id = a.team_id
                WHERE t.id = COALESCE(h.team_id, a.team_id)
            """))
            results["avg_goals"] = goals_result.rowcount
            await session.commit()

        logger.info(f"Team data prefill complete: {results}")
        return results

    @staticmethod
    async def calculate_elo_ratings() -> int:
        """Calculate proper ELO ratings from match history."""
        from src.prediction_engine.models.elo import ELOSystem

        elo_system = ELOSystem(k_factor=20.0, home_advantage=100.0)
        team_ratings: dict[int, float] = {}

        async with get_async_session() as session:
            # Get all finished matches ordered by date
            result = await session.execute(text("""
                SELECT id, home_team_id, away_team_id, home_score, away_score, match_date
                FROM matches
                WHERE status = 'FINISHED'
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                ORDER BY match_date ASC
            """))
            matches = result.fetchall()

            logger.info(f"Processing {len(matches)} matches for ELO calculation")

            for match in matches:
                home_id = match.home_team_id
                away_id = match.away_team_id

                # Initialize at 1500 if new
                if home_id not in team_ratings:
                    team_ratings[home_id] = 1500.0
                if away_id not in team_ratings:
                    team_ratings[away_id] = 1500.0

                # Calculate new ratings
                new_home, new_away = elo_system.update_ratings(
                    home_rating=team_ratings[home_id],
                    away_rating=team_ratings[away_id],
                    home_goals=match.home_score,
                    away_goals=match.away_score,
                )

                team_ratings[home_id] = new_home
                team_ratings[away_id] = new_away

            # Update database
            updated = 0
            for team_id, elo in team_ratings.items():
                clamped_elo = max(1000.0, min(2500.0, elo))
                await session.execute(
                    text("UPDATE teams SET elo_rating = :elo, updated_at = NOW() WHERE id = :id"),
                    {"elo": clamped_elo, "id": team_id}
                )
                updated += 1

            await session.commit()
            logger.info(f"Updated ELO for {updated} teams")
            return updated

    @staticmethod
    async def prefill_predictions_for_upcoming() -> int:
        """Pre-generate predictions for all upcoming matches."""
        from src.db.services.prediction_service import PredictionService

        async with get_async_session() as session:
            # Get upcoming matches without predictions
            result = await session.execute(text("""
                SELECT m.id, m.external_id, m.home_team_id, m.away_team_id,
                       m.competition_code, m.match_date,
                       ht.name as home_team, at.name as away_team
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                LEFT JOIN predictions p ON m.id = p.match_id
                WHERE m.status IN ('SCHEDULED', 'TIMED')
                    AND m.match_date > NOW()
                    AND m.match_date < NOW() + INTERVAL '14 days'
                    AND p.id IS NULL
                ORDER BY m.match_date
            """))
            upcoming = result.fetchall()

            logger.info(f"Found {len(upcoming)} upcoming matches without predictions")

            generated = 0
            for match in upcoming:
                try:
                    # Generate prediction using ensemble
                    from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor

                    # Get team stats
                    team_result = await session.execute(text("""
                        SELECT t.id, t.elo_rating, t.avg_goals_scored_home, t.avg_goals_scored_away,
                               t.avg_goals_conceded_home, t.avg_goals_conceded_away, t.form_score,
                               t.rest_days, t.fixture_congestion
                        FROM teams t WHERE t.id IN (:home_id, :away_id)
                    """), {"home_id": match.home_team_id, "away_id": match.away_team_id})
                    teams = {t.id: t for t in team_result.fetchall()}

                    home = teams.get(match.home_team_id)
                    away = teams.get(match.away_team_id)

                    if not home or not away:
                        continue

                    # Run ensemble prediction
                    pred = advanced_ensemble_predictor.predict(
                        home_attack=float(home.avg_goals_scored_home or 1.3),
                        home_defense=float(home.avg_goals_conceded_home or 1.3),
                        away_attack=float(away.avg_goals_scored_away or 1.3),
                        away_defense=float(away.avg_goals_conceded_away or 1.3),
                        home_elo=float(home.elo_rating or 1500),
                        away_elo=float(away.elo_rating or 1500),
                        home_team_id=match.home_team_id,
                        away_team_id=match.away_team_id,
                        home_form_score=float(home.form_score or 0.5) * 100,
                        away_form_score=float(away.form_score or 0.5) * 100,
                        home_rest_days=float(home.rest_days or 0.5),
                        away_rest_days=float(away.rest_days or 0.5),
                        home_congestion=float(home.fixture_congestion or 0.5),
                        away_congestion=float(away.fixture_congestion or 0.5),
                    )

                    # Save prediction
                    await PredictionService.save_prediction_from_api({
                        "match_id": match.id,
                        "match_external_id": match.external_id,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "competition_code": match.competition_code,
                        "match_date": match.match_date.isoformat(),
                        "home_win_prob": pred.home_win_prob,
                        "draw_prob": pred.draw_prob,
                        "away_win_prob": pred.away_win_prob,
                        "confidence": pred.confidence,
                        "recommendation": pred.recommended_bet,
                        "explanation": f"Prédiction pré-calculée pour {match.home_team} vs {match.away_team}",
                    })
                    generated += 1

                except Exception as e:
                    logger.warning(f"Failed to generate prediction for match {match.id}: {e}")

            logger.info(f"Pre-generated {generated} predictions")
            return generated

    @staticmethod
    async def warm_redis_cache() -> int:
        """Pre-warm Redis cache with predictions and stats."""
        import json
        from src.core.cache import cache_set

        cached = 0
        async with get_async_session() as session:
            # Cache all predictions for upcoming matches
            result = await session.execute(text("""
                SELECT p.match_id, p.home_prob, p.draw_prob, p.away_prob,
                       p.predicted_outcome, p.confidence, p.value_score,
                       p.explanation, p.created_at,
                       m.match_date, m.competition_code,
                       ht.name as home_team, at.name as away_team
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE m.match_date > NOW() AND m.match_date < NOW() + INTERVAL '14 days'
            """))
            predictions = result.fetchall()

            for pred in predictions:
                cache_data = {
                    "match_id": pred.match_id,
                    "home_team": pred.home_team,
                    "away_team": pred.away_team,
                    "competition": pred.competition_code,
                    "match_date": pred.match_date.isoformat(),
                    "probabilities": {
                        "home_win": float(pred.home_prob),
                        "draw": float(pred.draw_prob),
                        "away_win": float(pred.away_prob),
                    },
                    "recommended_bet": pred.predicted_outcome,
                    "confidence": float(pred.confidence),
                    "value_score": float(pred.value_score) if pred.value_score else 0.1,
                    "explanation": pred.explanation,
                    "created_at": pred.created_at.isoformat(),
                }

                try:
                    await cache_set(
                        f"prediction:{pred.match_id}",
                        json.dumps(cache_data, default=str),
                        ttl=3600  # 1 hour
                    )
                    cached += 1
                except Exception as e:
                    logger.warning(f"Failed to cache prediction {pred.match_id}: {e}")

            logger.info(f"Cached {cached} predictions in Redis")
            return cached

    @staticmethod
    async def fill_news_items() -> int:
        """Fetch news from RSS feeds and store in database."""
        from src.vector.news_ingestion import get_ingestion_service

        saved = 0
        try:
            service = get_ingestion_service()

            # Fetch general football news
            general_news = await service.fetch_general_football_news(max_per_source=10)
            logger.info(f"Fetched {len(general_news)} general news articles")

            async with get_async_session() as session:
                for article in general_news:
                    try:
                        # Create unique external_id from URL or title hash
                        external_id = hashlib.md5(
                            (article.url or article.title).encode()
                        ).hexdigest()[:20]

                        # Check if already exists
                        existing = await session.execute(
                            text("SELECT id FROM news_items WHERE external_id = :ext_id"),
                            {"ext_id": external_id}
                        )
                        if existing.fetchone():
                            continue

                        # Determine team_ids from team_name
                        team_ids = None
                        if article.team_id:
                            team_ids = json.dumps([article.team_id])

                        # Insert news item
                        await session.execute(
                            text("""
                                INSERT INTO news_items (
                                    external_id, title, content, url, source,
                                    team_ids, is_injury_news, published_at, created_at
                                ) VALUES (
                                    :external_id, :title, :content, :url, :source,
                                    :team_ids, :is_injury_news, :published_at, NOW()
                                )
                            """),
                            {
                                "external_id": external_id,
                                "title": article.title[:500],
                                "content": article.content[:2000] if article.content else None,
                                "url": article.url or f"https://news.google.com/search?q={article.title[:50]}",
                                "source": article.source,
                                "team_ids": team_ids,
                                "is_injury_news": article.article_type == "injury",
                                "published_at": article.published_at,
                            }
                        )
                        saved += 1

                    except Exception as e:
                        logger.warning(f"Failed to save news article: {e}")
                        continue

                await session.commit()

            logger.info(f"Saved {saved} news articles to database")
            return saved

        except Exception as e:
            logger.error(f"Error filling news items: {e}")
            return saved

    @staticmethod
    async def run_full_prefill(triggered_by: str = "startup") -> dict[str, Any]:
        """Run complete data prefill pipeline."""
        logger.info("Starting full data prefill...")
        start = datetime.now()
        errors: list[str] = []

        results: dict[str, Any] = {
            "team_data": {},
            "elo_ratings": 0,
            "predictions": 0,
            "redis_cache": 0,
            "news_items": 0,
        }

        # 1. Fill team data
        try:
            results["team_data"] = await DataPrefillService.fill_all_team_data()
            total_team_updates = sum(results["team_data"].values())
            await log_sync_operation("team_data", "success", total_team_updates, triggered_by=triggered_by)
        except Exception as e:
            logger.error(f"Team data prefill failed: {e}")
            errors.append(f"team_data: {str(e)}")
            await log_sync_operation("team_data", "failed", 0, str(e), triggered_by)

        # 2. Calculate ELO ratings
        try:
            results["elo_ratings"] = await DataPrefillService.calculate_elo_ratings()
            await log_sync_operation("elo_ratings", "success", results["elo_ratings"], triggered_by=triggered_by)
        except Exception as e:
            logger.error(f"ELO calculation failed: {e}")
            errors.append(f"elo_ratings: {str(e)}")
            await log_sync_operation("elo_ratings", "failed", 0, str(e), triggered_by)

        # 3. Pre-generate predictions
        try:
            results["predictions"] = await DataPrefillService.prefill_predictions_for_upcoming()
            await log_sync_operation("predictions", "success", results["predictions"], triggered_by=triggered_by)
        except Exception as e:
            logger.error(f"Predictions prefill failed: {e}")
            errors.append(f"predictions: {str(e)}")
            await log_sync_operation("predictions", "failed", 0, str(e), triggered_by)

        # 4. Warm Redis cache
        try:
            results["redis_cache"] = await DataPrefillService.warm_redis_cache()
            await log_sync_operation("redis_cache", "success", results["redis_cache"], triggered_by=triggered_by)
        except Exception as e:
            logger.error(f"Redis cache warm failed: {e}")
            errors.append(f"redis_cache: {str(e)}")
            await log_sync_operation("redis_cache", "failed", 0, str(e), triggered_by)

        # 5. Fill news items from RSS
        try:
            results["news_items"] = await DataPrefillService.fill_news_items()
            await log_sync_operation("news_items", "success", results["news_items"], triggered_by=triggered_by)
        except Exception as e:
            logger.error(f"News items fetch failed: {e}")
            errors.append(f"news_items: {str(e)}")
            await log_sync_operation("news_items", "failed", 0, str(e), triggered_by)

        duration = (datetime.now() - start).total_seconds()
        results["duration_seconds"] = duration
        results["errors"] = errors

        # Log overall prefill operation
        overall_status = "success" if not errors else "partial"
        total_records = (
            sum(results["team_data"].values()) +
            results["elo_ratings"] +
            results["predictions"] +
            results["redis_cache"] +
            results["news_items"]
        )
        await log_sync_operation(
            "full_prefill",
            overall_status,
            total_records,
            "; ".join(errors) if errors else None,
            triggered_by
        )

        logger.info(f"Full prefill complete in {duration:.1f}s: {results}")
        return results


# Singleton instance
prefill_service = DataPrefillService()


async def run_prefill() -> dict[str, Any]:
    """Run the full prefill pipeline."""
    return await prefill_service.run_full_prefill()
