"""Bets and bankroll management endpoints."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.data.database import db_session, get_placeholder

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Models
# ============================================================================


class BankrollSettings(BaseModel):
    """User bankroll settings."""

    initial_bankroll: float = Field(ge=0, description="Initial bankroll amount")
    alert_threshold: float = Field(
        ge=0, le=100, default=20, description="Alert when bankroll drops below this % of initial"
    )
    default_stake_pct: float = Field(
        ge=0.1, le=100, default=2, description="Default stake as % of current bankroll"
    )


class BetCreate(BaseModel):
    """Create a new bet."""

    match_id: int
    prediction: str = Field(..., description="home_win, away_win, or draw")
    odds: float = Field(ge=1.01, description="Odds for this bet")
    amount: float = Field(ge=0, description="Stake amount")
    confidence: float | None = Field(None, ge=0, le=100, description="Confidence level %")


class BetUpdate(BaseModel):
    """Update bet status."""

    status: str = Field(..., description="pending, won, lost, void")


class BetResponse(BaseModel):
    """Bet response."""

    id: int
    match_id: int
    prediction: str
    odds: float
    amount: float
    status: str
    potential_return: float
    actual_return: float | None
    confidence: float | None
    created_at: str


class BankrollResponse(BaseModel):
    """Bankroll summary response."""

    initial_bankroll: float
    current_bankroll: float
    total_staked: float
    total_returned: float
    profit_loss: float
    roi_pct: float
    win_rate: float
    total_bets: int
    won_bets: int
    lost_bets: int
    pending_bets: int
    alert_threshold: float
    is_below_threshold: bool


class KellySuggestion(BaseModel):
    """Kelly criterion stake suggestion."""

    suggested_stake: float
    suggested_stake_pct: float
    kelly_fraction: float
    edge: float
    bankroll: float
    confidence_adjusted: bool


# ============================================================================
# Database initialization
# ============================================================================


def _init_bets_tables():
    """Initialize bets and bankroll tables."""
    with db_session() as conn:
        cursor = conn.cursor()

        # User bankroll settings
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_bankroll (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                initial_bankroll REAL DEFAULT 0,
                alert_threshold REAL DEFAULT 20,
                default_stake_pct REAL DEFAULT 2,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # User bets
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                match_id INTEGER NOT NULL,
                prediction TEXT NOT NULL,
                odds REAL NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                potential_return REAL,
                actual_return REAL,
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create index for user_id
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_bets_user_id ON user_bets(user_id)
        """
        )


try:
    _init_bets_tables()
except Exception as e:
    logger.warning(f"Could not initialize bets tables: {e}")


# ============================================================================
# Bankroll endpoints
# ============================================================================


@router.get("/bankroll", response_model=BankrollResponse, responses=AUTH_RESPONSES)
async def get_bankroll(user: AuthenticatedUser) -> BankrollResponse:
    """Get user's bankroll summary."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        # Get bankroll settings
        cursor.execute(
            f"SELECT initial_bankroll, alert_threshold FROM user_bankroll WHERE user_id = {ph}",
            (user_id,),
        )
        settings = cursor.fetchone()

        initial_bankroll = settings[0] if settings else 0.0
        alert_threshold = settings[1] if settings else 20.0

        # Get bet statistics
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won,
                SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) as lost,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status != 'void' THEN amount ELSE 0 END) as total_staked,
                SUM(CASE WHEN status = 'won' THEN actual_return ELSE 0 END) as total_returned
            FROM user_bets
            WHERE user_id = {ph}
            """,
            (user_id,),
        )
        stats = cursor.fetchone()

        total_bets = stats[0] or 0
        won_bets = stats[1] or 0
        lost_bets = stats[2] or 0
        pending_bets = stats[3] or 0
        total_staked = stats[4] or 0.0
        total_returned = stats[5] or 0.0

        # Calculate metrics
        profit_loss = total_returned - total_staked
        current_bankroll = initial_bankroll + profit_loss
        roi_pct = (profit_loss / total_staked * 100) if total_staked > 0 else 0.0
        win_rate = (won_bets / (won_bets + lost_bets) * 100) if (won_bets + lost_bets) > 0 else 0.0

        # Check threshold
        threshold_amount = initial_bankroll * (alert_threshold / 100)
        is_below_threshold = current_bankroll < threshold_amount if initial_bankroll > 0 else False

        return BankrollResponse(
            initial_bankroll=initial_bankroll,
            current_bankroll=round(current_bankroll, 2),
            total_staked=round(total_staked, 2),
            total_returned=round(total_returned, 2),
            profit_loss=round(profit_loss, 2),
            roi_pct=round(roi_pct, 2),
            win_rate=round(win_rate, 1),
            total_bets=total_bets,
            won_bets=won_bets,
            lost_bets=lost_bets,
            pending_bets=pending_bets,
            alert_threshold=alert_threshold,
            is_below_threshold=is_below_threshold,
        )


