"""SQLAlchemy database models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all models."""

    pass


class Team(Base):
    """Football team model."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(10), nullable=True)
    tla: Mapped[str] = mapped_column(String(5), nullable=True)  # Three Letter Abbreviation
    country: Mapped[str] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    elo_rating: Mapped[Decimal] = mapped_column(Numeric(6, 1), default=1500.0)

    # Stats cache
    avg_goals_scored_home: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    avg_goals_scored_away: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    avg_goals_conceded_home: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    avg_goals_conceded_away: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    avg_xg_for: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    avg_xg_against: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    home_matches: Mapped[list["Match"]] = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )


class Competition(Base):
    """Football competition/league model."""

    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)  # PL, PD, BL1, SA, FL1, CL, EL
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emblem_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_season: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="competition")


class Match(Base):
    """Football match model."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    competition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitions.id"), nullable=False
    )

    match_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default="scheduled"
    )  # scheduled, live, finished, postponed, cancelled

    # Results (null if not finished)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score_ht: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Half-time
    away_score_ht: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # xG data (if available)
    home_xg: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    away_xg: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    # Odds (from bookmakers, for value calculation)
    odds_home: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    odds_draw: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    odds_away: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    home_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_matches"
    )
    competition: Mapped["Competition"] = relationship("Competition", back_populates="matches")
    prediction: Mapped[Optional["Prediction"]] = relationship(
        "Prediction", back_populates="match", uselist=False
    )

    # Indexes
    __table_args__ = (
        Index("ix_matches_date_status", "match_date", "status"),
        Index("ix_matches_competition_date", "competition_id", "match_date"),
    )

    @property
    def outcome(self) -> str | None:
        """Get match outcome: 'home', 'draw', 'away', or None if not finished."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return "home"
        elif self.home_score < self.away_score:
            return "away"
        return "draw"


class Prediction(Base):
    """Match prediction model."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), unique=True, nullable=False
    )

    # Probabilities (0-1)
    home_prob: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    draw_prob: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    away_prob: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    # Predicted outcome
    predicted_outcome: Mapped[str] = mapped_column(String(10), nullable=False)  # home, draw, away
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    # Value score vs bookmaker odds
    value_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)

    # Daily pick selection
    is_daily_pick: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pick_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 for daily picks
    pick_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)

    # LLM-generated explanation
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    risk_factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Model contributions (JSON)
    model_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_adjustments: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="prediction")
    result: Mapped[Optional["PredictionResult"]] = relationship(
        "PredictionResult", back_populates="prediction", uselist=False
    )

    # Indexes
    __table_args__ = (Index("ix_predictions_daily_pick", "is_daily_pick", "created_at"),)


class PredictionResult(Base):
    """Track prediction accuracy after match completion."""

    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("predictions.id"), unique=True, nullable=False
    )

    actual_outcome: Mapped[str] = mapped_column(String(10), nullable=False)  # home, draw, away
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Value captured (if odds were available)
    value_captured: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Probability assigned to actual outcome
    assigned_probability: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    prediction: Mapped["Prediction"] = relationship("Prediction", back_populates="result")


class NewsItem(Base):
    """News articles for LLM analysis."""

    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)

    # Related entities
    team_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    player_names: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Analysis results
    is_injury_news: Mapped[bool] = mapped_column(Boolean, default=False)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)  # -1 to 1
    impact_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)  # 0 to 1
    llm_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Indexes
    __table_args__ = (
        Index("ix_news_published", "published_at"),
        Index("ix_news_injury", "is_injury_news", "published_at"),
    )


class PushSubscription(Base):
    """Web push notification subscription."""

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    # Push subscription keys
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)

    # User association (optional - anonymous subscriptions allowed)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Preferences
    daily_picks: Mapped[bool] = mapped_column(Boolean, default=True)
    match_start: Mapped[bool] = mapped_column(Boolean, default=False)
    result_updates: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class CachedData(Base):
    """Pre-calculated data cache for fast API responses.

    Stores JSON data calculated daily at 6am to avoid real-time computation.
    Cache types: prediction_stats, standings, teams, upcoming_matches
    """

    __tablename__ = "cached_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    cache_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # prediction_stats, standings, teams, upcoming_matches
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON data
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# ============================================================================
# Standings & Sync Models
# ============================================================================


class Standing(Base):
    """League standings for a competition."""

    __tablename__ = "standings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    season: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Team info
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    team_name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_logo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stats
    played_games: Mapped[int] = mapped_column(Integer, default=0)
    won: Mapped[int] = mapped_column(Integer, default=0)
    drawn: Mapped[int] = mapped_column(Integer, default=0)
    lost: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    goal_difference: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)

    # Form (last 5 matches as string, e.g., "WWDLW")
    form: Mapped[str | None] = mapped_column(String(10), nullable=True)

    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Unique constraint: one standing per competition per team
    __table_args__ = (
        Index("ix_standings_competition", "competition_code"),
        Index("ix_standings_position", "competition_code", "position"),
        Index("uq_standings_comp_team", "competition_code", "team_id", unique=True),
    )


