"""Database module for storing football data locally.

Uses SQLite for persistent storage of matches and standings.
This reduces API calls and provides faster responses.
"""

import sqlite3
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path(__file__).parent / "football_data.db"


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session():
    """Context manager for database sessions."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database schema."""
    with db_session() as conn:
        cursor = conn.cursor()

        # Matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY,
                external_id TEXT UNIQUE,
                home_team_id INTEGER,
                home_team_name TEXT,
                home_team_short TEXT,
                home_team_logo TEXT,
                away_team_id INTEGER,
                away_team_name TEXT,
                away_team_short TEXT,
                away_team_logo TEXT,
                competition_code TEXT,
                competition_name TEXT,
                match_date TEXT,
                status TEXT,
                matchday INTEGER,
                home_score INTEGER,
                away_score INTEGER,
                raw_data TEXT,
                synced_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Standings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_code TEXT,
                position INTEGER,
                team_id INTEGER,
                team_name TEXT,
                team_logo TEXT,
                played INTEGER,
                won INTEGER,
                drawn INTEGER,
                lost INTEGER,
                goals_for INTEGER,
                goals_against INTEGER,
                goal_difference INTEGER,
                points INTEGER,
                synced_at TEXT,
                UNIQUE(competition_code, team_id)
            )
        """)

        # Sync log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT,
                status TEXT,
                records_synced INTEGER,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_competition ON standings(competition_code)")

        logger.info("Database initialized successfully")


def save_match(match_data: dict) -> bool:
    """Save a single match to database."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            home_team = match_data.get("homeTeam", {})
            away_team = match_data.get("awayTeam", {})
            competition = match_data.get("competition", {})
            score = match_data.get("score", {}) or {}
            full_time = score.get("fullTime", {}) or {}

            cursor.execute("""
                INSERT OR REPLACE INTO matches (
                    id, external_id,
                    home_team_id, home_team_name, home_team_short, home_team_logo,
                    away_team_id, away_team_name, away_team_short, away_team_logo,
                    competition_code, competition_name, match_date, status, matchday,
                    home_score, away_score, raw_data, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_data.get("id"),
                f"{competition.get('code')}_{match_data.get('id')}",
                home_team.get("id"),
                home_team.get("name"),
                home_team.get("tla") or home_team.get("shortName"),
                home_team.get("crest"),
                away_team.get("id"),
                away_team.get("name"),
                away_team.get("tla") or away_team.get("shortName"),
                away_team.get("crest"),
                competition.get("code"),
                competition.get("name"),
                match_data.get("utcDate"),
                match_data.get("status"),
                match_data.get("matchday"),
                full_time.get("home"),
                full_time.get("away"),
                json.dumps(match_data),
                datetime.now().isoformat()
            ))

            return True
    except Exception as e:
        logger.error(f"Error saving match: {e}")
        return False


def save_matches(matches: list[dict]) -> int:
    """Save multiple matches to database. Returns count of saved matches."""
    saved = 0
    for match in matches:
        if save_match(match):
            saved += 1
    logger.info(f"Saved {saved}/{len(matches)} matches to database")
    return saved


def get_matches_from_db(
    date_from: date | None = None,
    date_to: date | None = None,
    competition: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Get matches from database."""
    with db_session() as conn:
        cursor = conn.cursor()

        query = "SELECT raw_data FROM matches WHERE 1=1"
        params = []

        if date_from:
            query += " AND DATE(match_date) >= ?"
            params.append(date_from.isoformat())
        if date_to:
            query += " AND DATE(match_date) <= ?"
            params.append(date_to.isoformat())
        if competition:
            query += " AND competition_code = ?"
            params.append(competition)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY match_date ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [json.loads(row["raw_data"]) for row in rows]


def save_standings(competition_code: str, standings: list[dict]) -> int:
    """Save standings for a competition."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Delete old standings for this competition
            cursor.execute("DELETE FROM standings WHERE competition_code = ?", (competition_code,))

            synced_at = datetime.now().isoformat()
            saved = 0

            for standing in standings:
                team = standing.get("team", {})
                cursor.execute("""
                    INSERT INTO standings (
                        competition_code, position, team_id, team_name, team_logo,
                        played, won, drawn, lost, goals_for, goals_against,
                        goal_difference, points, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    competition_code,
                    standing.get("position"),
                    team.get("id"),
                    team.get("name"),
                    team.get("crest"),
                    standing.get("playedGames"),
                    standing.get("won"),
                    standing.get("draw"),
                    standing.get("lost"),
                    standing.get("goalsFor"),
                    standing.get("goalsAgainst"),
                    standing.get("goalDifference"),
                    standing.get("points"),
                    synced_at
                ))
                saved += 1

            logger.info(f"Saved {saved} standings for {competition_code}")
            return saved
    except Exception as e:
        logger.error(f"Error saving standings: {e}")
        return 0


def get_standings_from_db(competition_code: str) -> list[dict]:
    """Get standings from database."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM standings
            WHERE competition_code = ?
            ORDER BY position ASC
        """, (competition_code,))

        rows = cursor.fetchall()

        return [{
            "position": row["position"],
            "team": {
                "id": row["team_id"],
                "name": row["team_name"],
                "crest": row["team_logo"],
            },
            "playedGames": row["played"],
            "won": row["won"],
            "draw": row["drawn"],
            "lost": row["lost"],
            "goalsFor": row["goals_for"],
            "goalsAgainst": row["goals_against"],
            "goalDifference": row["goal_difference"],
            "points": row["points"],
        } for row in rows]


def log_sync(sync_type: str, status: str, records: int, error: str | None = None):
    """Log a sync operation."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_log (sync_type, status, records_synced, started_at, completed_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sync_type,
            status,
            records,
            datetime.now().isoformat(),
            datetime.now().isoformat() if status != "running" else None,
            error
        ))


def get_last_sync(sync_type: str) -> dict | None:
    """Get last sync info for a sync type."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sync_log
            WHERE sync_type = ? AND status = 'success'
            ORDER BY completed_at DESC LIMIT 1
        """, (sync_type,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_db_stats() -> dict:
    """Get database statistics."""
    with db_session() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM matches")
        match_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(DISTINCT competition_code) as count FROM standings")
        standings_count = cursor.fetchone()["count"]

        cursor.execute("SELECT MAX(synced_at) as last_sync FROM matches")
        last_match_sync = cursor.fetchone()["last_sync"]

        cursor.execute("SELECT MAX(synced_at) as last_sync FROM standings")
        last_standings_sync = cursor.fetchone()["last_sync"]

        return {
            "total_matches": match_count,
            "competitions_with_standings": standings_count,
            "last_match_sync": last_match_sync,
            "last_standings_sync": last_standings_sync,
        }


# Initialize database on import
init_database()
