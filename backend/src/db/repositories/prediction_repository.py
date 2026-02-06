"""Prediction repository with domain-specific operations."""

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any
from typing import cast as typing_cast

from sqlalchemy import Integer, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.db.models import Match, Prediction, PredictionResult
from src.db.repositories.base import BaseRepository


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction operations with domain-specific methods."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Prediction, session)

    async def get_by_match_id(self, match_id: int) -> Prediction | None:
        """Get prediction for a specific match."""
        return await self.get_by_field("match_id", match_id)

    async def get_with_match(self, prediction_id: int) -> Prediction | None:
        """Get prediction with match data loaded."""
        stmt = (
            select(Prediction)
            .options(
                joinedload(Prediction.match).joinedload(Match.home_team),
                joinedload(Prediction.match).joinedload(Match.away_team),
            )
            .where(Prediction.id == prediction_id)
        )
        result = await self.session.execute(stmt)
        return typing_cast(Prediction | None, result.scalar_one_or_none())

    async def get_daily_picks(
        self,
        target_date: date,
        *,
        limit: int = 5,
    ) -> Sequence[Prediction]:
        """Get daily picks for a specific date."""
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        stmt = (
            select(Prediction)
            .options(
                joinedload(Prediction.match).joinedload(Match.home_team),
                joinedload(Prediction.match).joinedload(Match.away_team),
            )
            .where(
                and_(
                    Prediction.is_daily_pick == True,  # noqa: E712
                    Prediction.created_at >= start_dt,
                    Prediction.created_at <= end_dt,
                )
            )
            .order_by(Prediction.pick_rank.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return typing_cast(Sequence[Prediction], result.scalars().unique().all())

    async def get_by_date_range(
        self,
        date_from: date,
        date_to: date,
    ) -> Sequence[Prediction]:
        """Get predictions within a date range."""
        stmt = (
            select(Prediction)
            .join(Match)
            .where(
                and_(
                    Match.match_date >= datetime.combine(date_from, datetime.min.time()),
                    Match.match_date <= datetime.combine(date_to, datetime.max.time()),
                )
            )
            .options(joinedload(Prediction.match))
            .order_by(Prediction.confidence.desc())
        )
        result = await self.session.execute(stmt)
        return typing_cast(Sequence[Prediction], result.scalars().unique().all())

    async def get_unverified(self, limit: int = 100) -> Sequence[Prediction]:
        """Get predictions that haven't been verified yet."""
        stmt = (
            select(Prediction)
            .outerjoin(PredictionResult)
            .where(PredictionResult.id.is_(None))
            .options(joinedload(Prediction.match))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return typing_cast(Sequence[Prediction], result.scalars().unique().all())

    async def get_statistics(self, days: int = 30) -> dict[str, Any]:
        """Calculate prediction performance statistics."""
        cutoff = datetime.now() - timedelta(days=days)

        # Get verified predictions
        stmt = (
            select(
                func.count(PredictionResult.id).label("total"),
                func.sum(cast(PredictionResult.was_correct, Integer)).label("correct"),
            )
            .join(Prediction)
            .where(PredictionResult.created_at >= cutoff)
        )
        result = await self.session.execute(stmt)
        row = result.one()

        total = row.total or 0
        correct = row.correct or 0
        accuracy = (correct / total * 100) if total > 0 else 0.0

        # ROI calculation (assuming odds ~2.0)
        avg_odds = 2.0
        profit = correct * (avg_odds - 1) - (total - correct)
        roi = (profit / total * 100) if total > 0 else 0.0

        return {
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": round(accuracy, 1),
            "roi_simulated": round(roi, 1),
        }

    async def get_daily_breakdown(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily breakdown of prediction statistics.

        Returns stats grouped by day for charting purposes.
        """
        cutoff = datetime.now() - timedelta(days=days)

        # Group by date and calculate stats per day
        stmt = (
            select(
                func.date(PredictionResult.created_at).label("date"),
                func.count(PredictionResult.id).label("predictions"),
                func.sum(cast(PredictionResult.was_correct, Integer)).label("correct"),
            )
            .join(Prediction)
            .where(PredictionResult.created_at >= cutoff)
            .group_by(func.date(PredictionResult.created_at))
            .order_by(func.date(PredictionResult.created_at))
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        daily_stats = []
        for row in rows:
            predictions = row.predictions or 0
            correct = row.correct or 0
            accuracy = (correct / predictions) if predictions > 0 else 0.0

            daily_stats.append(
                {
                    "date": row.date.isoformat() if row.date else None,
                    "predictions": predictions,
                    "correct": correct,
                    "accuracy": round(accuracy, 4),
                }
            )

        return daily_stats

    async def get_by_competition(
        self,
        competition_code: str,
        *,
        days: int = 30,
    ) -> Sequence[Prediction]:
        """Get predictions for a specific competition."""
        cutoff = datetime.now() - timedelta(days=days)
        stmt = (
            select(Prediction)
            .join(Match)
            .where(
                and_(
                    Match.competition_code.isnot(None),  # Has competition
                    Prediction.created_at >= cutoff,
                )
            )
            .options(joinedload(Prediction.match))
            .order_by(Prediction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return typing_cast(Sequence[Prediction], result.scalars().unique().all())

    async def mark_as_daily_pick(
        self,
        prediction_id: int,
        rank: int,
        pick_score: float,
    ) -> Prediction | None:
        """Mark a prediction as a daily pick."""
        return await self.update(
            prediction_id,
            is_daily_pick=True,
            pick_rank=rank,
            pick_score=pick_score,
        )

    async def clear_daily_picks(self, target_date: date) -> int:
        """Clear daily picks for a specific date."""
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        stmt = select(Prediction).where(
            and_(
                Prediction.is_daily_pick == True,  # noqa: E712
                Prediction.created_at >= start_dt,
                Prediction.created_at <= end_dt,
            )
        )
        result = await self.session.execute(stmt)
        predictions = result.scalars().all()

        for pred in predictions:
            pred.is_daily_pick = False
            pred.pick_rank = None
            pred.pick_score = None

        await self.session.flush()
        return len(predictions)


class PredictionResultRepository(BaseRepository[PredictionResult]):
    """Repository for PredictionResult operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PredictionResult, session)

    async def get_by_prediction_id(self, prediction_id: int) -> PredictionResult | None:
        """Get result for a specific prediction."""
        return await self.get_by_field("prediction_id", prediction_id)

    async def verify_prediction(
        self,
        prediction: Prediction,
        actual_outcome: str,
    ) -> PredictionResult:
        """Create a verification result for a prediction."""
        was_correct = prediction.predicted_outcome == actual_outcome

        # Get the probability assigned to actual outcome
        prob_map = {
            "home": float(prediction.home_prob),
            "draw": float(prediction.draw_prob),
            "away": float(prediction.away_prob),
        }
        assigned_probability = prob_map.get(actual_outcome, 0.0)

        return await self.create(
            prediction_id=prediction.id,
            actual_outcome=actual_outcome,
            was_correct=was_correct,
            assigned_probability=assigned_probability,
        )