class SyncLog(Base):
    """Track data synchronization operations."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # matches, standings, predictions
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # running, success, failed
    records_synced: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stack trace

    # Metadata
    triggered_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # scheduler, manual, api

    __table_args__ = (Index("ix_sync_log_type_date", "sync_type", "started_at"),)


class MLModel(Base):
    """Trained machine learning model storage."""

    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # xgboost, random_forest, neural_net
    version: Mapped[str] = mapped_column(String(20), nullable=False)

    # Performance metrics
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    precision: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    recall: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    f1_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    training_samples: Mapped[int] = mapped_column(Integer, default=0)

    # Model storage
    feature_columns: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    hyperparameters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    model_binary: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    scaler_binary: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Status
    # Whether this model is currently used for predictions
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class NotificationLog(Base):
    """Track sent notifications for auditing and debugging."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # daily_picks, match_start, result
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # push, email, sms

    # Target
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("push_subscriptions.id"), nullable=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, sent, failed, delivered
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    __table_args__ = (Index("ix_notification_logs_type_date", "notification_type", "created_at"),)


class UserBankroll(Base):
    """Track user bankroll transactions and balance history."""

    __tablename__ = "user_bankrolls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Transaction
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # deposit, withdrawal, bet, win, adjustment
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Reference
    bet_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user_bets.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    __table_args__ = (Index("ix_user_bankrolls_user_date", "user_id", "created_at"),)


# ============================================================================
# User Data Models
# ============================================================================


class UserBet(Base):
    """User betting history - tracks all bets placed by users."""

    __tablename__ = "user_bets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # Supabase user ID
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    prediction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("predictions.id"), nullable=True
    )

    # Bet details
    bet_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # home_win, draw, away_win, over_25, under_25
    stake: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # Amount bet
    odds: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # Odds at time of bet
    potential_return: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # stake * odds

    # Result (filled after match)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, won, lost, void
    actual_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )  # 0 if lost, potential_return if won
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata
    followed_prediction: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Did user follow our prediction?
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # User notes

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index("ix_user_bets_user_status", "user_id", "status"),
        Index("ix_user_bets_user_date", "user_id", "created_at"),
    )


class UserStats(Base):
    """Pre-calculated user statistics - updated daily or on bet settlement."""

    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Betting stats
    total_bets: Mapped[int] = mapped_column(Integer, default=0)
    won_bets: Mapped[int] = mapped_column(Integer, default=0)
    lost_bets: Mapped[int] = mapped_column(Integer, default=0)
    pending_bets: Mapped[int] = mapped_column(Integer, default=0)
    void_bets: Mapped[int] = mapped_column(Integer, default=0)

    # Financial stats
    total_staked: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_returns: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    profit_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    roi_percentage: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=0
    )  # (profit/staked) * 100

    # Performance stats
    win_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)  # Percentage
    avg_odds: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Positive = wins, negative = losses

    # Prediction following stats
    followed_predictions: Mapped[int] = mapped_column(Integer, default=0)
    followed_wins: Mapped[int] = mapped_column(Integer, default=0)
    followed_win_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)

    # By bet type breakdown (JSON)
    stats_by_bet_type: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    stats_by_competition: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class UserFavorite(Base):
    """User favorite picks/predictions for quick access."""

    __tablename__ = "user_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    prediction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("predictions.id"), nullable=True
    )

    # What type of favorite
    favorite_type: Mapped[str] = mapped_column(String(20), default="pick")  # pick, match, team

    # Optional note
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Notification preference for this favorite
    notify_before_match: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Unique constraint: one favorite per user per match
    __table_args__ = (
        Index("ix_user_favorites_user", "user_id"),
        Index("ix_user_favorites_type", "user_id", "favorite_type"),
        Index("uq_user_favorites_user_match", "user_id", "match_id", unique=True),
    )


class UserPreferences(Base):
    """User preferences and settings."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Display preferences
    language: Mapped[str] = mapped_column(String(5), default="fr")  # fr, en, nl
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Paris")
    odds_format: Mapped[str] = mapped_column(
        String(20), default="decimal"
    )  # decimal, fractional, american
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=True)

    # Notification preferences
    email_daily_picks: Mapped[bool] = mapped_column(Boolean, default=True)
    email_match_results: Mapped[bool] = mapped_column(Boolean, default=False)
    push_daily_picks: Mapped[bool] = mapped_column(Boolean, default=True)
    push_match_start: Mapped[bool] = mapped_column(Boolean, default=False)
    push_bet_results: Mapped[bool] = mapped_column(Boolean, default=True)

    # Betting preferences
    default_stake: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=10.0)
    bankroll: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )  # Optional bankroll tracking
    risk_level: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high

    # Favorite competitions (JSON array of codes)
    favorite_competitions: Mapped[str | None] = mapped_column(Text, nullable=True)  # ["PL", "CL"]
    favorite_teams: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array of team IDs

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
