"""Bets and bankroll management endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.auth import AUTH_RESPONSES, AuthenticatedUser
from src.db.services.user_service import BetService

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
# Bankroll endpoints
# ============================================================================


@router.get("/bankroll", response_model=BankrollResponse, responses=AUTH_RESPONSES)
async def get_bankroll(user: AuthenticatedUser) -> BankrollResponse:
    """Get user's bankroll summary."""
    user_id = user.get("sub", "")
    summary = await BetService.get_bankroll_summary(user_id)
    return BankrollResponse(**summary)


@router.put("/bankroll", response_model=BankrollResponse, responses=AUTH_RESPONSES)
async def update_bankroll(
    user: AuthenticatedUser,
    settings: BankrollSettings,
) -> BankrollResponse:
    """Update user's bankroll settings."""
    user_id = user.get("sub", "")
    summary = await BetService.update_bankroll_settings(
        user_id=user_id,
        initial_bankroll=settings.initial_bankroll,
        alert_threshold=settings.alert_threshold,
        default_stake_pct=settings.default_stake_pct,
    )
    return BankrollResponse(**summary)


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
    bets = await BetService.list_bets(
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [BetResponse(**bet) for bet in bets]


@router.post(
    "", response_model=BetResponse, status_code=status.HTTP_201_CREATED, responses=AUTH_RESPONSES
)
async def create_bet(
    user: AuthenticatedUser,
    bet: BetCreate,
) -> BetResponse:
    """Create a new bet."""
    user_id = user.get("sub", "")

    if bet.prediction not in ("home_win", "away_win", "draw"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid prediction. Must be home_win, away_win, or draw",
        )

    result = await BetService.create_bet(
        user_id=user_id,
        match_id=bet.match_id,
        prediction=bet.prediction,
        odds=bet.odds,
        amount=bet.amount,
        confidence=bet.confidence,
    )
    return BetResponse(**result)


@router.patch("/{bet_id}", response_model=BetResponse, responses=AUTH_RESPONSES)
async def update_bet(
    user: AuthenticatedUser,
    bet_id: int,
    update: BetUpdate,
) -> BetResponse:
    """Update bet status (won, lost, void)."""
    user_id = user.get("sub", "")

    if update.status not in ("pending", "won", "lost", "void"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be pending, won, lost, or void",
        )

    result = await BetService.update_bet_status(
        user_id=user_id,
        bet_id=bet_id,
        status=update.status,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    return BetResponse(**result)


@router.delete("/{bet_id}", status_code=status.HTTP_204_NO_CONTENT, responses=AUTH_RESPONSES)
async def delete_bet(
    user: AuthenticatedUser,
    bet_id: int,
):
    """Delete a pending bet."""
    user_id = user.get("sub", "")

    deleted = await BetService.delete_bet(user_id, bet_id)
    if not deleted:
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
    result = await BetService.get_kelly_suggestion(
        user_id=user_id,
        odds=odds,
        confidence=confidence,
    )
    return KellySuggestion(**result)
