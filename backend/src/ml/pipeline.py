"""Automated ML pipeline for data collection and model retraining.

Provides scheduled tasks for:
- Weekly data collection (new match results)
- Weekly model retraining
- Model performance monitoring
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).parent
DATA_DIR = ML_DIR / "data"
MODELS_DIR = ML_DIR / "trained_models"


class MLPipeline:
    """Automated ML pipeline manager."""

    def __init__(self) -> None:
        """Initialize pipeline."""
        self.last_collection: datetime | None = None
        self.last_training: datetime | None = None
        self.is_running = False

    async def collect_new_data(self) -> bool:
        """
        Collect new match data from API.

        Returns:
            True if collection successful
        """
        from .data_collector import HistoricalDataCollector

        logger.info("Starting data collection...")
        try:
            collector = HistoricalDataCollector()

            # Get current season only for updates
            current_year = datetime.now().year
            current_month = datetime.now().month

            # Football season runs Aug-May, so adjust year
            if current_month < 8:
                season = current_year - 1
            else:
                season = current_year

            await collector.collect_all_historical_data(
                seasons=[season - 2, season - 1, season],  # Last 3 seasons
                competitions=["PL", "PD", "BL1", "SA", "FL1"],
            )

            self.last_collection = datetime.now()
            logger.info("Data collection completed successfully")
            return True

        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            return False

    def retrain_models(self) -> bool:
        """
        Retrain ML models with latest data.

        Returns:
            True if training successful
        """
        from .model_loader import model_loader
        from .trainer import MLTrainer

        logger.info("Starting model retraining...")
        try:
            trainer = MLTrainer()
            success = trainer.train_all()

            if success:
                # Reload models in the loader
                model_loader.reload_models()
                self.last_training = datetime.now()
                logger.info("Model retraining completed successfully")

            return success

        except Exception as e:
            logger.error(f"Model retraining failed: {e}")
            return False

    async def run_full_pipeline(self) -> bool:
        """
        Run complete pipeline: collect data + retrain models.

        Returns:
            True if all steps successful
        """
        logger.info("=" * 50)
        logger.info("Starting full ML pipeline")
        logger.info("=" * 50)

        # Step 1: Collect data
        collection_success = await self.collect_new_data()
        if not collection_success:
            logger.error("Pipeline aborted: data collection failed")
            return False

        # Step 2: Retrain models
        training_success = self.retrain_models()
        if not training_success:
            logger.error("Pipeline completed with warnings: training failed")
            return False

        logger.info("=" * 50)
        logger.info("Full ML pipeline completed successfully!")
        logger.info("=" * 50)
        return True

    def should_collect_data(self, max_age_days: int = 7) -> bool:
        """Check if data collection is needed."""
        from .data_collector import HistoricalDataCollector

        collector = HistoricalDataCollector()
        age = collector.get_data_age_days()

        if age is None:
            return True  # No data exists
        return age >= max_age_days

    def should_retrain(self, max_age_days: int = 7) -> bool:
        """Check if model retraining is needed."""
        xgb_path = MODELS_DIR / "xgboost_latest.pkl"
        rf_path = MODELS_DIR / "random_forest_latest.pkl"

        # No models exist
        if not xgb_path.exists() and not rf_path.exists():
            return True

        # Check model age
        for path in [xgb_path, rf_path]:
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                age = (datetime.now() - mtime).days
                if age >= max_age_days:
                    return True

        return False

    async def scheduled_task(self, interval_hours: int = 168) -> None:  # Default: weekly
        """
        Background task that runs the pipeline on schedule.

        Args:
            interval_hours: Hours between pipeline runs (default: 168 = 1 week)
        """
        self.is_running = True
        logger.info(f"Starting scheduled ML pipeline (interval: {interval_hours}h)")

        while self.is_running:
            try:
                # Check if we need to run
                if self.should_collect_data() or self.should_retrain():
                    await self.run_full_pipeline()
                else:
                    logger.info("Pipeline skipped: data and models are fresh")

            except Exception as e:
                logger.error(f"Scheduled pipeline error: {e}")

            # Wait for next run
            await asyncio.sleep(interval_hours * 3600)

    def stop(self) -> None:
        """Stop the scheduled task."""
        self.is_running = False


# Global pipeline instance
ml_pipeline = MLPipeline()


async def start_ml_scheduler() -> None:
    """Start the ML pipeline scheduler as a background task."""
    asyncio.create_task(ml_pipeline.scheduled_task())
    logger.info("ML scheduler started")


async def run_pipeline_now() -> bool:
    """Run the ML pipeline immediately."""
    return await ml_pipeline.run_full_pipeline()


# CLI interface
async def main() -> None:
    """Command-line interface for pipeline operations."""
    import argparse

    parser = argparse.ArgumentParser(description="ML Pipeline Operations")
    parser.add_argument("command", choices=["collect", "train", "full", "status"])

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    pipeline = MLPipeline()

    if args.command == "collect":
        await pipeline.collect_new_data()

    elif args.command == "train":
        pipeline.retrain_models()

    elif args.command == "full":
        await pipeline.run_full_pipeline()

    elif args.command == "status":
        print("\n=== ML Pipeline Status ===")
        print(f"Should collect data: {pipeline.should_collect_data()}")
        print(f"Should retrain: {pipeline.should_retrain()}")

        from .data_collector import HistoricalDataCollector

        collector = HistoricalDataCollector()
        age = collector.get_data_age_days()
        print(f"Data age: {age} days" if age else "No data collected")

        from .model_loader import model_loader

        print(f"Models loaded: {model_loader.is_trained()}")


if __name__ == "__main__":
    asyncio.run(main())
