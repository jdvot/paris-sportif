"""NBA data sync service.

Fetches NBA games, teams, and standings from API-Sports,
generates predictions, and stores everything in the database.
"""

import asyncio
import json
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
        await _mark_daily_picks_nba()
        await _generate_daily_summary_nba()

        total = teams_synced + standings_synced + games_synced + odds_synced + predictions_generated

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
    """Generate ensemble predictions + LLM explanations for scheduled NBA games."""
    from src.prediction_engine.basketball_ensemble import predict_nba_ensemble

    count = 0
    async with _get_session() as session:
        result = await session.execute(
            text(
                """
                SELECT m.id, m.is_back_to_back_home, m.is_back_to_back_away,
                       m.odds_home, m.odds_away,
                       ht.name as home_name, ht.elo_rating as home_elo,
                       ht.offensive_rating as home_off,
                       ht.defensive_rating as home_def, ht.pace as home_pace,
                       ht.win_rate_ytd as home_wr,
                       at.name as away_name, at.elo_rating as away_elo,
                       at.offensive_rating as away_off,
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
            home_elo = float(row.home_elo or 1500)
            away_elo = float(row.away_elo or 1500)
            home_off = float(row.home_off) if row.home_off else None
            home_def = float(row.home_def) if row.home_def else None
            away_off = float(row.away_off) if row.away_off else None
            away_def = float(row.away_def) if row.away_def else None
            home_pace = float(row.home_pace) if row.home_pace else None
            away_pace = float(row.away_pace) if row.away_pace else None
            b2b_home = bool(row.is_back_to_back_home)
            b2b_away = bool(row.is_back_to_back_away)
            home_wr = float(row.home_wr or 50) / 100.0
            away_wr = float(row.away_wr or 50) / 100.0

            pred = predict_nba_ensemble(
                home_elo=home_elo,
                away_elo=away_elo,
                home_off_rating=home_off,
                home_def_rating=home_def,
                away_off_rating=away_off,
                away_def_rating=away_def,
                home_pace=home_pace,
                away_pace=away_pace,
                is_back_to_back_home=b2b_home,
                is_back_to_back_away=b2b_away,
                home_win_rate=home_wr,
                away_win_rate=away_wr,
                odds_home=float(row.odds_home) if row.odds_home else None,
                odds_away=float(row.odds_away) if row.odds_away else None,
            )

            # LLM explanation (None if unavailable — NEVER fallback)
            explanation = await _generate_llm_explanation_nba(
                home_name=row.home_name or "Home",
                away_name=row.away_name or "Away",
                home_prob=pred.home_prob,
                away_prob=pred.away_prob,
                confidence=pred.confidence,
                home_elo=home_elo,
                away_elo=away_elo,
                home_off=home_off,
                home_def=home_def,
                away_off=away_off,
                away_def=away_def,
                home_pace=home_pace,
                away_pace=away_pace,
                home_wr=home_wr,
                away_wr=away_wr,
                b2b_home=b2b_home,
                b2b_away=b2b_away,
                exp_home=pred.expected_home_score,
                exp_away=pred.expected_away_score,
                model_agreement=pred.model_agreement,
                uncertainty=pred.uncertainty,
            )

            await session.execute(
                text(
                    """
                    UPDATE basketball_matches SET
                        pred_home_prob = :hp, pred_away_prob = :ap,
                        pred_confidence = :conf, pred_explanation = :expl,
                        model_details = :details,
                        updated_at = NOW()
                    WHERE id = :mid
                """
                ),
                {
                    "hp": pred.home_prob,
                    "ap": pred.away_prob,
                    "conf": pred.confidence,
                    "expl": explanation,
                    "details": json.dumps(pred.model_details),
                    "mid": row.id,
                },
            )
            count += 1

        await session.commit()

    logger.info(f"[NBA Sync] Generated {count} predictions")
    return count


async def _generate_llm_explanation_nba(
    home_name: str,
    away_name: str,
    home_prob: float,
    away_prob: float,
    confidence: float,
    home_elo: float,
    away_elo: float,
    home_off: float | None,
    home_def: float | None,
    away_off: float | None,
    away_def: float | None,
    home_pace: float | None,
    away_pace: float | None,
    home_wr: float,
    away_wr: float,
    b2b_home: bool,
    b2b_away: bool,
    exp_home: float,
    exp_away: float,
    model_agreement: float,
    uncertainty: float,
) -> str | None:
    """Generate LLM explanation for an NBA game. Returns None if LLM unavailable."""
    try:
        from src.llm.client import get_llm_client
        from src.llm.prompts import NBA_MATCH_EXPLANATION_PROMPT, SYSTEM_NBA_ANALYST

        llm = get_llm_client()
        prompt = NBA_MATCH_EXPLANATION_PROMPT.format(
            home_team=home_name,
            away_team=away_name,
            home_prob=f"{home_prob * 100:.0f}",
            away_prob=f"{away_prob * 100:.0f}",
            exp_home=exp_home,
            exp_away=exp_away,
            confidence=f"{confidence * 100:.0f}",
            home_elo=home_elo,
            away_elo=away_elo,
            home_off=f"{home_off:.1f}" if home_off else "N/A",
            home_def=f"{home_def:.1f}" if home_def else "N/A",
            away_off=f"{away_off:.1f}" if away_off else "N/A",
            away_def=f"{away_def:.1f}" if away_def else "N/A",
            home_pace=f"{home_pace:.1f}" if home_pace else "N/A",
            away_pace=f"{away_pace:.1f}" if away_pace else "N/A",
            home_wr=home_wr,
            away_wr=away_wr,
            b2b_home="oui" if b2b_home else "non",
            b2b_away="oui" if b2b_away else "non",
            model_agreement=model_agreement,
            uncertainty=uncertainty,
        )

        result = await llm.complete(
            prompt=prompt,
            system=SYSTEM_NBA_ANALYST,
            max_tokens=200,
            temperature=0.3,
        )
        return result.strip() if result else None

    except Exception as e:
        logger.warning(f"NBA LLM explanation failed: {e}")
        return None


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


async def _mark_daily_picks_nba() -> int:
    """Mark top 3 NBA predictions as daily picks by confidence × value_score."""
    today = date.today()

    async with _get_session() as session:
        # Reset existing NBA daily picks
        await session.execute(
            text(
                """
                UPDATE basketball_matches SET
                    is_daily_pick = FALSE, pick_rank = NULL
                WHERE is_daily_pick = TRUE
                  AND match_date::date >= :today
            """
            ),
            {"today": today},
        )

        # Get predictions with confidence
        result = await session.execute(
            text(
                """
                SELECT id, pred_confidence, model_details
                FROM basketball_matches
                WHERE status = 'scheduled'
                  AND pred_confidence IS NOT NULL
                  AND match_date::date >= :today
                  AND match_date::date <= :tomorrow
            """
            ),
            {"today": today, "tomorrow": today + timedelta(days=1)},
        )
        rows = result.fetchall()

        scored: list[dict[str, Any]] = []
        for row in rows:
            conf = float(row.pred_confidence or 0)
            details = row.model_details
            if isinstance(details, str):
                details = json.loads(details)
            elif not isinstance(details, dict):
                details = {}
            vs = abs(conf - 0.5) * 2.0  # Simple value proxy
            scored.append({"id": row.id, "score": conf * vs})

        scored.sort(key=lambda x: x["score"], reverse=True)

        marked = 0
        for rank, pick in enumerate(scored[:3], start=1):
            await session.execute(
                text(
                    """
                    UPDATE basketball_matches SET
                        is_daily_pick = TRUE, pick_rank = :rank, updated_at = NOW()
                    WHERE id = :mid
                """
                ),
                {"rank": rank, "mid": pick["id"]},
            )
            marked += 1

        await session.commit()

    logger.info(f"[NBA Sync] Marked {marked} daily picks")
    return marked


async def _generate_daily_summary_nba() -> str:
    """Generate editorial daily NBA picks summary via LLM. Returns '' if unavailable."""
    try:
        from src.llm.client import get_llm_client
        from src.llm.prompts import NBA_DAILY_PICKS_PROMPT, SYSTEM_NBA_ANALYST

        async with _get_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT m.pred_confidence, m.pred_home_prob, m.pred_away_prob,
                           m.pred_explanation, m.pick_rank,
                           ht.name as home_name, at.name as away_name
                    FROM basketball_matches m
                    JOIN basketball_teams ht ON m.home_team_id = ht.id
                    JOIN basketball_teams at ON m.away_team_id = at.id
                    WHERE m.is_daily_pick = TRUE
                      AND m.match_date::date >= CURRENT_DATE
                    ORDER BY m.pick_rank
                    LIMIT 3
                """
                )
            )
            picks = result.fetchall()

        if not picks:
            return ""

        parts: list[str] = []
        for p in picks:
            home_prob = float(p.pred_home_prob or 0.5)
            away_prob = float(p.pred_away_prob or 0.5)
            favored = p.home_name if home_prob >= away_prob else p.away_name
            parts.append(
                f"#{p.pick_rank}: {p.home_name} vs {p.away_name}\n"
                f"  Pronostic: Victoire {favored} | "
                f"Confiance: {float(p.pred_confidence or 0):.0%}\n"
                f"  {(p.pred_explanation or '')[:150]}"
            )

        picks_data = "\n\n".join(parts)
        prompt = NBA_DAILY_PICKS_PROMPT.format(picks_data=picks_data)

        llm = get_llm_client()
        analysis = await llm.analyze_json(
            prompt=prompt,
            system_prompt=SYSTEM_NBA_ANALYST,
            temperature=0.5,
        )

        if analysis and isinstance(analysis, dict):
            summary = str(analysis.get("daily_summary", ""))
            logger.info(f"[NBA] Daily summary: {len(summary)} chars")

            try:
                from src.core.cache import cache_set

                await cache_set(
                    "nba_daily_picks_summary",
                    json.dumps(analysis, ensure_ascii=False),
                    ttl=86400,
                )
            except Exception as ce:
                logger.warning(f"Failed to cache NBA daily summary: {ce}")

            return summary

    except Exception as e:
        logger.warning(f"NBA daily summary failed: {e}")

    return ""
