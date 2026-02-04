"""User favorites and preferences endpoints."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.data.database import db_session, get_placeholder

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Models
# ============================================================================


class FavoriteCreate(BaseModel):
    """Add a favorite pick."""
    match_id: int
    prediction_id: int | None = None
    note: str | None = Field(None, max_length=500)
    notify_before_match: bool = True


class FavoriteResponse(BaseModel):
    """Favorite response."""
    id: int
    match_id: int
    prediction_id: int | None
    note: str | None
    notify_before_match: bool
    created_at: str
    # Match details (from join)
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None


class FavoriteListResponse(BaseModel):
    """List of favorites."""
    favorites: list[FavoriteResponse]
    total: int


class PreferencesUpdate(BaseModel):
    """Update user preferences."""
    language: str | None = Field(None, pattern="^(fr|en|nl)$")
    timezone: str | None = None
    odds_format: str | None = Field(None, pattern="^(decimal|fractional|american)$")
    dark_mode: bool | None = None
    email_daily_picks: bool | None = None
    email_match_results: bool | None = None
    push_daily_picks: bool | None = None
    push_match_start: bool | None = None
    push_bet_results: bool | None = None
    default_stake: float | None = Field(None, gt=0)
    risk_level: str | None = Field(None, pattern="^(low|medium|high)$")
    favorite_competitions: list[str] | None = None


class PreferencesResponse(BaseModel):
    """User preferences."""
    language: str
    timezone: str
    odds_format: str
    dark_mode: bool
    email_daily_picks: bool
    email_match_results: bool
    push_daily_picks: bool
    push_match_start: bool
    push_bet_results: bool
    default_stake: float
    risk_level: str
    favorite_competitions: list[str]


# ============================================================================
# Database initialization
# ============================================================================


def _init_tables():
    """Initialize favorites and preferences tables."""
    with db_session() as conn:
        cursor = conn.cursor()

        # User favorites table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                match_id INTEGER NOT NULL,
                prediction_id INTEGER,
                note TEXT,
                notify_before_match INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, match_id)
            )
        """)

        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                language TEXT DEFAULT 'fr',
                timezone TEXT DEFAULT 'Europe/Paris',
                odds_format TEXT DEFAULT 'decimal',
                dark_mode INTEGER DEFAULT 1,
                email_daily_picks INTEGER DEFAULT 1,
                email_match_results INTEGER DEFAULT 0,
                push_daily_picks INTEGER DEFAULT 1,
                push_match_start INTEGER DEFAULT 0,
                push_bet_results INTEGER DEFAULT 1,
                default_stake REAL DEFAULT 10.0,
                risk_level TEXT DEFAULT 'medium',
                favorite_competitions TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_id)
        """)


try:
    _init_tables()
except Exception as e:
    logger.warning(f"Could not initialize favorites tables: {e}")


# ============================================================================
# Favorites endpoints
# ============================================================================


@router.post("/favorites", response_model=FavoriteResponse, responses=AUTH_RESPONSES)
async def add_favorite(user: AuthenticatedUser, favorite: FavoriteCreate) -> FavoriteResponse:
    """Add a pick to favorites."""
    user_id = user.get("sub", "")
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()

    with db_session() as conn:
        cursor = conn.cursor()

        # Check if already exists
        cursor.execute(
            f"SELECT id FROM user_favorites WHERE user_id = {ph} AND match_id = {ph}",
            (user_id, favorite.match_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Already in favorites")

        # Insert
        cursor.execute(
            f"""
            INSERT INTO user_favorites (user_id, match_id, prediction_id, note, notify_before_match, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (user_id, favorite.match_id, favorite.prediction_id, favorite.note,
             1 if favorite.notify_before_match else 0, now)
        )
        fav_id = cursor.lastrowid

    return FavoriteResponse(
        id=fav_id,
        match_id=favorite.match_id,
        prediction_id=favorite.prediction_id,
        note=favorite.note,
        notify_before_match=favorite.notify_before_match,
        created_at=now,
    )


@router.get("/favorites", response_model=FavoriteListResponse, responses=AUTH_RESPONSES)
async def list_favorites(user: AuthenticatedUser) -> FavoriteListResponse:
    """List user's favorite picks with match details."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        # Get favorites with match join
        cursor.execute(
            f"""
            SELECT f.id, f.match_id, f.prediction_id, f.note, f.notify_before_match, f.created_at,
                   ht.name as home_team, at.name as away_team, m.match_date, c.name as competition
            FROM user_favorites f
            LEFT JOIN matches m ON f.match_id = m.id
            LEFT JOIN teams ht ON m.home_team_id = ht.id
            LEFT JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN competitions c ON m.competition_id = c.id
            WHERE f.user_id = {ph}
            ORDER BY f.created_at DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()

    favorites = []
    for row in rows:
        favorites.append(FavoriteResponse(
            id=row[0],
            match_id=row[1],
            prediction_id=row[2],
            note=row[3],
            notify_before_match=bool(row[4]),
            created_at=row[5] or "",
            home_team=row[6],
            away_team=row[7],
            match_date=row[8],
            competition=row[9],
        ))

    return FavoriteListResponse(favorites=favorites, total=len(favorites))


