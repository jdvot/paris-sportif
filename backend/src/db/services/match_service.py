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
    async def _save_match_in_uow(uow: Any, match_data: dict[str, Any]) -> bool:
        """Save a single match within an existing Unit of Work (no commit).

        Args:
            uow: Active Unit of Work with open session
            match_data: Raw match data from football-data.org API

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            home_team = match_data.get("homeTeam", {})
            away_team = match_data.get("awayTeam", {})
            competition = match_data.get("competition", {})
            score = match_data.get("score", {}) or {}
            full_time = score.get("fullTime", {}) or {}
            half_time = score.get("halfTime", {}) or {}
            odds = match_data.get("odds", {}) or {}

            external_id = f"{competition.get('code')}_{match_data.get('id')}"

            # Extract country from team.area or competition.area
            home_country = home_team.get("area", {}).get("name") or competition.get("area", {}).get(
                "name"
            )
            away_country = away_team.get("area", {}).get("name") or competition.get("area", {}).get(
                "name"
            )

            # Ensure teams exist - include country field
            home_team_obj = await uow.teams.get_by_external_id(str(home_team.get("id")))
            if not home_team_obj:
                home_team_obj = await uow.teams.create(
                    external_id=str(home_team.get("id")),
                    name=home_team.get("name", "Unknown"),
                    short_name=home_team.get("tla") or home_team.get("shortName"),
                    tla=home_team.get("tla"),
                    logo_url=home_team.get("crest"),
                    country=home_country,
                )
            elif not home_team_obj.country and home_country:
                await uow.teams.update(home_team_obj.id, country=home_country)

            away_team_obj = await uow.teams.get_by_external_id(str(away_team.get("id")))
            if not away_team_obj:
                away_team_obj = await uow.teams.create(
                    external_id=str(away_team.get("id")),
                    name=away_team.get("name", "Unknown"),
                    short_name=away_team.get("tla") or away_team.get("shortName"),
                    tla=away_team.get("tla"),
                    logo_url=away_team.get("crest"),
                    country=away_country,
                )
            elif not away_team_obj.country and away_country:
                await uow.teams.update(away_team_obj.id, country=away_country)

            # Parse date
            match_date_str = match_data.get("utcDate")
            match_date = (
                datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
                if match_date_str
                else datetime.now()
            )

            # Build match data with all available fields
            match_fields = {
                "home_team_id": home_team_obj.id,
                "away_team_id": away_team_obj.id,
                "competition_code": competition.get("code", "UNKNOWN"),
                "match_date": match_date,
                "matchday": match_data.get("matchday"),
                "status": match_data.get("status", "scheduled"),
                "home_score": full_time.get("home"),
                "away_score": full_time.get("away"),
            }

            # Add half-time scores if available
            if half_time.get("home") is not None:
                match_fields["home_score_ht"] = half_time.get("home")
            if half_time.get("away") is not None:
                match_fields["away_score_ht"] = half_time.get("away")

            # Add odds if available
            if odds.get("homeWin"):
                match_fields["odds_home"] = odds.get("homeWin")
            if odds.get("draw"):
                match_fields["odds_draw"] = odds.get("draw")
            if odds.get("awayWin"):
                match_fields["odds_away"] = odds.get("awayWin")

            # Upsert match with all fields
            await uow.matches.upsert(
                "external_id",
                external_id,
                **match_fields,
            )
            return True

        except Exception as e:
            logger.error(f"Error saving match: {e}")
            return False

    @staticmethod
    async def save_match(match_data: dict[str, Any]) -> bool:
        """Save a single match to database.

        Args:
            match_data: Raw match data from football-data.org API

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            async with get_uow() as uow:
                result = await MatchService._save_match_in_uow(uow, match_data)
                if result:
                    await uow.commit()
                return result
        except Exception as e:
            logger.error(f"Error saving match: {e}")
            return False

    @staticmethod
    async def save_matches(matches: list[dict[str, Any]]) -> int:
        """Save multiple matches to database in a single transaction.

        Uses a single DB session for all matches instead of one per match.

        Args:
            matches: List of raw match data from API

        Returns:
            Count of successfully saved matches
        """
        saved = 0
        try:
            async with get_uow() as uow:
                for match in matches:
                    if await MatchService._save_match_in_uow(uow, match):
                        saved += 1
                if saved > 0:
                    await uow.commit()
        except Exception as e:
            logger.error(f"Error in batch save_matches: {e}")
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
                    "competition_code": m.competition_code,
                    "matchday": m.matchday,
                    "home_team": {
                        "id": m.home_team_id,
                        "name": m.home_team.name if m.home_team else None,
                        "short_name": (
                            m.home_team.short_name or m.home_team.tla if m.home_team else None
                        ),
                        "logo_url": m.home_team.logo_url if m.home_team else None,
                        "elo_rating": (
                            float(m.home_team.elo_rating)
                            if m.home_team and m.home_team.elo_rating
                            else 1500.0
                        ),
                        "form": m.home_team.form if m.home_team else None,
                    },
                    "away_team": {
                        "id": m.away_team_id,
                        "name": m.away_team.name if m.away_team else None,
                        "short_name": (
                            m.away_team.short_name or m.away_team.tla if m.away_team else None
                        ),
                        "logo_url": m.away_team.logo_url if m.away_team else None,
                        "elo_rating": (
                            float(m.away_team.elo_rating)
                            if m.away_team and m.away_team.elo_rating
                            else 1500.0
                        ),
                        "form": m.away_team.form if m.away_team else None,
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
        """Get scheduled (upcoming) matches with full team data.

        Replaces: src.data.database.get_scheduled_matches_from_db()
        Teams are eager-loaded to avoid N+1 queries.
        """
        async with get_uow() as uow:
            matches = await uow.matches.get_scheduled(
                date_from=date_from,
                date_to=date_to,
                competition_code=competition,
            )
            return [
                {
                    "id": m.id,
                    "external_id": m.external_id,
                    "competition_code": m.competition_code,
                    "matchday": m.matchday,
                    "home_team": {
                        "id": m.home_team_id,
                        "name": m.home_team.name if m.home_team else "Unknown",
                        "short_name": (
                            m.home_team.short_name or m.home_team.tla if m.home_team else "UNK"
                        ),
                        "logo_url": m.home_team.logo_url if m.home_team else None,
                        "elo_rating": (
                            float(m.home_team.elo_rating)
                            if m.home_team and m.home_team.elo_rating
                            else 1500.0
                        ),
                        "form": m.home_team.form if m.home_team else None,
                    },
                    "away_team": {
                        "id": m.away_team_id,
                        "name": m.away_team.name if m.away_team else "Unknown",
                        "short_name": (
                            m.away_team.short_name or m.away_team.tla if m.away_team else "UNK"
                        ),
                        "logo_url": m.away_team.logo_url if m.away_team else None,
                        "elo_rating": (
                            float(m.away_team.elo_rating)
                            if m.away_team and m.away_team.elo_rating
                            else 1500.0
                        ),
                        "form": m.away_team.form if m.away_team else None,
                    },
                    "match_date": m.match_date.isoformat() if m.match_date else None,
                    "status": m.status,
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                }
                for m in matches
            ]

    @staticmethod
    async def get_match_by_api_id(api_match_id: int) -> dict[str, Any] | None:
        """Get a single match by football-data.org API match ID.

        Args:
            api_match_id: The match ID from football-data.org API

        Returns:
            Match data dictionary or None if not found
        """
        async with get_uow() as uow:
            match = await uow.matches.get_by_api_match_id(api_match_id)
            if not match:
                return None

            return {
                "id": match.id,
                "external_id": match.external_id,
                "competition_code": match.competition_code,
                "matchday": match.matchday,
                "home_team": {
                    "id": match.home_team_id,
                    "name": match.home_team.name if match.home_team else "Unknown",
                    "short_name": (
                        match.home_team.short_name or match.home_team.tla
                        if match.home_team
                        else "UNK"
                    ),
                    "logo_url": match.home_team.logo_url if match.home_team else None,
                    "elo_rating": (
                        float(match.home_team.elo_rating)
                        if match.home_team and match.home_team.elo_rating
                        else 1500.0
                    ),
                    "form": match.home_team.form if match.home_team else None,
                },
                "away_team": {
                    "id": match.away_team_id,
                    "name": match.away_team.name if match.away_team else "Unknown",
                    "short_name": (
                        match.away_team.short_name or match.away_team.tla
                        if match.away_team
                        else "UNK"
                    ),
                    "logo_url": match.away_team.logo_url if match.away_team else None,
                    "elo_rating": (
                        float(match.away_team.elo_rating)
                        if match.away_team and match.away_team.elo_rating
                        else 1500.0
                    ),
                    "form": match.away_team.form if match.away_team else None,
                },
                "match_date": match.match_date.isoformat() if match.match_date else None,
                "status": match.status,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "home_score_ht": match.home_score_ht,
                "away_score_ht": match.away_score_ht,
                "odds_home": float(match.odds_home) if match.odds_home else None,
                "odds_draw": float(match.odds_draw) if match.odds_draw else None,
                "odds_away": float(match.odds_away) if match.odds_away else None,
            }

    @staticmethod
    async def get_head_to_head_from_db(
        home_team_id: int,
        away_team_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get head-to-head matches from database.

        Args:
            home_team_id: Internal DB ID of home team
            away_team_id: Internal DB ID of away team
            limit: Max number of matches to return

        Returns:
            List of head-to-head match data
        """
        async with get_uow() as uow:
            matches = await uow.matches.get_head_to_head(home_team_id, away_team_id, limit=limit)
            return [
                {
                    "date": m.match_date.isoformat() if m.match_date else None,
                    "home_team": m.home_team.name if m.home_team else "Unknown",
                    "away_team": m.away_team.name if m.away_team else "Unknown",
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                    "competition": m.competition_code,
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
