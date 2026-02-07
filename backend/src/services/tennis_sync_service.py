"""Tennis data sync service.

Fetches tennis matches, players, and tournaments from Tennis Live Data API
(via RapidAPI), generates predictions, and stores everything in the database.
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
    """Fetch and upsert tennis players from ATP + WTA rankings."""
    from src.data.sources.sportdevs_tennis import get_rankings

    count = 0
    for tour in ("ATP", "WTA"):
        rankings = await get_rankings(tour)
        if not rankings:
            continue

        async with _get_session() as session:
            for player_data in rankings:
                # Tennis Live Data rankings: {first_name, last_name, ranking, country, ...}
                first_name = player_data.get("first_name", "")
                last_name = player_data.get("last_name", "")
                full_name = f"{first_name} {last_name}".strip()
                if not full_name:
                    continue

                # Use ranking position as a stable external ID (no player ID in this API)
                ranking = _safe_int(player_data.get("ranking"))
                country = player_data.get("country", "")
                # Build a stable external ID from tour + name (no numeric ID in rankings API)
                ext_id = f"{tour}_{full_name}".replace(" ", "_").lower()

                await session.execute(
                    text(
                        """
                        INSERT INTO tennis_players (
                            external_id, name, country,
                            atp_ranking, circuit
                        )
                        VALUES (:ext_id, :name, :country, :ranking, :circuit)
                        ON CONFLICT (external_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            country = EXCLUDED.country,
                            atp_ranking = COALESCE(
                                EXCLUDED.atp_ranking, tennis_players.atp_ranking
                            ),
                            circuit = EXCLUDED.circuit,
                            updated_at = NOW()
                    """
                    ),
                    {
                        "ext_id": ext_id[:100],
                        "name": full_name[:100],
                        "country": country[:50] if country else None,
                        "ranking": ranking,
                        "circuit": tour,
                    },
                )
                count += 1

            await session.commit()

    logger.info(f"[Tennis Sync] Upserted {count} players")
    return count


async def _sync_tournaments() -> int:
    """Fetch and upsert tennis tournaments from ATP + WTA."""
    from src.data.sources.sportdevs_tennis import get_tournaments

    count = 0
    for tour in ("ATP", "WTA"):
        tournaments = await get_tournaments(tour)
        if not tournaments:
            continue

        async with _get_session() as session:
            for t in tournaments:
                ext_id = str(t.get("id", ""))
                name = t.get("name", "")
                if not ext_id or not name:
                    continue

                surface = _normalize_surface(t.get("surface", "hard"))
                category = t.get("category", "atp_250")
                country_data = t.get("country", {})
                country = (
                    country_data.get("name", "")
                    if isinstance(country_data, dict)
                    else str(country_data) if country_data else ""
                )

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
                        "circuit": tour,
                    },
                )
                count += 1

            await session.commit()

    logger.info(f"[Tennis Sync] Upserted {count} tournaments")
    return count


async def _sync_matches() -> int:
    """Fetch tennis matches for today + next 14 days and past 7 days."""
    from src.data.sources.sportdevs_tennis import get_matches, get_upcoming_matches

    today = date.today()
    count = 0

    # Past results (7 days) + upcoming (14 days)
    for day_offset in range(-7, 15):
        match_date = today + timedelta(days=day_offset)
        date_str = match_date.isoformat()

        if day_offset < 0:
            matches = await get_matches(date_str)  # past results
        else:
            # Try upcoming first, then results
            matches = await get_upcoming_matches(date_str)
            if not matches:
                matches = await get_matches(date_str)

        if not matches:
            continue

        async with _get_session() as session:
            for match in matches:
                ext_id = str(match.get("id", ""))
                if not ext_id:
                    continue

                # Tennis Live Data: home_player/away_player or home_id/away_id
                home_name = match.get("home_player", "") or ""
                away_name = match.get("away_player", "") or ""
                home_id_str = str(match.get("home_id", ""))
                away_id_str = str(match.get("away_id", ""))

                if not home_name and not away_name:
                    continue

                # Resolve players by name (create ext_id from name)
                p1_ext = home_id_str if home_id_str else home_name.replace(" ", "_").lower()
                p2_ext = away_id_str if away_id_str else away_name.replace(" ", "_").lower()

                p1_id = await _ensure_player(session, p1_ext, home_name or "TBD")
                p2_id = await _ensure_player(session, p2_ext, away_name or "TBD")
                if not p1_id or not p2_id:
                    continue

                # Tournament
                tournament_name = match.get("tournament", "")
                tournament_ext = match.get("tournament_id", "")
                if not tournament_ext and tournament_name:
                    tournament_ext = tournament_name.replace(" ", "_").lower()
                tournament_id = await _ensure_tournament(
                    session, str(tournament_ext), str(tournament_name or "Unknown")
                )
                if not tournament_id:
                    continue

                surface = _normalize_surface(match.get("surface"))
                round_name = match.get("round_name", "") or match.get("round", "")

                # Parse date/time
                raw_date = match.get("date", date_str)
                if isinstance(raw_date, str):
                    try:
                        match_datetime = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    except ValueError:
                        match_datetime = datetime(
                            match_date.year, match_date.month, match_date.day, tzinfo=UTC
                        )
                else:
                    match_datetime = datetime(
                        match_date.year, match_date.month, match_date.day, tzinfo=UTC
                    )

                # Status mapping
                raw_status = str(match.get("status", "")).lower()
                status = _map_tennis_status(raw_status)

                # Score
                result_str = match.get("result", "")
                sets_p1, sets_p2 = _parse_tennis_result(result_str)

                winner_id_val = None
                if status == "finished" and sets_p1 is not None and sets_p2 is not None:
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
    """Map Tennis Live Data API status to our internal status."""
    status_map: dict[str, str] = {
        "notstarted": "scheduled",
        "scheduled": "scheduled",
        "inprogress": "live",
        "live": "live",
        "finished": "finished",
        "result": "finished",
        "canceled": "postponed",
        "cancelled": "postponed",
        "postponed": "postponed",
        "interrupted": "postponed",
        "suspended": "postponed",
        "walkover": "finished",
        "retired": "finished",
    }
    return status_map.get(api_status.lower(), "scheduled")


def _parse_tennis_result(result_str: Any) -> tuple[int | None, int | None]:
    """Parse a tennis result string like '6-3 7-5' into sets won.

    Returns (sets_p1, sets_p2).
    """
    if not result_str or not isinstance(result_str, str):
        return None, None

    sets_p1 = 0
    sets_p2 = 0
    for set_score in result_str.strip().split():
        parts = set_score.split("-")
        if len(parts) != 2:
            continue
        s1 = _safe_int(parts[0])
        s2 = _safe_int(parts[1])
        if s1 is None or s2 is None:
            continue
        if s1 > s2:
            sets_p1 += 1
        elif s2 > s1:
            sets_p2 += 1

    if sets_p1 == 0 and sets_p2 == 0:
        return None, None
    return sets_p1, sets_p2


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