@router.delete("/favorites/{match_id}", responses=AUTH_RESPONSES)
async def remove_favorite(user: AuthenticatedUser, match_id: int) -> dict[str, Any]:
    """Remove a pick from favorites."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM user_favorites WHERE user_id = {ph} AND match_id = {ph}",
            (user_id, match_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Favorite not found")

    return {"status": "removed", "match_id": match_id}


# ============================================================================
# Preferences endpoints
# ============================================================================


@router.get("/preferences", response_model=PreferencesResponse, responses=AUTH_RESPONSES)
async def get_preferences(user: AuthenticatedUser) -> PreferencesResponse:
    """Get user preferences."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM user_preferences WHERE user_id = {ph}",
            (user_id,)
        )
        row = cursor.fetchone()

    # Return defaults if no preferences saved
    if not row:
        return PreferencesResponse(
            language="fr",
            timezone="Europe/Paris",
            odds_format="decimal",
            dark_mode=True,
            email_daily_picks=True,
            email_match_results=False,
            push_daily_picks=True,
            push_match_start=False,
            push_bet_results=True,
            default_stake=10.0,
            risk_level="medium",
            favorite_competitions=[],
        )

    # Parse row (column order from CREATE TABLE)
    # id, user_id, language, timezone, odds_format, dark_mode, email_daily_picks,
    # email_match_results, push_daily_picks, push_match_start, push_bet_results,
    # default_stake, risk_level, favorite_competitions, created_at, updated_at
    fav_comps = []
    if row[13]:
        try:
            fav_comps = json.loads(row[13])
        except Exception:
            pass

    return PreferencesResponse(
        language=row[2] or "fr",
        timezone=row[3] or "Europe/Paris",
        odds_format=row[4] or "decimal",
        dark_mode=bool(row[5]),
        email_daily_picks=bool(row[6]),
        email_match_results=bool(row[7]),
        push_daily_picks=bool(row[8]),
        push_match_start=bool(row[9]),
        push_bet_results=bool(row[10]),
        default_stake=float(row[11] or 10.0),
        risk_level=row[12] or "medium",
        favorite_competitions=fav_comps,
    )


@router.put("/preferences", response_model=PreferencesResponse, responses=AUTH_RESPONSES)
async def update_preferences(user: AuthenticatedUser, prefs: PreferencesUpdate) -> PreferencesResponse:
    """Update user preferences."""
    user_id = user.get("sub", "")
    ph = get_placeholder()
    now = datetime.utcnow().isoformat()

    with db_session() as conn:
        cursor = conn.cursor()

        # Check if exists
        cursor.execute(f"SELECT id FROM user_preferences WHERE user_id = {ph}", (user_id,))
        existing = cursor.fetchone()

        if existing:
            # Build dynamic update
            updates = []
            params = []

            if prefs.language is not None:
                updates.append(f"language = {ph}")
                params.append(prefs.language)
            if prefs.timezone is not None:
                updates.append(f"timezone = {ph}")
                params.append(prefs.timezone)
            if prefs.odds_format is not None:
                updates.append(f"odds_format = {ph}")
                params.append(prefs.odds_format)
            if prefs.dark_mode is not None:
                updates.append(f"dark_mode = {ph}")
                params.append(1 if prefs.dark_mode else 0)
            if prefs.email_daily_picks is not None:
                updates.append(f"email_daily_picks = {ph}")
                params.append(1 if prefs.email_daily_picks else 0)
            if prefs.email_match_results is not None:
                updates.append(f"email_match_results = {ph}")
                params.append(1 if prefs.email_match_results else 0)
            if prefs.push_daily_picks is not None:
                updates.append(f"push_daily_picks = {ph}")
                params.append(1 if prefs.push_daily_picks else 0)
            if prefs.push_match_start is not None:
                updates.append(f"push_match_start = {ph}")
                params.append(1 if prefs.push_match_start else 0)
            if prefs.push_bet_results is not None:
                updates.append(f"push_bet_results = {ph}")
                params.append(1 if prefs.push_bet_results else 0)
            if prefs.default_stake is not None:
                updates.append(f"default_stake = {ph}")
                params.append(prefs.default_stake)
            if prefs.risk_level is not None:
                updates.append(f"risk_level = {ph}")
                params.append(prefs.risk_level)
            if prefs.favorite_competitions is not None:
                updates.append(f"favorite_competitions = {ph}")
                params.append(json.dumps(prefs.favorite_competitions))

            updates.append(f"updated_at = {ph}")
            params.append(now)
            params.append(user_id)

            if updates:
                query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = {ph}"
                cursor.execute(query, tuple(params))
        else:
            # Insert new
            cursor.execute(
                f"""
                INSERT INTO user_preferences (user_id, language, timezone, odds_format, dark_mode,
                    email_daily_picks, email_match_results, push_daily_picks, push_match_start,
                    push_bet_results, default_stake, risk_level, favorite_competitions, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    user_id,
                    prefs.language or "fr",
                    prefs.timezone or "Europe/Paris",
                    prefs.odds_format or "decimal",
                    1 if prefs.dark_mode in (None, True) else 0,
                    1 if prefs.email_daily_picks in (None, True) else 0,
                    0 if prefs.email_match_results in (None, False) else 1,
                    1 if prefs.push_daily_picks in (None, True) else 0,
                    0 if prefs.push_match_start in (None, False) else 1,
                    1 if prefs.push_bet_results in (None, True) else 0,
                    prefs.default_stake or 10.0,
                    prefs.risk_level or "medium",
                    json.dumps(prefs.favorite_competitions) if prefs.favorite_competitions else None,
                    now,
                    now,
                )
            )

    return await get_preferences(user)
