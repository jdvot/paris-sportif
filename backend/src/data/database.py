"""Database module for storing football data.

Uses PostgreSQL in production (via DATABASE_URL) or SQLite locally.
This reduces API calls and provides faster responses.
"""

import json
import logging
import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check if we're using PostgreSQL (production) or SQLite (local)
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith("postgres")

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras

        logger.info("Using PostgreSQL database")
    except ImportError:
        logger.warning("psycopg2 not installed, falling back to SQLite")
        USE_POSTGRES = False

# SQLite database file path (for local development)
DB_PATH = Path(__file__).parent / "football_data.db"


def get_db_connection() -> Any:
    """Get database connection (PostgreSQL or SQLite)."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn


def dict_row_factory(cursor: Any) -> list[dict[str, Any]]:
    """Convert PostgreSQL rows to dict-like objects."""
    if USE_POSTGRES:
        columns = [col.name for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    return cursor.fetchall()  # type: ignore[no-any-return]


def get_placeholder() -> str:
    """Get the correct SQL placeholder for the database type."""
    return "%s" if USE_POSTGRES else "?"


def adapt_query(query: str) -> str:
    """Convert SQLite query to PostgreSQL if needed."""
    if USE_POSTGRES:
        # Replace ? with %s for PostgreSQL
        return query.replace("?", "%s")
    return query


def fetch_one_dict(cursor: Any) -> dict[str, Any] | None:
    """Fetch one row as a dictionary."""
    row = cursor.fetchone()
    if row is None:
        return None
    if USE_POSTGRES:
        columns = [col.name for col in cursor.description]
        return dict(zip(columns, row))
    return dict(row)


def fetch_all_dict(cursor: Any) -> list[dict[str, Any]]:
    """Fetch all rows as dictionaries."""
    rows = cursor.fetchall()
    if USE_POSTGRES:
        if not rows:
            return []
        columns = [col.name for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    return [dict(row) for row in rows]


@contextmanager
def db_session() -> Generator[Any, None, None]:
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


def init_database() -> None:
    """Initialize database schema (PostgreSQL or SQLite)."""
    with db_session() as conn:
        cursor = conn.cursor()

        if USE_POSTGRES:
            # PostgreSQL schema
            cursor.execute(
                """
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
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS standings (
                    id SERIAL PRIMARY KEY,
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
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_log (
                    id SERIAL PRIMARY KEY,
                    sync_type TEXT,
                    status TEXT,
                    records_synced INTEGER,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER UNIQUE,
                    match_external_id TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    competition_code TEXT,
                    match_date TEXT,
                    home_win_prob REAL,
                    draw_prob REAL,
                    away_win_prob REAL,
                    predicted_home_goals REAL,
                    predicted_away_goals REAL,
                    confidence REAL,
                    recommendation TEXT,
                    explanation TEXT,
                    model_version TEXT,
                    actual_home_score INTEGER,
                    actual_away_score INTEGER,
                    actual_result TEXT,
                    was_correct INTEGER,
                    verified_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ml_models (
                    id SERIAL PRIMARY KEY,
                    model_name TEXT UNIQUE,
                    model_type TEXT,
                    version TEXT,
                    accuracy REAL,
                    training_samples INTEGER,
                    feature_columns TEXT,
                    model_binary BYTEA,
                    scaler_binary BYTEA,
                    trained_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            logger.info("PostgreSQL database initialized")

        else:
            # SQLite schema
            cursor.execute(
                """
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
            """
            )

            cursor.execute(
                """
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
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT,
                    status TEXT,
                    records_synced INTEGER,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER,
                    match_external_id TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    competition_code TEXT,
                    match_date TEXT,
                    home_win_prob REAL,
                    draw_prob REAL,
                    away_win_prob REAL,
                    predicted_home_goals REAL,
                    predicted_away_goals REAL,
                    confidence REAL,
                    recommendation TEXT,
                    explanation TEXT,
                    model_version TEXT,
                    actual_home_score INTEGER,
                    actual_away_score INTEGER,
                    actual_result TEXT,
                    was_correct INTEGER,
                    verified_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(match_id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ml_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT UNIQUE,
                    model_type TEXT,
                    version TEXT,
                    accuracy REAL,
                    training_samples INTEGER,
                    feature_columns TEXT,
                    model_binary BLOB,
                    scaler_binary BLOB,
                    trained_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition_code)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_standings_competition ON standings(competition_code)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(match_date)")

        logger.info("Database initialized successfully")


def save_match(match_data: dict[str, Any]) -> bool:
    """Save a single match to database."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            home_team = match_data.get("homeTeam", {})
            away_team = match_data.get("awayTeam", {})
            competition = match_data.get("competition", {})
            score = match_data.get("score", {}) or {}
            full_time = score.get("fullTime", {}) or {}

            values = (
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
                datetime.now().isoformat(),
            )

            if USE_POSTGRES:
                cursor.execute(
                    """
                    INSERT INTO matches (
                        id, external_id,
                        home_team_id, home_team_name, home_team_short, home_team_logo,
                        away_team_id, away_team_name, away_team_short, away_team_logo,
                        competition_code, competition_name, match_date, status, matchday,
                        home_score, away_score, raw_data, synced_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        raw_data = EXCLUDED.raw_data,
                        synced_at = EXCLUDED.synced_at
                """,
                    values,
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO matches (
                        id, external_id,
                        home_team_id, home_team_name, home_team_short, home_team_logo,
                        away_team_id, away_team_name, away_team_short, away_team_logo,
                        competition_code, competition_name, match_date, status, matchday,
                        home_score, away_score, raw_data, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values,
                )

            return True
    except Exception as e:
        logger.error(f"Error saving match: {e}")
        return False


def save_matches(matches: list[dict[str, Any]]) -> int:
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
) -> list[dict[str, Any]]:
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


def save_standings(competition_code: str, standings: list[dict[str, Any]]) -> int:
    """Save standings for a competition."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Delete old standings for this competition
            del_query = adapt_query("DELETE FROM standings WHERE competition_code = ?")
            cursor.execute(del_query, (competition_code,))

            synced_at = datetime.now().isoformat()
            saved = 0

            insert_query = adapt_query(
                """
                INSERT INTO standings (
                    competition_code, position, team_id, team_name, team_logo,
                    played, won, drawn, lost, goals_for, goals_against,
                    goal_difference, points, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            )

            for standing in standings:
                team = standing.get("team", {})
                cursor.execute(
                    insert_query,
                    (
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
                        synced_at,
                    ),
                )
                saved += 1

            logger.info(f"Saved {saved} standings for {competition_code}")
            return saved
    except Exception as e:
        logger.error(f"Error saving standings: {e}")
        return 0


def get_standings_from_db(competition_code: str) -> list[dict[str, Any]]:
    """Get standings from database."""
    with db_session() as conn:
        cursor = conn.cursor()
        query = adapt_query(
            """
            SELECT * FROM standings
            WHERE competition_code = ?
            ORDER BY position ASC
        """
        )
        cursor.execute(query, (competition_code,))

        rows = fetch_all_dict(cursor)

        return [
            {
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
            }
            for row in rows
        ]


def log_sync(sync_type: str, status: str, records: int, error: str | None = None) -> None:
    """Log a sync operation."""
    with db_session() as conn:
        cursor = conn.cursor()
        query = adapt_query(
            """
            INSERT INTO sync_log (sync_type, status, records_synced, started_at, completed_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        )
        cursor.execute(
            query,
            (
                sync_type,
                status,
                records,
                datetime.now().isoformat(),
                datetime.now().isoformat() if status != "running" else None,
                error,
            ),
        )


def get_last_sync(sync_type: str) -> dict[str, Any] | None:
    """Get last sync info for a sync type."""
    with db_session() as conn:
        cursor = conn.cursor()
        query = adapt_query(
            """
            SELECT * FROM sync_log
            WHERE sync_type = ? AND status = 'success'
            ORDER BY completed_at DESC LIMIT 1
        """
        )
        cursor.execute(query, (sync_type,))

        return fetch_one_dict(cursor)


def get_db_stats() -> dict[str, Any]:
    """Get database statistics."""
    with db_session() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM matches")
        row = fetch_one_dict(cursor)
        match_count = row["count"] if row else 0

        cursor.execute("SELECT COUNT(DISTINCT competition_code) as count FROM standings")
        row = fetch_one_dict(cursor)
        standings_count = row["count"] if row else 0

        cursor.execute("SELECT MAX(synced_at) as last_sync FROM matches")
        row = fetch_one_dict(cursor)
        last_match_sync = row["last_sync"] if row else None

        cursor.execute("SELECT MAX(synced_at) as last_sync FROM standings")
        row = fetch_one_dict(cursor)
        last_standings_sync = row["last_sync"] if row else None

        return {
            "total_matches": match_count,
            "competitions_with_standings": standings_count,
            "last_match_sync": last_match_sync,
            "last_standings_sync": last_standings_sync,
        }


# ============== PREDICTIONS ==============


def save_prediction(prediction: dict[str, Any]) -> bool:
    """Save a prediction to database."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            values = (
                prediction.get("match_id"),
                prediction.get("match_external_id"),
                prediction.get("home_team"),
                prediction.get("away_team"),
                prediction.get("competition_code"),
                prediction.get("match_date"),
                prediction.get("home_win_prob"),
                prediction.get("draw_prob"),
                prediction.get("away_win_prob"),
                prediction.get("predicted_home_goals"),
                prediction.get("predicted_away_goals"),
                prediction.get("confidence"),
                prediction.get("recommendation"),
                prediction.get("explanation"),
                prediction.get("model_version", "v1"),
                datetime.now().isoformat(),
            )

            if USE_POSTGRES:
                cursor.execute(
                    """
                    INSERT INTO predictions (
                        match_id, match_external_id, home_team, away_team,
                        competition_code, match_date, home_win_prob, draw_prob,
                        away_win_prob, predicted_home_goals, predicted_away_goals,
                        confidence, recommendation, explanation, model_version, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_win_prob = EXCLUDED.home_win_prob,
                        draw_prob = EXCLUDED.draw_prob,
                        away_win_prob = EXCLUDED.away_win_prob,
                        confidence = EXCLUDED.confidence,
                        recommendation = EXCLUDED.recommendation,
                        explanation = EXCLUDED.explanation,
                        created_at = EXCLUDED.created_at
                """,
                    values,
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO predictions (
                        match_id, match_external_id, home_team, away_team,
                        competition_code, match_date, home_win_prob, draw_prob,
                        away_win_prob, predicted_home_goals, predicted_away_goals,
                        confidence, recommendation, explanation, model_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values,
                )
            return True
    except Exception as e:
        logger.error(f"Error saving prediction: {e}")
        return False


def get_prediction_from_db(match_id: int) -> dict[str, Any] | None:
    """Get a prediction by match ID."""
    with db_session() as conn:
        cursor = conn.cursor()
        query = adapt_query("SELECT * FROM predictions WHERE match_id = ?")
        cursor.execute(query, (match_id,))
        return fetch_one_dict(cursor)


def get_predictions_by_date(target_date: date) -> list[dict[str, Any]]:
    """Get all predictions for a specific date."""
    with db_session() as conn:
        cursor = conn.cursor()
        query = adapt_query(
            """
            SELECT * FROM predictions
            WHERE DATE(match_date) = ?
            ORDER BY confidence DESC
        """
        )
        cursor.execute(query, (target_date.isoformat(),))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_scheduled_matches_from_db(
    date_from: date | None = None,
    date_to: date | None = None,
    competition: str | None = None,
) -> list[dict[str, Any]]:
    """Get scheduled (not finished) matches from database."""
    with db_session() as conn:
        cursor = conn.cursor()

        query = "SELECT raw_data FROM matches WHERE status IN ('SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED', 'LIVE')"
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

        query += " ORDER BY match_date ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [json.loads(row["raw_data"]) for row in rows]


# ============== PREDICTION TRACKING ==============


def verify_prediction(match_id: int, home_score: int, away_score: int) -> dict[str, Any] | None:
    """
    Verify a prediction against actual match result.
    Updates the prediction record with actual scores and correctness.

    Returns:
        Dict with verification details or None if prediction not found.
    """
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Get the prediction
            query = adapt_query("SELECT * FROM predictions WHERE match_id = ?")
            cursor.execute(query, (match_id,))
            pred = fetch_one_dict(cursor)

            if not pred:
                logger.warning(f"No prediction found for match {match_id}")
                return None

            # Determine actual result
            if home_score > away_score:
                actual_result = "home_win"
            elif away_score > home_score:
                actual_result = "away_win"
            else:
                actual_result = "draw"

            # Check if prediction was correct
            recommendation = pred["recommendation"]
            was_correct = recommendation == actual_result

            # Update the prediction
            update_query = adapt_query(
                """
                UPDATE predictions SET
                    actual_home_score = ?,
                    actual_away_score = ?,
                    actual_result = ?,
                    was_correct = ?,
                    verified_at = ?
                WHERE match_id = ?
            """
            )
            cursor.execute(
                update_query,
                (
                    home_score,
                    away_score,
                    actual_result,
                    1 if was_correct else 0,
                    datetime.now().isoformat(),
                    match_id,
                ),
            )

            logger.info(f"Verified prediction for match {match_id}: {was_correct=}")
            return {
                "match_id": match_id,
                "home_score": home_score,
                "away_score": away_score,
                "actual_result": actual_result,
                "predicted_result": recommendation,
                "was_correct": was_correct,
            }

    except Exception as e:
        logger.error(f"Error verifying prediction {match_id}: {e}")
        return None


def get_prediction_statistics(days: int = 30) -> dict[str, Any]:
    """
    Calculate prediction performance statistics.
    Returns accuracy, ROI, and breakdowns by competition and bet type.
    """
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Get verified predictions from the last N days
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            query = adapt_query(
                """
                SELECT
                    competition_code,
                    recommendation,
                    was_correct,
                    confidence,
                    home_win_prob,
                    draw_prob,
                    away_win_prob
                FROM predictions
                WHERE verified_at IS NOT NULL
                AND verified_at >= ?
            """
            )
            cursor.execute(query, (cutoff_date,))

            rows = fetch_all_dict(cursor)

            if not rows:
                return {
                    "total_predictions": 0,
                    "correct_predictions": 0,
                    "accuracy": 0.0,
                    "roi_simulated": 0.0,
                    "by_competition": {},
                    "by_bet_type": {},
                }

            total = len(rows)
            correct = sum(1 for r in rows if r["was_correct"])
            accuracy = correct / total if total > 0 else 0.0

            # Calculate by competition
            by_competition = {}
            for row in rows:
                comp = row["competition_code"] or "Unknown"
                if comp not in by_competition:
                    by_competition[comp] = {"total": 0.0, "correct": 0.0, "accuracy": 0.0}
                by_competition[comp]["total"] += 1
                if row["was_correct"]:
                    by_competition[comp]["correct"] += 1

            # Add accuracy to each competition
            for comp in by_competition:
                t = by_competition[comp]["total"]
                c = by_competition[comp]["correct"]
                by_competition[comp]["accuracy"] = round(c / t * 100, 1) if t > 0 else 0.0

            # Calculate by bet type
            by_bet_type = {}
            for row in rows:
                bet = row["recommendation"] or "unknown"
                if bet not in by_bet_type:
                    by_bet_type[bet] = {"total": 0.0, "correct": 0.0, "accuracy": 0.0}
                by_bet_type[bet]["total"] += 1
                if row["was_correct"]:
                    by_bet_type[bet]["correct"] += 1

            for bet in by_bet_type:
                t = by_bet_type[bet]["total"]
                c = by_bet_type[bet]["correct"]
                by_bet_type[bet]["accuracy"] = round(c / t * 100, 1) if t > 0 else 0.0

            # Simulated ROI (assuming flat bets at odds ~2.0)
            # ROI = (profit / stake) * 100
            # If correct, profit = stake * (odds - 1) ≈ stake * 1.0
            # If wrong, profit = -stake
            avg_odds = 2.0
            total_stake = total
            total_profit = correct * (avg_odds - 1) - (total - correct)
            roi_simulated = (total_profit / total_stake * 100) if total_stake > 0 else 0.0

            return {
                "total_predictions": total,
                "correct_predictions": correct,
                "accuracy": round(accuracy * 100, 1),
                "roi_simulated": round(roi_simulated, 1),
                "by_competition": by_competition,
                "by_bet_type": by_bet_type,
            }

    except Exception as e:
        logger.error(f"Error getting prediction statistics: {e}")
        return {
            "total_predictions": 0,
            "correct_predictions": 0,
            "accuracy": 0.0,
            "roi_simulated": 0.0,
            "by_competition": {},
            "by_bet_type": {},
        }


def get_all_predictions_stats(days: int = 30) -> dict[str, Any]:
    """
    Get statistics from all predictions (including unverified).
    Used when no verified predictions exist yet to show distribution data.
    """
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            query = adapt_query(
                """
                SELECT
                    competition_code,
                    recommendation,
                    confidence
                FROM predictions
                WHERE created_at >= ?
            """
            )
            cursor.execute(query, (cutoff_date,))

            rows = fetch_all_dict(cursor)

            if not rows:
                return {
                    "total_predictions": 0,
                    "by_competition": {},
                    "by_bet_type": {},
                }

            total = len(rows)

            # Calculate by competition
            by_competition = {}
            for row in rows:
                comp = row["competition_code"] or "Unknown"
                if comp not in by_competition:
                    by_competition[comp] = {"total": 0, "correct": 0, "accuracy": 0.0}
                by_competition[comp]["total"] += 1

            # Calculate by bet type
            by_bet_type = {}
            for row in rows:
                bet = row["recommendation"] or "unknown"
                if bet not in by_bet_type:
                    by_bet_type[bet] = {"total": 0, "correct": 0, "accuracy": 0.0}
                by_bet_type[bet]["total"] += 1

            return {
                "total_predictions": total,
                "by_competition": by_competition,
                "by_bet_type": by_bet_type,
            }

    except Exception as e:
        logger.error(f"Error getting all predictions stats: {e}")
        return {
            "total_predictions": 0,
            "by_competition": {},
            "by_bet_type": {},
        }


def verify_finished_matches() -> int:
    """
    Verify all predictions for finished matches that haven't been verified yet.
    Returns the number of predictions verified.
    """
    try:
        with db_session() as conn:
            cursor = conn.cursor()

            # Get predictions without verification that have finished matches
            cursor.execute(
                """
                SELECT p.match_id, m.home_score, m.away_score
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                WHERE p.verified_at IS NULL
                AND m.status = 'FINISHED'
                AND m.home_score IS NOT NULL
                AND m.away_score IS NOT NULL
            """
            )

            rows = fetch_all_dict(cursor)
            verified_count = 0

            for row in rows:
                if verify_prediction(row["match_id"], row["home_score"], row["away_score"]):
                    verified_count += 1

            logger.info(f"Verified {verified_count} predictions")
            return verified_count

    except Exception as e:
        logger.error(f"Error verifying finished matches: {e}")
        return 0


# ============== ML MODELS ==============


def save_ml_model(
    model_name: str,
    model_type: str,
    version: str,
    accuracy: float,
    training_samples: int,
    feature_columns: list[str],
    model_binary: bytes,
    scaler_binary: bytes | None = None,
) -> bool:
    """Save a trained ML model to database."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO ml_models (
                    model_name, model_type, version, accuracy, training_samples,
                    feature_columns, model_binary, scaler_binary, trained_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    model_name,
                    model_type,
                    version,
                    accuracy,
                    training_samples,
                    json.dumps(feature_columns),
                    model_binary,
                    scaler_binary,
                    datetime.now().isoformat(),
                ),
            )
            logger.info(f"Saved ML model {model_name} v{version} to database")
            return True
    except Exception as e:
        logger.error(f"Error saving ML model: {e}")
        return False


def get_ml_model(model_name: str) -> dict[str, Any] | None:
    """Get a trained ML model from database."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM ml_models WHERE model_name = ?
        """,
            (model_name,),
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["feature_columns"] = json.loads(result["feature_columns"])
            return result
        return None


def get_all_ml_models() -> list[dict[str, Any]]:
    """Get all ML models metadata (without binary)."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT model_name, model_type, version, accuracy,
                   training_samples, trained_at
            FROM ml_models
            ORDER BY trained_at DESC
        """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# Initialize database on import
init_database()