@router.put("/bankroll", response_model=BankrollResponse, responses=AUTH_RESPONSES)
async def update_bankroll(
    user: AuthenticatedUser,
    settings: BankrollSettings,
) -> BankrollResponse:
    """Update user's bankroll settings."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        # Upsert bankroll settings
        cursor.execute(
            f"SELECT id FROM user_bankroll WHERE user_id = {ph}",
            (user_id,),
        )
        existing = cursor.fetchone()

        now = datetime.now(UTC).isoformat()

        if existing:
            cursor.execute(
                f"""
                UPDATE user_bankroll
                SET initial_bankroll = {ph},
                    alert_threshold = {ph},
                    default_stake_pct = {ph},
                    updated_at = {ph}
                WHERE user_id = {ph}
                """,
                (
                    settings.initial_bankroll,
                    settings.alert_threshold,
                    settings.default_stake_pct,
                    now,
                    user_id,
                ),
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO user_bankroll
                (user_id, initial_bankroll, alert_threshold, default_stake_pct, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    user_id,
                    settings.initial_bankroll,
                    settings.alert_threshold,
                    settings.default_stake_pct,
                    now,
                    now,
                ),
            )

    # Return updated bankroll
    return await get_bankroll(user)


# ============================================================================
# Bets endpoints
# ============================================================================


@router.get("", response_model=list[BetResponse], responses=AUTH_RESPONSES)
async def list_bets(
    user: AuthenticatedUser,
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[BetResponse]:
    """List user's bets."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        query = f"""
            SELECT id, match_id, prediction, odds, amount, status,
                   potential_return, actual_return, confidence, created_at
            FROM user_bets
            WHERE user_id = {ph}
        """
        params: list = [user_id]

        if status:
            query += f" AND status = {ph}"
            params.append(status)

        query += f" ORDER BY created_at DESC LIMIT {ph} OFFSET {ph}"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

    return [
        BetResponse(
            id=row[0],
            match_id=row[1],
            prediction=row[2],
            odds=row[3],
            amount=row[4],
            status=row[5],
            potential_return=row[6] or 0,
            actual_return=row[7],
            confidence=row[8],
            created_at=row[9],
        )
        for row in rows
    ]


@router.post(
    "", response_model=BetResponse, status_code=status.HTTP_201_CREATED, responses=AUTH_RESPONSES
)
async def create_bet(
    user: AuthenticatedUser,
    bet: BetCreate,
) -> BetResponse:
    """Create a new bet."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    if bet.prediction not in ("home_win", "away_win", "draw"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid prediction. Must be home_win, away_win, or draw",
        )

    potential_return = bet.amount * bet.odds
    now = datetime.now(UTC).isoformat()

    with db_session() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            INSERT INTO user_bets
            (user_id, match_id, prediction, odds, amount, status, potential_return, confidence, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'pending', {ph}, {ph}, {ph}, {ph})
            """,
            (
                user_id,
                bet.match_id,
                bet.prediction,
                bet.odds,
                bet.amount,
                potential_return,
                bet.confidence,
                now,
                now,
            ),
        )
        bet_id = cursor.lastrowid

    return BetResponse(
        id=bet_id,
        match_id=bet.match_id,
        prediction=bet.prediction,
        odds=bet.odds,
        amount=bet.amount,
        status="pending",
        potential_return=potential_return,
        actual_return=None,
        confidence=bet.confidence,
        created_at=now,
    )


@router.patch("/{bet_id}", response_model=BetResponse, responses=AUTH_RESPONSES)
async def update_bet(
    user: AuthenticatedUser,
    bet_id: int,
    update: BetUpdate,
) -> BetResponse:
    """Update bet status (won, lost, void)."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    if update.status not in ("pending", "won", "lost", "void"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be pending, won, lost, or void",
        )

    with db_session() as conn:
        cursor = conn.cursor()

        # Get current bet
        cursor.execute(
            f"""
            SELECT id, match_id, prediction, odds, amount, potential_return, confidence, created_at
            FROM user_bets
            WHERE id = {ph} AND user_id = {ph}
            """,
            (bet_id, user_id),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bet not found",
            )

        # Calculate actual return
        actual_return = None
        if update.status == "won":
            actual_return = row[5]  # potential_return
        elif update.status == "lost":
            actual_return = 0.0
        elif update.status == "void":
            actual_return = row[4]  # refund amount

        # Update bet
        cursor.execute(
            f"""
            UPDATE user_bets
            SET status = {ph}, actual_return = {ph}, updated_at = {ph}
            WHERE id = {ph}
            """,
            (update.status, actual_return, datetime.now(UTC).isoformat(), bet_id),
        )

    return BetResponse(
        id=row[0],
        match_id=row[1],
        prediction=row[2],
        odds=row[3],
        amount=row[4],
        status=update.status,
        potential_return=row[5],
        actual_return=actual_return,
        confidence=row[6],
        created_at=row[7],
    )


