"""Match service providing high-level match operations.

This service replaces the legacy database.py functions with
repository-based implementations.

Migration mapping:
- save_match() -> MatchService.save_match()
- save_matches() -> MatchService.save_matches()
- get_matches_from_db() -> MatchService.get_matches()
- get_scheduled_matches_from_db() -> MatchService.get_scheduled()
"""

import logging
from datetime import date, datetime
from typing import Any

from src.db.repositories import get_uow

logger = logging.getLogger(__name__)


class MatchService:
    """Service for match-related operations."""

    @staticmethod
    async def save_match(match_data: dict[str, Any]) -> bool:
        """Save a single match to database.

        Replaces: src.data.database.save_match()

        Args:
            match_data: Raw match data from football-data.org API

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            async with get_uow() as uow:
                home_team = match_data.get("homeTeam", {})
                away_team = match_data.get("awayTeam", {})
                competition = match_data.get("competition", {})
                score = match_data.get("score", {}) or {}
                full_time = score.get("fullTime", {}) or {}

                external_id = f"{competition.get('code')}_{match_data.get('id')}"

                # Ensure teams exist
                home_team_obj = await uow.teams.get_by_external_id(str(home_team.get("id")))
                if not home_team_obj:
                    home_team_obj = await uow.teams.create(
                        external_id=str(home_team.get("id")),
                        name=home_team.get("name", "Unknown"),
                        short_name=home_team.get("tla") or home_team.get("shortName"),
                        tla=home_team.get("tla"),
                        logo_url=home_team.get("crest"),
                    )

                away_team_obj = await uow.teams.get_by_external_id(str(away_team.get("id")))
                if not away_team_obj:
                    away_team_obj = await uow.teams.create(
                        external_id=str(away_team.get("id")),
                        name=away_team.get("name", "Unknown"),
                        short_name=away_team.get("tla") or away_team.get("shortName"),
                        tla=away_team.get("tla"),
                        logo_url=away_team.get("crest"),
                    )

                # Parse date
                match_date_str = match_data.get("utcDate")
                match_date = (
                    datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
                    if match_date_str
                    else datetime.now()
                )

                # Upsert match
                await uow.matches.upsert(
                    "external_id",
                    external_id,
                    home_team_id=home_team_obj.id,
                    away_team_id=away_team_obj.id,
                    competition_code=match_data.get("competition", {}).get("code", "UNKNOWN"),
                    match_date=match_date,
                    matchday=match_data.get("matchday"),
                    status=match_data.get("status", "scheduled"),
                    home_score=full_time.get("home"),
                    away_score=full_time.get("away"),
                )

                await uow.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving match: {e}")
            return False

    @staticmethod
    async def save_matches(matches: list[dict[str, Any]]) -> int:
        """Save multiple matches to database.

        Replaces: src.data.database.save_matches()

        Args:
            matches: List of raw match data from API

        Returns:
            Count of successfully saved matches
        """
        saved = 0
        for match in matches:
            if await MatchService.save_match(match):
                saved += 1
        logger.info(f"Saved {saved}/{len(matches)} matches to database")
        return saved

    @staticmethod
    async def get_matches(
        date_from: date | None = None,
        date_to: date | None = None,
        competition: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get matches from database.

        Replaces: src.data.database.get_matches_from_db()

        Args:
            date_from: Start date filter
            date_to: End date filter
            competition: Competition code filter
            status: Match status filter

        Returns:
            List of match data dictionaries
        """
        async with get_uow() as uow:
            if date_from and date_to:
                matches = await uow.matches.get_by_date_range(
                    date_from,
                    date_to,
                    status=status,
                )
            else:
                matches = await uow.matches.get_all(limit=500)

            return [
                {
                    "id": m.id,
                    "external_id": m.external_id,
                    "home_team": {
                        "id": m.home_team_id,
                        "name": m.home_team.name if m.home_team else None,
                    },
                    "away_team": {
                        "id": m.away_team_id,
                        "name": m.away_team.name if m.away_team else None,
                    },
                    "match_date": m.match_date.isoformat() if m.match_date else None,
                    "status": m.status,
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                }
                for m in matches
            ]

    @staticmethod
    async def get_scheduled(
        date_from: date | None = None,
        date_to: date | None = None,
        competition: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get scheduled (upcoming) matches.

        Replaces: src.data.database.get_scheduled_matches_from_db()
        """
        async with get_uow() as uow:
            matches = await uow.matches.get_scheduled(
                date_from=date_from,
                date_to=date_to,
            )
            return [
                {
                    "id": m.id,
                    "external_id": m.external_id,
                    "home_team_id": m.home_team_id,
                    "away_team_id": m.away_team_id,
                    "match_date": m.match_date.isoformat() if m.match_date else None,
                    "status": m.status,
                }
                for m in matches
            ]


class StandingService:
    """Service for standing-related operations."""

    @staticmethod
    async def save_standings(
        competition_code: str,
        standings: list[dict[str, Any]],
    ) -> int:
        """Save standings for a competition.

        Replaces: src.data.database.save_standings()
        """
        try:
            async with get_uow() as uow:
                standings_data = []
                for standing in standings:
                    team = standing.get("team", {})
                    standings_data.append(
                        {
                            "position": standing.get("position"),
                            "team_id": team.get("id"),
                            "team_name": team.get("name"),
                            "team_logo": team.get("crest"),
                            "played_games": standing.get("playedGames"),
                            "won": standing.get("won"),
                            "drawn": standing.get("draw"),
                            "lost": standing.get("lost"),
                            "goals_for": standing.get("goalsFor"),
                            "goals_against": standing.get("goalsAgainst"),
                            "goal_difference": standing.get("goalDifference"),
                            "points": standing.get("points"),
                        }
                    )

                count = await uow.standings.replace_competition_standings(
                    competition_code,
                    standings_data,
                )
                await uow.commit()
                logger.info(f"Saved {count} standings for {competition_code}")
                return count

        except Exception as e:
            logger.error(f"Error saving standings: {e}")
            return 0

    @staticmethod
    async def get_standings(competition_code: str) -> list[dict[str, Any]]:
        """Get standings from database.

        Replaces: src.data.database.get_standings_from_db()
        """
        async with get_uow() as uow:
            standings = await uow.standings.get_by_competition(competition_code)
            return [
                {
                    "position": s.position,
                    "team": {
                        "id": s.team_id,
                        "name": s.team_name,
                        "crest": s.team_logo,
                    },
                    "playedGames": s.played_games,
                    "won": s.won,
                    "draw": s.drawn,
                    "lost": s.lost,
                    "goalsFor": s.goals_for,
                    "goalsAgainst": s.goals_against,
                    "goalDifference": s.goal_difference,
                    "points": s.points,
                }
                for s in standings
            ]


class SyncService:
    """Service for sync log operations."""

    @staticmethod
    async def log_sync(
        sync_type: str,
        status: str,
        records: int,
        error: str | None = None,
    ) -> None:
        """Log a sync operation.

        Replaces: src.data.database.log_sync()
        """
        async with get_uow() as uow:
            if status == "running":
                await uow.sync_logs.start_sync(sync_type)
            elif status == "success":
                # Get the running sync and complete it
                running = await uow.sync_logs.get_last_successful_sync(sync_type)
                if running:
                    await uow.sync_logs.complete_sync(running, records)
            elif status == "failed" and error:
                running_syncs = await uow.sync_logs.get_running_syncs()
                for sync in running_syncs:
                    if sync.sync_type == sync_type:
                        await uow.sync_logs.fail_sync(sync, error)
                        break
            await uow.commit()

    @staticmethod
    async def get_last_sync(sync_type: str) -> dict[str, Any] | None:
        """Get last sync info.

        Replaces: src.data.database.get_last_sync()
        """
        async with get_uow() as uow:
            sync = await uow.sync_logs.get_last_successful_sync(sync_type)
            if not sync:
                return None
            return {
                "id": sync.id,
                "sync_type": sync.sync_type,
                "status": sync.status,
                "records_synced": sync.records_synced,
                "started_at": sync.started_at.isoformat() if sync.started_at else None,
                "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
            }
