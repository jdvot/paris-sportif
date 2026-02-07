"""NBA data sync service.

Fetches NBA games, teams, and standings from API-Sports,
generates predictions, and stores everything in the database.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text

from src.db import async_session_factory
from src.services.data_prefill_service import log_sync_operation

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _get_session():  # type: ignore[no-untyped-def]
    """Async session context manager."""
    async with async_session_factory() as session:
        yield session


async def sync_nba_games() -> None:
    """Full NBA sync pipeline: teams → standings → games → predictions."""
    logger.info("[NBA Sync] Starting NBA sync...")

    try:
        await log_sync_operation("nba_sync", "running", 0, triggered_by="scheduler")

        teams_synced = await _sync_teams()
        standings_synced = await _sync_standings()
        games_synced = await _sync_games()
        odds_synced = await _sync_odds()
        predictions_generated = await _generate_predictions()

        total = teams_synced + standings_synced + games_synced + predictions_generated

        await log_sync_operation("nba_sync", "success", total, triggered_by="scheduler")
        logger.info(
            f"[NBA Sync] Complete: {teams_synced} teams, {standings_synced} standings, "
            f"{games_synced} games, {odds_synced} odds, {predictions_generated} predictions"
        )

    except Exception as e:
        logger.error(f"[NBA Sync] Failed: {e}", exc_info=True)
        await log_sync_operation(
            "nba_sync", "error", 0, error_message=str(e)[:500], triggered_by="scheduler"
        )


async def _sync_teams() -> int:
    """Fetch and upsert NBA teams."""
    from src.data.sources.api_sports_nba import get_teams

    teams = await get_teams()
    if not teams:
        return 0

    count = 0
    async with _get_session() as session:
        for team_data in teams:
            team_id = str(team_data.get("id", ""))
            name = team_data.get("name", "")
            if not team_id or not name:
                continue

            code = team_data.get("code", "")
            logo = team_data.get("logo", "")
            leagues_data: dict[str, Any] = team_data.get("leagues", {})
            nba_data: dict[str, Any] = leagues_data.get("standard", {})
            conference = nba_data.get("conference", "")
            division = nba_data.get("division", "")

            await session.execute(
                text(
                    """
                    INSERT INTO basketball_teams (
                        external_id, name, short_name, logo_url, league, conference, division
                    )
                    VALUES (:ext_id, :name, :short_name, :logo, 'NBA', :conf, :div)
                    ON CONFLICT (external_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        short_name = EXCLUDED.short_name,
                        logo_url = EXCLUDED.logo_url,
                        conference = EXCLUDED.conference,
                        division = EXCLUDED.division,
                        updated_at = NOW()
                """
                ),
                {
                    "ext_id": team_id,
                    "name": name,
                    "short_name": code[:10] if code else None,
                    "logo": logo or None,
                    "conf": conference or None,
                    "div": division or None,
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[NBA Sync] Upserted {count} teams")
    return count


async def _sync_standings() -> int:
    """Fetch standings and update team records."""
    from src.data.sources.api_sports_nba import get_standings

    standings = await get_standings("standard", "2025")
    if not standings:
        return 0

    count = 0
    async with _get_session() as session:
        for entry in standings:
            team_data: dict[str, Any] = entry.get("team", {})
            team_ext_id = str(team_data.get("id", ""))
            if not team_ext_id:
                continue

            win_data: dict[str, Any] = entry.get("win", {})
            loss_data: dict[str, Any] = entry.get("loss", {})
            wins = int(win_data.get("total", 0))
            losses = int(loss_data.get("total", 0))
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

            await session.execute(
                text(
                    """
                    UPDATE basketball_teams SET
                        wins = :wins,
                        losses = :losses,
                        win_rate_ytd = :win_rate,
                        updated_at = NOW()
                    WHERE external_id = :ext_id
                """
                ),
                {
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(win_rate, 2),
                    "ext_id": team_ext_id,
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[NBA Sync] Updated standings for {count} teams")
    return count


async def _sync_games() -> int:
    """Fetch upcoming and recent NBA games for the next 30 days."""
    from src.data.sources.api_sports_nba import get_games

    today = date.today()
    count = 0

    # Fetch games for today + next 30 days
    for day_offset in range(31):
        game_date = today + timedelta(days=day_offset)
        date_str = game_date.isoformat()

        games = await get_games(date_str)
        if not games:
            continue

        async with _get_session() as session:
            for game in games:
                game_id = str(game.get("id", ""))
                if not game_id:
                    continue

                teams_data: dict[str, Any] = game.get("teams", {})
                home_data: dict[str, Any] = teams_data.get("home", {})
                away_data: dict[str, Any] = teams_data.get("visitors", {})

                home_ext_id = str(home_data.get("id", ""))
                away_ext_id = str(away_data.get("id", ""))

                if not home_ext_id or not away_ext_id:
                    continue

                # Resolve internal team IDs
                home_row = await session.execute(
                    text("SELECT id FROM basketball_teams WHERE external_id = :ext_id"),
                    {"ext_id": home_ext_id},
                )
                away_row = await session.execute(
                    text("SELECT id FROM basketball_teams WHERE external_id = :ext_id"),
                    {"ext_id": away_ext_id},
                )

                home_result = home_row.fetchone()
                away_result = away_row.fetchone()

                if not home_result or not away_result:
                    continue

                home_team_id: int = home_result[0]
                away_team_id: int = away_result[0]

                # Map API-Sports status
                status_data: dict[str, Any] = game.get("status", {})
                api_status = str(status_data.get("short", ""))
                status = _map_nba_status(api_status)

                scores_data: dict[str, Any] = game.get("scores", {})
                home_scores: dict[str, Any] = scores_data.get("home", {})
                away_scores: dict[str, Any] = scores_data.get("visitors", {})

                date_info: dict[str, Any] = game.get("date", {})
                match_date_str = date_info.get("start", f"{date_str}T00:00:00Z")

                try:
                    match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    match_date = datetime(
                        game_date.year,
                        game_date.month,
                        game_date.day,
                        tzinfo=UTC,
                    )

                season_info: dict[str, Any] = game.get("season", {})
                season = str(season_info) if isinstance(season_info, int) else "2025-26"

                await session.execute(
                    text(
                        """
                        INSERT INTO basketball_matches (
                            external_id, home_team_id, away_team_id, league, season,
                            match_date, status,
                            home_score, away_score,
                            home_q1, away_q1, home_q2, away_q2,
                            home_q3, away_q3, home_q4, away_q4
                        )
                        VALUES (
                            :ext_id, :home_id, :away_id, 'NBA', :season,
                            :match_date, :status,
                            :home_score, :away_score,
                            :h_q1, :a_q1, :h_q2, :a_q2,
                            :h_q3, :a_q3, :h_q4, :a_q4
                        )
                        ON CONFLICT (external_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            home_score = EXCLUDED.home_score,
                            away_score = EXCLUDED.away_score,
                            home_q1 = EXCLUDED.home_q1,
                            away_q1 = EXCLUDED.away_q1,
                            home_q2 = EXCLUDED.home_q2,
                            away_q2 = EXCLUDED.away_q2,
                            home_q3 = EXCLUDED.home_q3,
                            away_q3 = EXCLUDED.away_q3,
                            home_q4 = EXCLUDED.home_q4,
                            away_q4 = EXCLUDED.away_q4,
                            updated_at = NOW()
                    """
                    ),
                    {
                        "ext_id": game_id,
                        "home_id": home_team_id,
                        "away_id": away_team_id,
                        "season": season,
                        "match_date": match_date,
                        "status": status,
                        "home_score": _safe_int(home_scores.get("points")),
                        "away_score": _safe_int(away_scores.get("points")),
                        "h_q1": _safe_linescore(home_scores, 0),
                        "a_q1": _safe_linescore(away_scores, 0),
                        "h_q2": _safe_linescore(home_scores, 1),
                        "a_q2": _safe_linescore(away_scores, 1),
                        "h_q3": _safe_linescore(home_scores, 2),
                        "a_q3": _safe_linescore(away_scores, 2),
                        "h_q4": _safe_linescore(home_scores, 3),
                        "a_q4": _safe_linescore(away_scores, 3),
                    },
                )
                count += 1

            await session.commit()

        # Respect rate limits between days
        await asyncio.sleep(1)

    logger.info(f"[NBA Sync] Upserted {count} games")
    return count


def _map_nba_status(api_status: str) -> str:
    """Map API-Sports NBA status to our internal status."""
    status_map: dict[str, str] = {
        "NS": "scheduled",  # Not started
        "Q1": "live",
        "Q2": "live",
        "Q3": "live",
        "Q4": "live",
        "OT": "live",
        "HT": "live",  # Half-time
        "BT": "live",  # Break time
        "FT": "finished",
        "AOT": "finished",  # After overtime
        "POST": "postponed",
        "CANC": "postponed",
        "SUSP": "postponed",
    }
    return status_map.get(api_status, "scheduled")


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int or None."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_linescore(scores: dict[str, Any], index: int) -> int | None:
    """Safely get a quarter score from linescore array."""
    linescore = scores.get("linescore")
    if isinstance(linescore, list) and len(linescore) > index:
        return _safe_int(linescore[index])
    return None


async def _generate_predictions() -> int:
    """Generate predictions for all scheduled NBA games."""
    from src.prediction_engine.basketball_predictor import predict_basketball

    count = 0
    async with _get_session() as session:
        # Get all scheduled games without predictions
        result = await session.execute(
            text(
                """
                SELECT m.id, m.home_team_id, m.away_team_id,
                       m.is_back_to_back_home, m.is_back_to_back_away,
                       ht.elo_rating as home_elo, ht.offensive_rating as home_off,
                       ht.defensive_rating as home_def, ht.pace as home_pace,
                       ht.win_rate_ytd as home_wr,
                       at.elo_rating as away_elo, at.offensive_rating as away_off,
                       at.defensive_rating as away_def, at.pace as away_pace,
                       at.win_rate_ytd as away_wr
                FROM basketball_matches m
                JOIN basketball_teams ht ON m.home_team_id = ht.id
                JOIN basketball_teams at ON m.away_team_id = at.id
                WHERE m.status = 'scheduled'
                  AND m.pred_home_prob IS NULL
            """
            )
        )

        rows = result.fetchall()
        for row in rows:
            pred = predict_basketball(
                home_elo=float(row.home_elo or 1500),
                away_elo=float(row.away_elo or 1500),
                home_off_rating=float(row.home_off) if row.home_off else None,
                home_def_rating=float(row.home_def) if row.home_def else None,
                away_off_rating=float(row.away_off) if row.away_off else None,
                away_def_rating=float(row.away_def) if row.away_def else None,
                home_pace=float(row.home_pace) if row.home_pace else None,
                away_pace=float(row.away_pace) if row.away_pace else None,
                is_back_to_back_home=bool(row.is_back_to_back_home),
                is_back_to_back_away=bool(row.is_back_to_back_away),
                home_win_rate=float(row.home_wr or 50) / 100.0,
                away_win_rate=float(row.away_wr or 50) / 100.0,
            )

            await session.execute(
                text(
                    """
                    UPDATE basketball_matches SET
                        pred_home_prob = :hp, pred_away_prob = :ap,
                        pred_confidence = :conf, pred_explanation = :expl,
                        updated_at = NOW()
                    WHERE id = :mid
                """
                ),
                {
                    "hp": pred.home_prob,
                    "ap": pred.away_prob,
                    "conf": pred.confidence,
                    "expl": pred.explanation,
                    "mid": row.id,
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[NBA Sync] Generated {count} predictions")
    return count


async def _sync_odds() -> int:
    """Fetch bookmaker odds for scheduled NBA games."""
    from src.data.odds_client import get_binary_match_odds

    count = 0
    async with _get_session() as session:
        result = await session.execute(
            text(
                """
                SELECT m.id, ht.name as home_name, at.name as away_name
                FROM basketball_matches m
                JOIN basketball_teams ht ON m.home_team_id = ht.id
                JOIN basketball_teams at ON m.away_team_id = at.id
                WHERE m.status = 'scheduled'
                  AND m.odds_home IS NULL
            """
            )
        )

        rows = result.fetchall()
        for row in rows:
            odds = await get_binary_match_odds(row.home_name, row.away_name, "NBA")
            if not odds:
                continue

            await session.execute(
                text(
                    """
                    UPDATE basketball_matches SET
                        odds_home = :oh, odds_away = :oa, updated_at = NOW()
                    WHERE id = :mid
                """
                ),
                {"oh": odds["home"], "oa": odds["away"], "mid": row.id},
            )
            count += 1

        await session.commit()

    logger.info(f"[NBA Sync] Updated odds for {count} games")
    return count
