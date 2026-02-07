"""Tennis data sync service.

Fetches tennis matches, players, and tournaments from SportDevs API,
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


async def sync_tennis_matches() -> None:
    """Full tennis sync pipeline: players → tournaments → matches → predictions."""
    logger.info("[Tennis Sync] Starting tennis sync...")

    try:
        await log_sync_operation("tennis_sync", "running", 0, triggered_by="scheduler")

        players_synced = await _sync_players()
        tournaments_synced = await _sync_tournaments()
        matches_synced = await _sync_matches()
        odds_synced = await _sync_odds()
        predictions_generated = await _generate_predictions()

        total = (
            players_synced
            + tournaments_synced
            + matches_synced
            + odds_synced
            + predictions_generated
        )

        await log_sync_operation("tennis_sync", "success", total, triggered_by="scheduler")
        logger.info(
            f"[Tennis Sync] Complete: {players_synced} players, "
            f"{tournaments_synced} tournaments, "
            f"{matches_synced} matches, {odds_synced} odds, "
            f"{predictions_generated} predictions"
        )

    except Exception as e:
        logger.error(f"[Tennis Sync] Failed: {e}", exc_info=True)
        await log_sync_operation(
            "tennis_sync", "error", 0, error_message=str(e)[:500], triggered_by="scheduler"
        )


async def _sync_players() -> int:
    """Fetch and upsert tennis players."""
    from src.data.sources.sportdevs_tennis import get_players

    players = await get_players()
    if not players:
        return 0

    count = 0
    async with _get_session() as session:
        for player_data in players:
            ext_id = str(player_data.get("id", ""))
            name = player_data.get("name", "")
            if not ext_id or not name:
                continue

            country = player_data.get("country", {})
            country_name = country.get("name", "") if isinstance(country, dict) else ""
            photo = player_data.get("photo", "")
            ranking = player_data.get("ranking")
            circuit = player_data.get("circuit", "ATP")

            ranking_val = _safe_int(ranking)

            await session.execute(
                text(
                    """
                    INSERT INTO tennis_players (
                        external_id, name, country, photo_url,
                        atp_ranking, circuit
                    )
                    VALUES (:ext_id, :name, :country, :photo, :ranking, :circuit)
                    ON CONFLICT (external_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        country = EXCLUDED.country,
                        photo_url = EXCLUDED.photo_url,
                        atp_ranking = COALESCE(EXCLUDED.atp_ranking, tennis_players.atp_ranking),
                        circuit = EXCLUDED.circuit,
                        updated_at = NOW()
                """
                ),
                {
                    "ext_id": ext_id,
                    "name": name[:100],
                    "country": country_name[:50] if country_name else None,
                    "photo": photo or None,
                    "ranking": ranking_val,
                    "circuit": (circuit[:10] if circuit else "ATP"),
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[Tennis Sync] Upserted {count} players")
    return count


async def _sync_tournaments() -> int:
    """Fetch and upsert tennis tournaments."""
    from src.data.sources.sportdevs_tennis import get_tournaments

    tournaments = await get_tournaments()
    if not tournaments:
        return 0

    count = 0
    async with _get_session() as session:
        for t in tournaments:
            ext_id = str(t.get("id", ""))
            name = t.get("name", "")
            if not ext_id or not name:
                continue

            surface = _normalize_surface(t.get("surface", "hard"))
            category = t.get("category", "atp_250")
            country_data = t.get("country", {})
            country = country_data.get("name", "") if isinstance(country_data, dict) else ""
            circuit = t.get("circuit", "ATP")

            await session.execute(
                text(
                    """
                    INSERT INTO tennis_tournaments (
                        external_id, name, category, surface, country, circuit
                    )
                    VALUES (:ext_id, :name, :category, :surface, :country, :circuit)
                    ON CONFLICT (external_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        category = EXCLUDED.category,
                        surface = EXCLUDED.surface,
                        country = EXCLUDED.country,
                        circuit = EXCLUDED.circuit
                """
                ),
                {
                    "ext_id": ext_id,
                    "name": name[:100],
                    "category": category[:30],
                    "surface": surface,
                    "country": country[:50] if country else None,
                    "circuit": (circuit[:10] if circuit else "ATP"),
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[Tennis Sync] Upserted {count} tournaments")
    return count


async def _sync_matches() -> int:
    """Fetch upcoming tennis matches for the next 30 days."""
    from src.data.sources.sportdevs_tennis import get_matches

    today = date.today()
    count = 0

    # Fetch matches for today + next 30 days
    for day_offset in range(31):
        match_date = today + timedelta(days=day_offset)
        date_str = match_date.isoformat()

        matches = await get_matches(date_str)
        if not matches:
            continue

        async with _get_session() as session:
            for match in matches:
                ext_id = str(match.get("id", ""))
                if not ext_id:
                    continue

                # Get player external IDs
                home_player = match.get("home", {}) or {}
                away_player = match.get("away", {}) or {}
                home_ext_id = str(home_player.get("id", ""))
                away_ext_id = str(away_player.get("id", ""))

                if not home_ext_id or not away_ext_id:
                    continue

                # Resolve internal player IDs (create if needed)
                p1_id = await _ensure_player(session, home_ext_id, home_player.get("name", "P1"))
                p2_id = await _ensure_player(session, away_ext_id, away_player.get("name", "P2"))

                if not p1_id or not p2_id:
                    continue

                # Resolve tournament
                tournament_data = match.get("tournament", {}) or {}
                tournament_ext_id = str(tournament_data.get("id", ""))
                tournament_id = await _ensure_tournament(
                    session, tournament_ext_id, tournament_data.get("name", "Unknown")
                )

                if not tournament_id:
                    continue

                surface = _normalize_surface(tournament_data.get("surface", "hard"))
                round_name = match.get("round", "")
                raw_datetime = match.get("startTimestamp") or f"{date_str}T00:00:00Z"

                if isinstance(raw_datetime, (int, float)):
                    match_datetime = datetime.fromtimestamp(raw_datetime, tz=UTC)
                elif isinstance(raw_datetime, str):
                    try:
                        match_datetime = datetime.fromisoformat(raw_datetime.replace("Z", "+00:00"))
                    except ValueError:
                        match_datetime = datetime(
                            match_date.year,
                            match_date.month,
                            match_date.day,
                            tzinfo=UTC,
                        )
                else:
                    match_datetime = datetime(
                        match_date.year,
                        match_date.month,
                        match_date.day,
                        tzinfo=UTC,
                    )

                # Map status
                raw_status = match.get("status")
                if isinstance(raw_status, dict):
                    status_str = str(raw_status.get("type", "notstarted"))
                else:
                    status_str = "notstarted"
                status = _map_tennis_status(status_str)

                # Score
                home_score_data = match.get("homeScore", {}) or {}
                away_score_data = match.get("awayScore", {}) or {}
                sets_p1 = _safe_int(home_score_data.get("current"))
                sets_p2 = _safe_int(away_score_data.get("current"))

                winner_id_val = None
                if status == "finished":
                    if sets_p1 is not None and sets_p2 is not None:
                        winner_id_val = p1_id if sets_p1 > sets_p2 else p2_id

                await session.execute(
                    text(
                        """
                        INSERT INTO tennis_matches (
                            external_id, player1_id, player2_id, tournament_id,
                            round, match_date, surface, status,
                            winner_id, sets_player1, sets_player2
                        )
                        VALUES (
                            :ext_id, :p1_id, :p2_id, :t_id,
                            :round, :match_date, :surface, :status,
                            :winner_id, :sets_p1, :sets_p2
                        )
                        ON CONFLICT (external_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            winner_id = EXCLUDED.winner_id,
                            sets_player1 = EXCLUDED.sets_player1,
                            sets_player2 = EXCLUDED.sets_player2,
                            updated_at = NOW()
                    """
                    ),
                    {
                        "ext_id": ext_id,
                        "p1_id": p1_id,
                        "p2_id": p2_id,
                        "t_id": tournament_id,
                        "round": (round_name[:30] if round_name else None),
                        "match_date": match_datetime,
                        "surface": surface,
                        "status": status,
                        "winner_id": winner_id_val,
                        "sets_p1": sets_p1,
                        "sets_p2": sets_p2,
                    },
                )
                count += 1

            await session.commit()

        await asyncio.sleep(2)  # Respect rate limits

    logger.info(f"[Tennis Sync] Upserted {count} matches")
    return count


async def _ensure_player(session: Any, ext_id: str, name: str) -> int | None:
    """Get or create a player by external ID. Returns internal ID."""
    if not ext_id:
        return None

    result = await session.execute(
        text("SELECT id FROM tennis_players WHERE external_id = :ext_id"),
        {"ext_id": ext_id},
    )
    row = result.fetchone()
    if row:
        return row[0]  # type: ignore[no-any-return]

    # Create minimal player record
    result = await session.execute(
        text(
            """
            INSERT INTO tennis_players (external_id, name)
            VALUES (:ext_id, :name)
            ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """
        ),
        {"ext_id": ext_id, "name": name[:100]},
    )
    row = result.fetchone()
    return row[0] if row else None  # type: ignore[no-any-return]


async def _ensure_tournament(session: Any, ext_id: str, name: str) -> int | None:
    """Get or create a tournament by external ID. Returns internal ID."""
    if not ext_id:
        return None

    result = await session.execute(
        text("SELECT id FROM tennis_tournaments WHERE external_id = :ext_id"),
        {"ext_id": ext_id},
    )
    row = result.fetchone()
    if row:
        return row[0]  # type: ignore[no-any-return]

    # Create minimal tournament record
    result = await session.execute(
        text(
            """
            INSERT INTO tennis_tournaments (external_id, name, category, surface)
            VALUES (:ext_id, :name, 'atp_250', 'hard')
            ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """
        ),
        {"ext_id": ext_id, "name": name[:100]},
    )
    row = result.fetchone()
    return row[0] if row else None  # type: ignore[no-any-return]


def _map_tennis_status(api_status: str) -> str:
    """Map SportDevs tennis status to our internal status."""
    status_map: dict[str, str] = {
        "notstarted": "scheduled",
        "inprogress": "live",
        "finished": "finished",
        "canceled": "postponed",
        "postponed": "postponed",
        "interrupted": "postponed",
    }
    return status_map.get(api_status.lower(), "scheduled")


def _normalize_surface(surface: str | None) -> str:
    """Normalize surface name."""
    if not surface:
        return "hard"
    s = surface.lower().strip()
    if "clay" in s:
        return "clay"
    if "grass" in s:
        return "grass"
    if "indoor" in s or "carpet" in s:
        return "indoor"
    return "hard"


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int or None."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


async def _generate_predictions() -> int:
    """Generate predictions for all scheduled tennis matches."""
    from src.prediction_engine.tennis_predictor import predict_tennis

    count = 0
    async with _get_session() as session:
        result = await session.execute(
            text(
                """
                SELECT m.id, m.surface,
                       p1.elo_hard as p1_elo_hard, p1.elo_clay as p1_elo_clay,
                       p1.elo_grass as p1_elo_grass, p1.elo_indoor as p1_elo_indoor,
                       p1.atp_ranking as p1_ranking, p1.win_rate_ytd as p1_wr,
                       p2.elo_hard as p2_elo_hard, p2.elo_clay as p2_elo_clay,
                       p2.elo_grass as p2_elo_grass, p2.elo_indoor as p2_elo_indoor,
                       p2.atp_ranking as p2_ranking, p2.win_rate_ytd as p2_wr
                FROM tennis_matches m
                JOIN tennis_players p1 ON m.player1_id = p1.id
                JOIN tennis_players p2 ON m.player2_id = p2.id
                WHERE m.status = 'scheduled'
                  AND m.pred_player1_prob IS NULL
            """
            )
        )

        rows = result.fetchall()
        for row in rows:
            surface = row.surface or "hard"
            p1_elo = _get_surface_elo(
                surface, row.p1_elo_hard, row.p1_elo_clay, row.p1_elo_grass, row.p1_elo_indoor
            )
            p2_elo = _get_surface_elo(
                surface, row.p2_elo_hard, row.p2_elo_clay, row.p2_elo_grass, row.p2_elo_indoor
            )

            pred = predict_tennis(
                player1_elo=p1_elo,
                player2_elo=p2_elo,
                player1_ranking=_safe_int(row.p1_ranking),
                player2_ranking=_safe_int(row.p2_ranking),
                player1_win_rate=float(row.p1_wr or 50) / 100.0,
                player2_win_rate=float(row.p2_wr or 50) / 100.0,
                surface=surface,
            )

            await session.execute(
                text(
                    """
                    UPDATE tennis_matches SET
                        pred_player1_prob = :p1p, pred_player2_prob = :p2p,
                        pred_confidence = :conf, pred_explanation = :expl,
                        updated_at = NOW()
                    WHERE id = :mid
                """
                ),
                {
                    "p1p": pred.player1_prob,
                    "p2p": pred.player2_prob,
                    "conf": pred.confidence,
                    "expl": pred.explanation,
                    "mid": row.id,
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[Tennis Sync] Generated {count} predictions")
    return count


async def _sync_odds() -> int:
    """Fetch bookmaker odds for scheduled tennis matches."""
    from src.data.odds_client import get_binary_match_odds

    count = 0
    async with _get_session() as session:
        result = await session.execute(
            text(
                """
                SELECT m.id, p1.name as p1_name, p2.name as p2_name,
                       t.circuit
                FROM tennis_matches m
                JOIN tennis_players p1 ON m.player1_id = p1.id
                JOIN tennis_players p2 ON m.player2_id = p2.id
                JOIN tennis_tournaments t ON m.tournament_id = t.id
                WHERE m.status = 'scheduled'
                  AND m.odds_player1 IS NULL
            """
            )
        )

        rows = result.fetchall()
        for row in rows:
            sport_code = row.circuit if row.circuit in ("ATP", "WTA") else "ATP"
            odds = await get_binary_match_odds(row.p1_name, row.p2_name, sport_code)
            if not odds:
                continue

            await session.execute(
                text(
                    """
                    UPDATE tennis_matches SET
                        odds_player1 = :o1, odds_player2 = :o2,
                        updated_at = NOW()
                    WHERE id = :mid
                """
                ),
                {"o1": odds["home"], "o2": odds["away"], "mid": row.id},
            )
            count += 1

        await session.commit()

    logger.info(f"[Tennis Sync] Updated odds for {count} matches")
    return count


def _get_surface_elo(
    surface: str,
    elo_hard: Any,
    elo_clay: Any,
    elo_grass: Any,
    elo_indoor: Any,
) -> float:
    """Get the appropriate ELO rating for a given surface."""
    elo_map: dict[str, Any] = {
        "hard": elo_hard,
        "clay": elo_clay,
        "grass": elo_grass,
        "indoor": elo_indoor,
    }
    elo = elo_map.get(surface, elo_hard)
    return float(elo) if elo is not None else 1500.0