@router.delete("/{bet_id}", status_code=status.HTTP_204_NO_CONTENT, responses=AUTH_RESPONSES)
async def delete_bet(
    user: AuthenticatedUser,
    bet_id: int,
):
    """Delete a pending bet."""
    user_id = user.get("sub", "")
    ph = get_placeholder()

    with db_session() as conn:
        cursor = conn.cursor()

        # Only allow deleting pending bets
        cursor.execute(
            f"""
            DELETE FROM user_bets
            WHERE id = {ph} AND user_id = {ph} AND status = 'pending'
            """,
            (bet_id, user_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bet not found or cannot be deleted (only pending bets can be deleted)",
            )


# ============================================================================
# Kelly Criterion
# ============================================================================


@router.get("/kelly", response_model=KellySuggestion, responses=AUTH_RESPONSES)
async def get_kelly_suggestion(
    user: AuthenticatedUser,
    odds: float = Query(..., ge=1.01, description="Decimal odds"),
    confidence: float = Query(..., ge=0, le=100, description="Win probability estimate %"),
) -> KellySuggestion:
    """
    Calculate Kelly Criterion stake suggestion.

    Kelly formula: f* = (bp - q) / b
    Where:
    - f* = fraction of bankroll to bet
    - b = decimal odds - 1
    - p = probability of winning
    - q = probability of losing (1 - p)
    """
    user_id = user.get("sub", "")
    ph = get_placeholder()

    # Get current bankroll
    with db_session() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT initial_bankroll FROM user_bankroll WHERE user_id = {ph}",
            (user_id,),
        )
        row = cursor.fetchone()
        initial_bankroll = row[0] if row else 0.0

        # Get current P&L
        cursor.execute(
            f"""
            SELECT
                SUM(CASE WHEN status != 'void' THEN amount ELSE 0 END) as staked,
                SUM(CASE WHEN status = 'won' THEN actual_return ELSE 0 END) as returned
            FROM user_bets WHERE user_id = {ph}
            """,
            (user_id,),
        )
        stats = cursor.fetchone()
        staked = stats[0] or 0
        returned = stats[1] or 0

    current_bankroll = initial_bankroll + (returned - staked)

    if current_bankroll <= 0:
        return KellySuggestion(
            suggested_stake=0,
            suggested_stake_pct=0,
            kelly_fraction=0,
            edge=0,
            bankroll=current_bankroll,
            confidence_adjusted=False,
        )

    # Kelly calculation
    p = confidence / 100  # Win probability
    q = 1 - p  # Loss probability
    b = odds - 1  # Net odds

    # Kelly fraction: (bp - q) / b
    kelly_fraction = (b * p - q) / b if b > 0 else 0

    # Clamp to reasonable range (0 to 25% of bankroll)
    kelly_fraction = max(0, min(kelly_fraction, 0.25))

    # Use half-Kelly for more conservative betting
    half_kelly = kelly_fraction / 2

    suggested_stake = current_bankroll * half_kelly
    suggested_stake_pct = half_kelly * 100

    # Calculate edge
    edge = (p * odds) - 1  # Expected value per unit staked

    return KellySuggestion(
        suggested_stake=round(suggested_stake, 2),
        suggested_stake_pct=round(suggested_stake_pct, 2),
        kelly_fraction=round(kelly_fraction, 4),
        edge=round(edge, 4),
        bankroll=round(current_bankroll, 2),
        confidence_adjusted=True,  # Using half-Kelly
    )
