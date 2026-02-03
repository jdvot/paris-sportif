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
