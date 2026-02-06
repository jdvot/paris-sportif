"""Prediction service providing high-level prediction operations.

Migration mapping:
- save_prediction() -> PredictionService.save_prediction()
- get_prediction_from_db() -> PredictionService.get_prediction()
- get_predictions_by_date() -> PredictionService.get_by_date()
- get_predictions_by_date() -> PredictionService.get_predictions_for_date_with_details()
- verify_prediction() -> PredictionService.verify_prediction()
- verify_finished_matches() -> PredictionService.verify_all_finished()
- get_prediction_statistics() -> PredictionService.get_statistics()
- get_all_predictions_stats() -> PredictionService.get_all_statistics()
- save_prediction (route format) -> PredictionService.save_prediction_from_api()
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from src.db.models import Match, Prediction
from src.db.repositories import get_uow

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for prediction-related operations."""

    @staticmethod
    async def save_prediction(prediction: dict[str, Any]) -> bool:
        """Save a prediction to database.

        Replaces: src.data.database.save_prediction()
        """
        try:
            async with get_uow() as uow:
                match_id = prediction.get("match_id")
                if not match_id:
                    logger.warning("No match_id in prediction data")
                    return False

                # Get or check the match exists
                match = await uow.matches.get_by_id(match_id)
                if not match:
                    logger.warning(f"Match {match_id} not found")
                    return False

                # Determine predicted outcome
                home_prob = Decimal(str(prediction.get("home_win_prob", 0)))
                draw_prob = Decimal(str(prediction.get("draw_prob", 0)))
                away_prob = Decimal(str(prediction.get("away_win_prob", 0)))

                if home_prob >= draw_prob and home_prob >= away_prob:
                    predicted_outcome = "home"
                    confidence = home_prob
                elif draw_prob >= home_prob and draw_prob >= away_prob:
                    predicted_outcome = "draw"
                    confidence = draw_prob
                else:
                    predicted_outcome = "away"
                    confidence = away_prob

                await uow.predictions.upsert(
                    "match_id",
                    match_id,
                    home_prob=home_prob,
                    draw_prob=draw_prob,
                    away_prob=away_prob,
                    predicted_outcome=predicted_outcome,
                    confidence=confidence,
                    explanation=prediction.get("explanation"),
                )

                await uow.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
            return False

    @staticmethod
    async def get_prediction(match_id: int) -> dict[str, Any] | None:
        """Get a prediction by match ID.

        Replaces: src.data.database.get_prediction_from_db()
        """
        async with get_uow() as uow:
            pred = await uow.predictions.get_by_match_id(match_id)
            if not pred:
                return None

            import json

            # Parse stored JSON arrays for key_factors and risk_factors
            key_factors = None
            risk_factors = None
            if pred.key_factors:
                try:
                    key_factors = json.loads(pred.key_factors)
                except (json.JSONDecodeError, TypeError):
                    key_factors = None
            if pred.risk_factors:
                try:
                    risk_factors = json.loads(pred.risk_factors)
                except (json.JSONDecodeError, TypeError):
                    risk_factors = None

            # Parse model_details and llm_adjustments from DB
            model_details = None
            llm_adjustments = None
            if pred.model_details:
                try:
                    model_details = json.loads(pred.model_details)
                except (json.JSONDecodeError, TypeError):
                    model_details = None
            if pred.llm_adjustments:
                try:
                    llm_adjustments = json.loads(pred.llm_adjustments)
                except (json.JSONDecodeError, TypeError):
                    llm_adjustments = None

            return {
                "id": pred.id,
                "match_id": pred.match_id,
                "home_win_prob": float(pred.home_prob),
                "draw_prob": float(pred.draw_prob),
                "away_win_prob": float(pred.away_prob),
                "predicted_outcome": pred.predicted_outcome,
                "confidence": float(pred.confidence),
                "explanation": pred.explanation,
                "key_factors": key_factors,
                "risk_factors": risk_factors,
                "value_score": float(pred.value_score) if pred.value_score else None,
                "is_daily_pick": pred.is_daily_pick,
                "pick_rank": pred.pick_rank,
                "model_details": model_details,
                "llm_adjustments": llm_adjustments,
                "created_at": (
                    pred.created_at.isoformat()
                    if pred.created_at and hasattr(pred.created_at, "isoformat")
                    else str(pred.created_at) if pred.created_at else None
                ),
            }

    @staticmethod
    async def get_by_date(target_date: date) -> list[dict[str, Any]]:
        """Get all predictions for a specific date.

        Replaces: src.data.database.get_predictions_by_date()
        """
        async with get_uow() as uow:
            predictions = await uow.predictions.get_by_date_range(
                target_date,
                target_date,
            )
            return [
                {
                    "id": p.id,
                    "match_id": p.match_id,
                    "home_win_prob": float(p.home_prob),
                    "draw_prob": float(p.draw_prob),
                    "away_win_prob": float(p.away_prob),
                    "confidence": float(p.confidence),
                    "predicted_outcome": p.predicted_outcome,
                    "is_daily_pick": p.is_daily_pick,
                }
                for p in predictions
            ]

    @staticmethod
    async def verify_prediction(
        match_id: int,
        home_score: int,
        away_score: int,
    ) -> dict[str, Any] | None:
        """Verify a prediction against actual match result.

        Replaces: src.data.database.verify_prediction()

        Returns:
            Dict with format: {
                "actual_result": str,  # "home_win", "draw", or "away_win"
                "was_correct": bool,
                ... additional fields
            }
            Returns None if prediction not found.
        """
        try:
            async with get_uow() as uow:
                pred = await uow.predictions.get_by_match_id(match_id)
                if not pred:
                    logger.warning(f"No prediction found for match {match_id}")
                    return None

                # Determine actual result (internal format: home, draw, away)
                if home_score > away_score:
                    actual_outcome = "home"
                elif away_score > home_score:
                    actual_outcome = "away"
                else:
                    actual_outcome = "draw"

                # Map to route format (home_win, draw, away_win)
                outcome_to_result = {
                    "home": "home_win",
                    "draw": "draw",
                    "away": "away_win",
                }
                actual_result = outcome_to_result.get(actual_outcome, actual_outcome)

                # Check if existing result
                existing_result = await uow.prediction_results.get_by_prediction_id(pred.id)
                if existing_result:
                    logger.info(f"Prediction {pred.id} already verified")
                    existing_outcome = existing_result.actual_outcome
                    return {
                        "actual_result": outcome_to_result.get(existing_outcome, existing_outcome),
                        "was_correct": existing_result.was_correct,
                    }

                # Create verification result
                result = await uow.prediction_results.verify_prediction(pred, actual_outcome)
                await uow.commit()

                logger.info(
                    f"Verified prediction for match {match_id}: correct={result.was_correct}"
                )
                return {
                    "actual_result": actual_result,
                    "was_correct": result.was_correct,
                }

        except Exception as e:
            logger.error(f"Error verifying prediction {match_id}: {e}")
            return None

    @staticmethod
    async def verify_all_finished() -> int:
        """Verify all predictions for finished matches.

        Replaces: src.data.database.verify_finished_matches()
        """
        try:
            async with get_uow() as uow:
                # Get finished matches with unverified predictions
                matches = await uow.matches.get_finished_unverified()
                verified_count = 0

                for match in matches:
                    if match.home_score is None or match.away_score is None:
                        continue

                    result = await PredictionService.verify_prediction(
                        match.id,
                        match.home_score,
                        match.away_score,
                    )
                    if result:
                        verified_count += 1

                logger.info(f"Verified {verified_count} predictions")
                return verified_count

        except Exception as e:
            logger.error(f"Error verifying finished matches: {e}")
            return 0

    @staticmethod
    async def get_statistics(days: int = 30) -> dict[str, Any]:
        """Calculate prediction performance statistics.

        Replaces: src.data.database.get_prediction_statistics()
        """
        try:
            async with get_uow() as uow:
                stats = await uow.predictions.get_statistics(days=days)
                return stats

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

    @staticmethod
    async def get_daily_picks(target_date: date | None = None) -> list[dict[str, Any]]:
        """Get daily picks for a date.

        New method using repository pattern.
        """
        if target_date is None:
            target_date = date.today()

        async with get_uow() as uow:
            picks = await uow.predictions.get_daily_picks(target_date)
            return [
                {
                    "id": p.id,
                    "match_id": p.match_id,
                    "home_prob": float(p.home_prob),
                    "draw_prob": float(p.draw_prob),
                    "away_prob": float(p.away_prob),
                    "confidence": float(p.confidence),
                    "predicted_outcome": p.predicted_outcome,
                    "pick_rank": p.pick_rank,
                    "pick_score": float(p.pick_score) if p.pick_score else None,
                    "explanation": p.explanation,
                    "match": (
                        {
                            "id": p.match.id,
                            "home_team": (p.match.home_team.name if p.match.home_team else None),
                            "away_team": (p.match.away_team.name if p.match.away_team else None),
                            "match_date": (
                                (
                                    p.match.match_date.isoformat()
                                    if hasattr(p.match.match_date, "isoformat")
                                    else str(p.match.match_date)
                                )
                                if p.match.match_date
                                else None
                            ),
                        }
                        if p.match
                        else None
                    ),
                }
                for p in picks
            ]

    @staticmethod
    async def get_predictions_for_date_with_details(
        target_date: date,
    ) -> list[dict[str, Any]]:
        """Get predictions for a date with full match details.

        Returns predictions with home_team, away_team, competition_code, match_date, etc.
        Replaces legacy get_predictions_by_date() for route usage.

        Args:
            target_date: The date to get predictions for.

        Returns:
            List of predictions with full match details.
        """
        async with get_uow() as uow:
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = datetime.combine(target_date, datetime.max.time())

            # Query predictions with match, team, and result data
            # Note: competition_code is a string field, not a relationship
            stmt = (
                select(Prediction)
                .join(Match)
                .options(
                    joinedload(Prediction.match).joinedload(Match.home_team),
                    joinedload(Prediction.match).joinedload(Match.away_team),
                    joinedload(Prediction.result),  # Load verification result
                )
                .where(
                    and_(
                        Match.match_date >= start_dt,
                        Match.match_date <= end_dt,
                    )
                )
                .order_by(Prediction.confidence.desc())
            )
            result = await uow.session.execute(stmt)
            predictions = result.scalars().unique().all()

            results = []
            for p in predictions:
                # Parse stored JSON arrays for key_factors and risk_factors
                import json

                key_factors = None
                risk_factors = None
                if p.key_factors:
                    try:
                        key_factors = json.loads(p.key_factors)
                    except (json.JSONDecodeError, TypeError):
                        key_factors = None
                if p.risk_factors:
                    try:
                        risk_factors = json.loads(p.risk_factors)
                    except (json.JSONDecodeError, TypeError):
                        risk_factors = None

                # Build actual score string from match result
                actual_score = None
                if p.match and p.match.home_score is not None and p.match.away_score is not None:
                    actual_score = f"{p.match.home_score}-{p.match.away_score}"

                results.append(
                    {
                        "id": p.id,
                        "match_id": p.match_id,
                        "match_external_id": p.match.external_id if p.match else None,
                        "home_team": (
                            p.match.home_team.name if p.match and p.match.home_team else None
                        ),
                        "away_team": (
                            p.match.away_team.name if p.match and p.match.away_team else None
                        ),
                        "competition_code": (p.match.competition_code if p.match else None),
                        "match_date": (
                            p.match.match_date.isoformat()
                            if p.match
                            and p.match.match_date
                            and hasattr(p.match.match_date, "isoformat")
                            else str(p.match.match_date) if p.match and p.match.match_date else None
                        ),
                        "home_win_prob": float(p.home_prob),
                        "draw_prob": float(p.draw_prob),
                        "away_win_prob": float(p.away_prob),
                        "confidence": float(p.confidence),
                        "recommendation": p.predicted_outcome,
                        "explanation": p.explanation,
                        "key_factors": key_factors,
                        "risk_factors": risk_factors,
                        "value_score": float(p.value_score) if p.value_score else None,
                        "is_daily_pick": p.is_daily_pick,
                        "pick_rank": p.pick_rank,
                        "created_at": (
                            p.created_at.isoformat()
                            if p.created_at and hasattr(p.created_at, "isoformat")
                            else str(p.created_at) if p.created_at else None
                        ),
                        # Verification fields
                        "is_verified": p.result is not None,
                        "is_correct": p.result.was_correct if p.result else None,
                        "actual_score": actual_score,
                    }
                )
            return results

    @staticmethod
    async def save_prediction_from_api(prediction_data: dict[str, Any]) -> bool:
        """Save a prediction with the format used by the predictions route.

        This method handles the prediction format from API routes:
        - match_id, match_external_id
        - home_team, away_team, competition_code, match_date
        - home_win_prob, draw_prob, away_win_prob
        - confidence, recommendation, explanation

        Args:
            prediction_data: Dict with prediction data from API route.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            async with get_uow() as uow:
                match_id = prediction_data.get("match_id")
                if not match_id:
                    logger.warning("No match_id in prediction data")
                    return False

                # Get or create the match
                match = await uow.matches.get_by_id(match_id)
                if not match:
                    # Try to find by external_id
                    external_id = prediction_data.get("match_external_id")
                    if external_id:
                        match = await uow.matches.get_by_field("external_id", external_id)

                if not match:
                    logger.warning(f"Match {match_id} not found, cannot save prediction")
                    return False

                # Parse probabilities
                home_prob = Decimal(str(prediction_data.get("home_win_prob", 0)))
                draw_prob = Decimal(str(prediction_data.get("draw_prob", 0)))
                away_prob = Decimal(str(prediction_data.get("away_win_prob", 0)))
                confidence = Decimal(str(prediction_data.get("confidence", 0)))

                # Get recommendation (predicted outcome)
                recommendation = prediction_data.get("recommendation", "")
                # Map route format to internal format
                outcome_map = {
                    "home_win": "home",
                    "draw": "draw",
                    "away_win": "away",
                    "home": "home",
                    "away": "away",
                }
                predicted_outcome = outcome_map.get(recommendation, recommendation)

                # If no explicit recommendation, determine from probabilities
                if not predicted_outcome:
                    if home_prob >= draw_prob and home_prob >= away_prob:
                        predicted_outcome = "home"
                    elif draw_prob >= home_prob and draw_prob >= away_prob:
                        predicted_outcome = "draw"
                    else:
                        predicted_outcome = "away"

                # Prepare optional fields
                import json

                key_factors = prediction_data.get("key_factors")
                risk_factors = prediction_data.get("risk_factors")
                value_score = prediction_data.get("value_score")
                model_details = prediction_data.get("model_details")
                llm_adjustments = prediction_data.get("llm_adjustments")

                # Upsert the prediction with all LLM-generated content and model details
                await uow.predictions.upsert(
                    "match_id",
                    match.id,
                    home_prob=home_prob,
                    draw_prob=draw_prob,
                    away_prob=away_prob,
                    predicted_outcome=predicted_outcome,
                    confidence=confidence,
                    explanation=prediction_data.get("explanation"),
                    key_factors=json.dumps(key_factors) if key_factors else None,
                    risk_factors=json.dumps(risk_factors) if risk_factors else None,
                    value_score=Decimal(str(value_score)) if value_score else None,
                    model_details=json.dumps(model_details) if model_details else None,
                    llm_adjustments=json.dumps(llm_adjustments) if llm_adjustments else None,
                )

                await uow.commit()
                logger.info(f"Saved prediction for match {match.id}")
                return True

        except Exception as e:
            logger.error(f"Error saving prediction from API: {e}")
            return False

    @staticmethod
    async def get_all_statistics(days: int = 30) -> dict[str, Any]:
        """Get statistics for all predictions (including unverified).

        Replaces legacy get_all_predictions_stats() for route usage.
        Used when no verified predictions exist yet to show distribution data.

        Args:
            days: Number of days to look back (default 30).

        Returns:
            Dict with total_predictions, by_competition, by_bet_type.
        """
        try:
            async with get_uow() as uow:
                cutoff = datetime.now() - timedelta(days=days)

                # Query all predictions from the period
                # Note: we access competition_code directly (string field, not relationship)
                stmt = (
                    select(Prediction)
                    .join(Match)
                    .options(joinedload(Prediction.match))
                    .where(Prediction.created_at >= cutoff)
                )
                result = await uow.session.execute(stmt)
                predictions = result.scalars().unique().all()

                if not predictions:
                    return {
                        "total_predictions": 0,
                        "by_competition": {},
                        "by_bet_type": {},
                    }

                total = len(predictions)

                # Calculate by competition
                by_competition: dict[str, dict[str, Any]] = {}
                for p in predictions:
                    comp_code = (
                        p.match.competition_code
                        if p.match and p.match.competition_code
                        else "Unknown"
                    )
                    if comp_code not in by_competition:
                        by_competition[comp_code] = {"total": 0, "correct": 0, "accuracy": 0.0}
                    by_competition[comp_code]["total"] += 1

                # Calculate by bet type (predicted outcome)
                by_bet_type: dict[str, dict[str, Any]] = {}
                for p in predictions:
                    # Map internal format to route format
                    bet_type = p.predicted_outcome or "unknown"
                    outcome_map = {"home": "home_win", "away": "away_win", "draw": "draw"}
                    bet_type = outcome_map.get(bet_type, bet_type)

                    if bet_type not in by_bet_type:
                        by_bet_type[bet_type] = {"total": 0, "correct": 0, "accuracy": 0.0}
                    by_bet_type[bet_type]["total"] += 1

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

    @staticmethod
    async def generate_daily_picks() -> list[dict[str, Any]]:
        """Generate predictions for today's matches.

        Called by scheduler every day at 9:00 UTC.
        Returns list of generated picks.
        """
        from src.data.sources.football_data import (  # type: ignore[attr-defined]
            COMPETITIONS,
            get_football_data_client,
        )

        logger.info("Generating daily picks...")

        client = get_football_data_client()
        today = date.today()
        tomorrow = today + timedelta(days=1)

        all_picks = []
        matches_processed = 0

        for comp_code in COMPETITIONS.keys():
            try:
                matches = await client.get_matches(
                    competition=comp_code,
                    date_from=today,
                    date_to=tomorrow,
                    status="SCHEDULED",
                )

                for match in matches:
                    try:
                        # Import here to avoid circular imports
                        from src.api.routes.predictions import _generate_prediction_from_api_match

                        # Generate prediction with full model details for storage
                        pred = await _generate_prediction_from_api_match(
                            match, include_model_details=True, request=None
                        )

                        # Extract data for DB storage
                        model_details_for_db = None
                        if pred.model_contributions:
                            model_details_for_db = {
                                "poisson": (
                                    pred.model_contributions.poisson.model_dump()
                                    if pred.model_contributions.poisson
                                    else None
                                ),
                                "xgboost": (
                                    pred.model_contributions.xgboost.model_dump()
                                    if pred.model_contributions.xgboost
                                    else None
                                ),
                                "xg_model": (
                                    pred.model_contributions.xg_model.model_dump()
                                    if pred.model_contributions.xg_model
                                    else None
                                ),
                                "elo": (
                                    pred.model_contributions.elo.model_dump()
                                    if pred.model_contributions.elo
                                    else None
                                ),
                            }

                        llm_adjustments_for_db = None
                        if pred.llm_adjustments:
                            llm_adjustments_for_db = pred.llm_adjustments.model_dump()

                        # Save to DB
                        await PredictionService.save_prediction_from_api(
                            {
                                "match_id": match.id,
                                "match_external_id": f"{comp_code}_{match.id}",
                                "home_team": pred.home_team,
                                "away_team": pred.away_team,
                                "competition_code": comp_code,
                                "match_date": match.utcDate,
                                "home_win_prob": pred.probabilities.home_win,
                                "draw_prob": pred.probabilities.draw,
                                "away_win_prob": pred.probabilities.away_win,
                                "confidence": pred.confidence,
                                "recommendation": pred.recommended_bet,
                                "explanation": pred.explanation,
                                "key_factors": pred.key_factors,
                                "risk_factors": pred.risk_factors,
                                "value_score": pred.value_score,
                                "model_details": model_details_for_db,
                                "llm_adjustments": llm_adjustments_for_db,
                            }
                        )

                        all_picks.append(
                            {
                                "match_id": match.id,
                                "home_team": pred.home_team,
                                "away_team": pred.away_team,
                                "confidence": pred.confidence,
                                "recommendation": pred.recommended_bet,
                            }
                        )
                        matches_processed += 1

                    except Exception as match_err:
                        logger.warning(
                            f"Failed to generate prediction for match {match.id}: {match_err}"
                        )
                        continue

            except Exception as comp_err:
                if "403" not in str(comp_err):
                    logger.warning(f"Error fetching {comp_code} matches: {comp_err}")
                continue

        logger.info(f"Generated {len(all_picks)} daily picks from {matches_processed} matches")
        return all_picks
