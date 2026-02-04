"""Walk-forward backtesting framework for football predictions.

This module provides:
- Walk-forward validation methodology (train on N days, test on M following days)
- Comprehensive metrics: accuracy, Brier score, log loss, calibration error, ROI
- Model comparison across different time periods
- Performance tracking over rolling windows
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Literal

import numpy as np

from src.prediction_engine.ensemble import EnsemblePredictor, LLMAdjustments
from src.prediction_engine.feature_engineering import FeatureEngineer
from src.prediction_engine.models.xgboost_model import XGBoostModel

logger = logging.getLogger(__name__)


@dataclass
class CalibrationBin:
    """Calibration data for a probability bin."""

    bin_start: float
    bin_end: float
    predicted_prob: float  # Mean predicted probability in bin
    actual_rate: float  # Actual win rate in bin
    count: int  # Number of predictions in bin


@dataclass
class BacktestMetrics:
    """Comprehensive backtesting metrics."""

    # Basic metrics
    accuracy: float = 0.0
    total_predictions: int = 0
    correct_predictions: int = 0

    # Probabilistic metrics
    brier_score: float = 0.0  # Lower is better (0 = perfect)
    log_loss: float = 0.0  # Lower is better
    rps: float = 0.0  # Ranked Probability Score

    # Calibration
    calibration_error: float = 0.0  # Expected Calibration Error (ECE)
    calibration_bins: list[CalibrationBin] = field(default_factory=list)

    # ROI metrics (requires odds data)
    roi: float = 0.0  # Return on Investment (%)
    profit_units: float = 0.0  # Profit in units
    total_stake: float = 0.0  # Total units staked
    win_rate: float = 0.0  # Percentage of winning bets
    avg_odds: float = 0.0  # Average odds on bets placed

    # Per-outcome breakdown
    home_accuracy: float = 0.0
    draw_accuracy: float = 0.0
    away_accuracy: float = 0.0
    home_brier: float = 0.0
    draw_brier: float = 0.0
    away_brier: float = 0.0

    # Model agreement
    avg_model_agreement: float = 0.0
    avg_confidence: float = 0.0


@dataclass
class WalkForwardFold:
    """Results from a single walk-forward fold."""

    fold_number: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    train_size: int
    test_size: int
    metrics: BacktestMetrics


@dataclass
class BacktestResults:
    """Complete backtesting results."""

    # Overall metrics (aggregated across folds)
    overall_metrics: BacktestMetrics

    # Per-fold results
    folds: list[WalkForwardFold] = field(default_factory=list)

    # Time series of performance
    rolling_accuracy: list[tuple[date, float]] = field(default_factory=list)
    rolling_brier: list[tuple[date, float]] = field(default_factory=list)

    # Configuration
    train_window_days: int = 365
    test_window_days: int = 30
    min_confidence: float = 0.0
    betting_threshold: float = 0.55


@dataclass
class MatchData:
    """Match data for backtesting."""

    match_id: str
    match_date: date
    home_team: str
    away_team: str

    # Features
    home_attack: float
    home_defense: float
    away_attack: float
    away_defense: float
    home_xg: float | None = None
    away_xg: float | None = None
    home_elo: float | None = None
    away_elo: float | None = None
    recent_form_home: float | None = None
    recent_form_away: float | None = None

    # Actual outcome
    outcome: Literal["home", "draw", "away"] = "draw"
    home_goals: int = 0
    away_goals: int = 0

    # Odds (optional, for ROI calculation)
    odds_home: float | None = None
    odds_draw: float | None = None
    odds_away: float | None = None


class WalkForwardBacktest:
    """
    Walk-forward backtesting framework.

    Implements time-series cross-validation where:
    1. Train on data from [t-train_window, t]
    2. Test on data from [t, t+test_window]
    3. Move window forward and repeat

    This prevents look-ahead bias and simulates real-world usage.
    """

    def __init__(
        self,
        train_window_days: int = 365,
        test_window_days: int = 30,
        min_confidence: float = 0.0,
        betting_threshold: float = 0.55,
        n_calibration_bins: int = 10,
    ):
        """
        Initialize backtesting framework.

        Args:
            train_window_days: Number of days to use for training
            test_window_days: Number of days to test on before retraining
            min_confidence: Minimum confidence to include in metrics
            betting_threshold: Probability threshold for simulated betting
            n_calibration_bins: Number of bins for calibration analysis
        """
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.min_confidence = min_confidence
        self.betting_threshold = betting_threshold
        self.n_calibration_bins = n_calibration_bins

    def run(
        self,
        matches: list[MatchData],
        use_llm_adjustments: bool = False,
        retrain_ml: bool = True,
    ) -> BacktestResults:
        """
        Run walk-forward backtest on match data.

        Args:
            matches: List of historical matches with outcomes
            use_llm_adjustments: Whether to apply LLM adjustments (if available)
            retrain_ml: Whether to retrain ML models at each fold

        Returns:
            BacktestResults with comprehensive metrics
        """
        if not matches:
            logger.warning("No matches provided for backtesting")
            return self._empty_results()

        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda m: m.match_date)
        min_date = sorted_matches[0].match_date
        max_date = sorted_matches[-1].match_date

        logger.info(f"Running backtest on {len(matches)} matches from {min_date} to {max_date}")

        # Calculate number of folds
        total_days = (max_date - min_date).days
        available_test_days = total_days - self.train_window_days

        if available_test_days < self.test_window_days:
            logger.warning(
                f"Not enough data for walk-forward. Need {self.train_window_days + self.test_window_days} days, "
                f"have {total_days}"
            )
            return self._empty_results()

        folds: list[WalkForwardFold] = []
        all_predictions: list[dict[str, Any]] = []

        # Walk forward through time
        current_test_start = min_date + timedelta(days=self.train_window_days)
        fold_number = 0

        while current_test_start + timedelta(days=self.test_window_days) <= max_date:
            fold_number += 1
            train_start = current_test_start - timedelta(days=self.train_window_days)
            train_end = current_test_start - timedelta(days=1)
            test_start = current_test_start
            test_end = current_test_start + timedelta(days=self.test_window_days - 1)

            # Get train and test matches
            train_matches = [m for m in sorted_matches if train_start <= m.match_date <= train_end]
            test_matches = [m for m in sorted_matches if test_start <= m.match_date <= test_end]

            if not train_matches or not test_matches:
                current_test_start += timedelta(days=self.test_window_days)
                continue

            logger.debug(
                f"Fold {fold_number}: Train [{train_start} to {train_end}] ({len(train_matches)} matches), "
                f"Test [{test_start} to {test_end}] ({len(test_matches)} matches)"
            )

            # Train models on training data
            predictor = self._train_predictor(train_matches, retrain_ml)

            # Make predictions on test data
            fold_predictions = self._make_predictions(predictor, test_matches, use_llm_adjustments)
            all_predictions.extend(fold_predictions)

            # Calculate fold metrics
            fold_metrics = self._calculate_metrics(fold_predictions)

            fold = WalkForwardFold(
                fold_number=fold_number,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                train_size=len(train_matches),
                test_size=len(test_matches),
                metrics=fold_metrics,
            )
            folds.append(fold)

            # Move to next fold
            current_test_start += timedelta(days=self.test_window_days)

        # Calculate overall metrics
        overall_metrics = self._calculate_metrics(all_predictions)

        # Calculate rolling metrics
        rolling_accuracy = self._calculate_rolling_metrics(all_predictions, metric="accuracy")
        rolling_brier = self._calculate_rolling_metrics(all_predictions, metric="brier")

        return BacktestResults(
            overall_metrics=overall_metrics,
            folds=folds,
            rolling_accuracy=rolling_accuracy,
            rolling_brier=rolling_brier,
            train_window_days=self.train_window_days,
            test_window_days=self.test_window_days,
            min_confidence=self.min_confidence,
            betting_threshold=self.betting_threshold,
        )

    def _train_predictor(
        self,
        train_matches: list[MatchData],
        retrain_ml: bool,
    ) -> EnsemblePredictor:
        """Train ensemble predictor on training data."""
        predictor = EnsemblePredictor()

        if retrain_ml and len(train_matches) >= 50:
            # Prepare training data for XGBoost
            X, y = self._prepare_training_data(train_matches)

            if len(X) >= 50:
                try:
                    # Train XGBoost model
                    xgboost_model = XGBoostModel()
                    xgboost_model.train(X, y)
                    predictor.xgboost_model = xgboost_model
                except Exception as e:
                    logger.warning(f"Failed to train XGBoost: {e}")

            # Update ELO ratings based on historical results
            for match in train_matches:
                self._update_elo_from_match(predictor.elo, match)

        return predictor

    def _prepare_training_data(
        self,
        matches: list[MatchData],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and labels from matches."""
        features = []
        labels = []

        for match in matches:
            feature_vec = FeatureEngineer.engineer_features(
                home_attack=match.home_attack,
                home_defense=match.home_defense,
                away_attack=match.away_attack,
                away_defense=match.away_defense,
            )
            features.append(feature_vec.to_array())

            # Convert outcome to numeric
            outcome_map = {"home": 0, "draw": 1, "away": 2}
            labels.append(outcome_map.get(match.outcome, 1))

        return np.array(features), np.array(labels)

    def _update_elo_from_match(self, elo_system: Any, match: MatchData) -> None:
        """Update ELO ratings based on match result."""
        try:
            elo_system.update_ratings(
                home_team=match.home_team,
                away_team=match.away_team,
                home_goals=match.home_goals,
                away_goals=match.away_goals,
            )
        except Exception:
            pass  # ELO update failures are non-critical

    def _make_predictions(
        self,
        predictor: EnsemblePredictor,
        test_matches: list[MatchData],
        use_llm_adjustments: bool,
    ) -> list[dict[str, Any]]:
        """Make predictions on test matches."""
        predictions = []

        # Default ELO rating if not available
        DEFAULT_ELO = 1500.0

        for match in test_matches:
            try:
                # Get ELO ratings (use stored values or default)
                home_elo = match.home_elo or DEFAULT_ELO
                away_elo = match.away_elo or DEFAULT_ELO

                # Make ensemble prediction
                # xG data is optional - only pass if available
                pred = predictor.predict(
                    home_attack=match.home_attack,
                    home_defense=match.home_defense,
                    away_attack=match.away_attack,
                    away_defense=match.away_defense,
                    home_elo=home_elo,
                    away_elo=away_elo,
                    llm_adjustments=LLMAdjustments() if not use_llm_adjustments else None,
                )

                # Determine predicted outcome
                probs = [pred.home_win_prob, pred.draw_prob, pred.away_win_prob]
                outcomes = ["home", "draw", "away"]
                predicted_outcome = outcomes[np.argmax(probs)]

                # Determine actual outcome
                if match.home_goals > match.away_goals:
                    actual_outcome = "home"
                elif match.home_goals < match.away_goals:
                    actual_outcome = "away"
                else:
                    actual_outcome = "draw"

                predictions.append(
                    {
                        "match_id": match.match_id,
                        "match_date": match.match_date,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "prob_home": pred.home_win_prob,
                        "prob_draw": pred.draw_prob,
                        "prob_away": pred.away_win_prob,
                        "predicted": predicted_outcome,
                        "actual": actual_outcome,
                        "confidence": pred.confidence,
                        "model_agreement": pred.model_agreement,
                        "odds_home": match.odds_home,
                        "odds_draw": match.odds_draw,
                        "odds_away": match.odds_away,
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to predict match {match.match_id}: {e}")
                continue

        return predictions

    def _calculate_metrics(
        self,
        predictions: list[dict[str, Any]],
    ) -> BacktestMetrics:
        """Calculate comprehensive metrics from predictions."""
        if not predictions:
            return BacktestMetrics()

        # Filter by minimum confidence
        filtered = [p for p in predictions if p.get("confidence", 0) >= self.min_confidence]

        if not filtered:
            return BacktestMetrics()

        # Basic accuracy
        correct = sum(1 for p in filtered if p["predicted"] == p["actual"])
        accuracy = correct / len(filtered)

        # Per-outcome accuracy
        home_preds = [p for p in filtered if p["actual"] == "home"]
        draw_preds = [p for p in filtered if p["actual"] == "draw"]
        away_preds = [p for p in filtered if p["actual"] == "away"]

        home_accuracy = (
            sum(1 for p in home_preds if p["predicted"] == "home") / len(home_preds)
            if home_preds
            else 0.0
        )
        draw_accuracy = (
            sum(1 for p in draw_preds if p["predicted"] == "draw") / len(draw_preds)
            if draw_preds
            else 0.0
        )
        away_accuracy = (
            sum(1 for p in away_preds if p["predicted"] == "away") / len(away_preds)
            if away_preds
            else 0.0
        )

        # Brier score (lower is better, 0 = perfect)
        brier_scores = []
        home_brier_scores = []
        draw_brier_scores = []
        away_brier_scores = []

        for p in filtered:
            actual_probs = [
                1.0 if p["actual"] == "home" else 0.0,
                1.0 if p["actual"] == "draw" else 0.0,
                1.0 if p["actual"] == "away" else 0.0,
            ]
            predicted_probs = [p["prob_home"], p["prob_draw"], p["prob_away"]]

            # Multi-class Brier score
            brier = sum((pred - actual) ** 2 for pred, actual in zip(predicted_probs, actual_probs))
            brier_scores.append(brier)

            # Per-outcome Brier
            home_brier_scores.append((p["prob_home"] - actual_probs[0]) ** 2)
            draw_brier_scores.append((p["prob_draw"] - actual_probs[1]) ** 2)
            away_brier_scores.append((p["prob_away"] - actual_probs[2]) ** 2)

        brier_score = np.mean(brier_scores)
        home_brier = np.mean(home_brier_scores)
        draw_brier = np.mean(draw_brier_scores)
        away_brier = np.mean(away_brier_scores)

        # Log loss
        log_loss_val = self._calculate_log_loss(filtered)

        # Ranked Probability Score
        rps = self._calculate_rps(filtered)

        # Calibration
        calibration_error, calibration_bins = self._calculate_calibration(filtered)

        # ROI (if odds available)
        roi_metrics = self._calculate_roi(filtered)

        # Model agreement and confidence
        avg_agreement = np.mean([p.get("model_agreement", 0) for p in filtered])
        avg_confidence = np.mean([p.get("confidence", 0) for p in filtered])

        return BacktestMetrics(
            accuracy=accuracy,
            total_predictions=len(filtered),
            correct_predictions=correct,
            brier_score=brier_score,
            log_loss=log_loss_val,
            rps=rps,
            calibration_error=calibration_error,
            calibration_bins=calibration_bins,
            roi=roi_metrics["roi"],
            profit_units=roi_metrics["profit"],
            total_stake=roi_metrics["stake"],
            win_rate=roi_metrics["win_rate"],
            avg_odds=roi_metrics["avg_odds"],
            home_accuracy=home_accuracy,
            draw_accuracy=draw_accuracy,
            away_accuracy=away_accuracy,
            home_brier=home_brier,
            draw_brier=draw_brier,
            away_brier=away_brier,
            avg_model_agreement=avg_agreement,
            avg_confidence=avg_confidence,
        )

    def _calculate_log_loss(self, predictions: list[dict[str, Any]]) -> float:
        """Calculate multi-class log loss."""
        eps = 1e-15
        log_loss_sum = 0.0

        for p in predictions:
            actual = p["actual"]
            if actual == "home":
                prob = np.clip(p["prob_home"], eps, 1 - eps)
            elif actual == "draw":
                prob = np.clip(p["prob_draw"], eps, 1 - eps)
            else:
                prob = np.clip(p["prob_away"], eps, 1 - eps)

            log_loss_sum -= np.log(prob)

        return log_loss_sum / len(predictions) if predictions else 0.0

    def _calculate_rps(self, predictions: list[dict[str, Any]]) -> float:
        """Calculate Ranked Probability Score (ordinal metric)."""
        rps_sum = 0.0

        for p in predictions:
            # Cumulative probabilities
            pred_cum = np.cumsum([p["prob_home"], p["prob_draw"], p["prob_away"]])

            # Actual cumulative
            actual_idx = {"home": 0, "draw": 1, "away": 2}[p["actual"]]
            actual_cum = np.array([1.0 if i >= actual_idx else 0.0 for i in range(3)])

            # RPS
            rps = np.mean((pred_cum - actual_cum) ** 2)
            rps_sum += rps

        return rps_sum / len(predictions) if predictions else 0.0

    def _calculate_calibration(
        self,
        predictions: list[dict[str, Any]],
    ) -> tuple[float, list[CalibrationBin]]:
        """Calculate Expected Calibration Error and calibration bins."""
        bins: list[CalibrationBin] = []
        bin_width = 1.0 / self.n_calibration_bins

        # Use home win probability for calibration analysis
        for i in range(self.n_calibration_bins):
            bin_start = i * bin_width
            bin_end = (i + 1) * bin_width

            # Get predictions in this bin (for home win probability)
            in_bin = [p for p in predictions if bin_start <= p["prob_home"] < bin_end]

            if in_bin:
                mean_pred = np.mean([p["prob_home"] for p in in_bin])
                actual_rate = np.mean([1.0 if p["actual"] == "home" else 0.0 for p in in_bin])

                bins.append(
                    CalibrationBin(
                        bin_start=bin_start,
                        bin_end=bin_end,
                        predicted_prob=mean_pred,
                        actual_rate=actual_rate,
                        count=len(in_bin),
                    )
                )

        # Calculate ECE (weighted by bin size)
        ece = 0.0
        total = sum(b.count for b in bins)
        if total > 0:
            for b in bins:
                ece += (b.count / total) * abs(b.predicted_prob - b.actual_rate)

        return ece, bins

    def _calculate_roi(
        self,
        predictions: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculate ROI metrics for simulated betting."""
        total_stake = 0.0
        total_return = 0.0
        wins = 0
        odds_sum = 0.0
        bets_placed = 0

        for p in predictions:
            # Check if we have odds
            odds_map = {
                "home": p.get("odds_home"),
                "draw": p.get("odds_draw"),
                "away": p.get("odds_away"),
            }
            prob_map = {
                "home": p["prob_home"],
                "draw": p["prob_draw"],
                "away": p["prob_away"],
            }

            # Find best value bet
            best_outcome = None
            best_value = 0.0

            for outcome in ["home", "draw", "away"]:
                odds = odds_map.get(outcome)
                prob = prob_map.get(outcome, 0)

                if odds and prob >= self.betting_threshold:
                    implied_prob = 1.0 / odds
                    value = prob - implied_prob

                    if value > best_value:
                        best_value = value
                        best_outcome = outcome

            # Place bet if value found
            if best_outcome:
                stake = 1.0  # Unit stake
                total_stake += stake
                odds = odds_map[best_outcome]
                odds_sum += odds
                bets_placed += 1

                if p["actual"] == best_outcome:
                    total_return += stake * odds
                    wins += 1

        # Calculate ROI
        profit = total_return - total_stake
        roi = (profit / total_stake * 100) if total_stake > 0 else 0.0
        win_rate = (wins / bets_placed * 100) if bets_placed > 0 else 0.0
        avg_odds = (odds_sum / bets_placed) if bets_placed > 0 else 0.0

        return {
            "roi": roi,
            "profit": profit,
            "stake": total_stake,
            "win_rate": win_rate,
            "avg_odds": avg_odds,
        }

    def _calculate_rolling_metrics(
        self,
        predictions: list[dict[str, Any]],
        metric: Literal["accuracy", "brier"] = "accuracy",
        window_size: int = 50,
    ) -> list[tuple[date, float]]:
        """Calculate rolling metrics over time."""
        if len(predictions) < window_size:
            return []

        # Sort by date
        sorted_preds = sorted(predictions, key=lambda p: p["match_date"])
        results: list[tuple[date, float]] = []

        for i in range(window_size, len(sorted_preds) + 1):
            window = sorted_preds[i - window_size : i]
            end_date = window[-1]["match_date"]

            if metric == "accuracy":
                correct = sum(1 for p in window if p["predicted"] == p["actual"])
                value = correct / len(window)
            else:  # brier
                brier_sum = 0.0
                for p in window:
                    actual_probs = [
                        1.0 if p["actual"] == "home" else 0.0,
                        1.0 if p["actual"] == "draw" else 0.0,
                        1.0 if p["actual"] == "away" else 0.0,
                    ]
                    predicted_probs = [p["prob_home"], p["prob_draw"], p["prob_away"]]
                    brier = sum(
                        (pred - actual) ** 2 for pred, actual in zip(predicted_probs, actual_probs)
                    )
                    brier_sum += brier
                value = brier_sum / len(window)

            results.append((end_date, value))

        return results

    def _empty_results(self) -> BacktestResults:
        """Return empty results for edge cases."""
        return BacktestResults(
            overall_metrics=BacktestMetrics(),
            train_window_days=self.train_window_days,
            test_window_days=self.test_window_days,
            min_confidence=self.min_confidence,
            betting_threshold=self.betting_threshold,
        )


def format_backtest_report(results: BacktestResults) -> str:
    """Format backtest results as a human-readable report."""
    m = results.overall_metrics
    lines = [
        "=" * 60,
        "WALK-FORWARD BACKTEST REPORT",
        "=" * 60,
        "",
        "Configuration:",
        f"  Train window: {results.train_window_days} days",
        f"  Test window:  {results.test_window_days} days",
        f"  Min confidence: {results.min_confidence:.2f}",
        f"  Betting threshold: {results.betting_threshold:.2f}",
        "",
        f"Overall Results ({len(results.folds)} folds):",
        f"  Total predictions: {m.total_predictions}",
        f"  Correct predictions: {m.correct_predictions}",
        "",
        "Accuracy Metrics:",
        f"  Overall accuracy:  {m.accuracy:.2%}",
        f"  Home accuracy:     {m.home_accuracy:.2%}",
        f"  Draw accuracy:     {m.draw_accuracy:.2%}",
        f"  Away accuracy:     {m.away_accuracy:.2%}",
        "",
        "Probabilistic Metrics:",
        f"  Brier score:       {m.brier_score:.4f} (lower is better)",
        f"  Log loss:          {m.log_loss:.4f} (lower is better)",
        f"  RPS:               {m.rps:.4f} (lower is better)",
        f"  Calibration error: {m.calibration_error:.4f} (lower is better)",
        "",
        "Betting Simulation:",
        f"  ROI:           {m.roi:+.2f}%",
        f"  Profit:        {m.profit_units:+.2f} units",
        f"  Total stake:   {m.total_stake:.1f} units",
        f"  Win rate:      {m.win_rate:.2f}%",
        f"  Avg odds:      {m.avg_odds:.2f}",
        "",
        "Model Performance:",
        f"  Avg confidence:    {m.avg_confidence:.2%}",
        f"  Avg model agreement: {m.avg_model_agreement:.2%}",
        "",
    ]

    # Calibration bins
    if m.calibration_bins:
        lines.append("Calibration (Home Win):")
        lines.append("  Bin Range    | Predicted | Actual | Count")
        lines.append("  " + "-" * 44)
        for b in m.calibration_bins:
            lines.append(
                f"  [{b.bin_start:.2f}-{b.bin_end:.2f}] | "
                f"{b.predicted_prob:.3f}     | {b.actual_rate:.3f}  | {b.count}"
            )
        lines.append("")

    # Per-fold summary
    if results.folds:
        lines.append("Per-Fold Results:")
        lines.append("  Fold | Test Period          | Tests | Accuracy | Brier")
        lines.append("  " + "-" * 55)
        for fold in results.folds:
            lines.append(
                f"  {fold.fold_number:4d} | {fold.test_start} - {fold.test_end} | "
                f"{fold.test_size:5d} | {fold.metrics.accuracy:7.2%} | {fold.metrics.brier_score:.4f}"
            )

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


# CLI entry point for validation
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run backtest validation")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation with synthetic data",
    )
    args = parser.parse_args()

    if args.validate:
        # Generate synthetic data for validation
        print("Running validation with synthetic data...")

        synthetic_matches = []
        start_date = date(2023, 1, 1)

        for i in range(500):
            match_date = start_date + timedelta(days=i // 2)
            outcome = np.random.choice(["home", "draw", "away"], p=[0.45, 0.25, 0.30])

            if outcome == "home":
                home_goals, away_goals = 2, 1
            elif outcome == "draw":
                home_goals, away_goals = 1, 1
            else:
                home_goals, away_goals = 0, 2

            synthetic_matches.append(
                MatchData(
                    match_id=f"match_{i}",
                    match_date=match_date,
                    home_team=f"Team_{i % 20}",
                    away_team=f"Team_{(i + 10) % 20}",
                    home_attack=1.2 + np.random.random() * 0.4,
                    home_defense=1.2 + np.random.random() * 0.4,
                    away_attack=1.1 + np.random.random() * 0.4,
                    away_defense=1.2 + np.random.random() * 0.4,
                    outcome=outcome,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    odds_home=1.8 + np.random.random() * 0.5,
                    odds_draw=3.2 + np.random.random() * 0.6,
                    odds_away=3.5 + np.random.random() * 1.0,
                )
            )

        # Run backtest
        backtest = WalkForwardBacktest(
            train_window_days=180,
            test_window_days=30,
            betting_threshold=0.50,
        )

        results = backtest.run(synthetic_matches, retrain_ml=False)
        print(format_backtest_report(results))
        print("\nValidation completed successfully!")
