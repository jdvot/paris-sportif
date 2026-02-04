"""ML Model repository for storing and retrieving trained models."""

import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import MLModel
from src.db.repositories.base import BaseRepository


class MLModelRepository(BaseRepository[MLModel]):
    """Repository for MLModel operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MLModel, session)

    async def get_by_name(self, model_name: str) -> MLModel | None:
        """Get model by name."""
        return await self.get_by_field("model_name", model_name)

    async def get_active_model(self, model_type: str | None = None) -> MLModel | None:
        """Get the currently active model, optionally filtered by type."""
        stmt = select(MLModel).where(MLModel.is_active == True)  # noqa: E712
        if model_type:
            stmt = stmt.where(MLModel.model_type == model_type)
        stmt = stmt.order_by(MLModel.trained_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_metadata(self) -> Sequence[dict]:
        """Get all models metadata (without binary data)."""
        stmt = select(
            MLModel.id,
            MLModel.model_name,
            MLModel.model_type,
            MLModel.version,
            MLModel.accuracy,
            MLModel.precision,
            MLModel.recall,
            MLModel.f1_score,
            MLModel.training_samples,
            MLModel.is_active,
            MLModel.trained_at,
            MLModel.created_at,
        ).order_by(MLModel.trained_at.desc())
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": row.id,
                "model_name": row.model_name,
                "model_type": row.model_type,
                "version": row.version,
                "accuracy": float(row.accuracy) if row.accuracy else None,
                "precision": float(row.precision) if row.precision else None,
                "recall": float(row.recall) if row.recall else None,
                "f1_score": float(row.f1_score) if row.f1_score else None,
                "training_samples": row.training_samples,
                "is_active": row.is_active,
                "trained_at": row.trained_at.isoformat() if row.trained_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def save_model(
        self,
        model_name: str,
        model_type: str,
        version: str,
        accuracy: float,
        training_samples: int,
        feature_columns: list[str],
        model_binary: bytes,
        scaler_binary: bytes | None = None,
        *,
        set_active: bool = False,
    ) -> MLModel:
        """Save a trained ML model.

        Replaces: src.data.database.save_ml_model()
        """
        # Check if model exists
        existing = await self.get_by_name(model_name)

        if existing:
            # Update existing model
            existing.model_type = model_type
            existing.version = version
            existing.accuracy = accuracy
            existing.training_samples = training_samples
            existing.feature_columns = json.dumps(feature_columns)
            existing.model_binary = model_binary
            existing.scaler_binary = scaler_binary
            existing.trained_at = datetime.now()
            if set_active:
                existing.is_active = True
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        # Create new model
        model = await self.create(
            model_name=model_name,
            model_type=model_type,
            version=version,
            accuracy=accuracy,
            training_samples=training_samples,
            feature_columns=json.dumps(feature_columns),
            model_binary=model_binary,
            scaler_binary=scaler_binary,
            trained_at=datetime.now(),
            is_active=set_active,
        )
        return model

    async def load_model(self, model_name: str) -> dict | None:
        """Load a model with its binary data.

        Replaces: src.data.database.get_ml_model()
        """
        model = await self.get_by_name(model_name)
        if not model:
            return None

        return {
            "id": model.id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "version": model.version,
            "accuracy": float(model.accuracy) if model.accuracy else None,
            "training_samples": model.training_samples,
            "feature_columns": (json.loads(model.feature_columns) if model.feature_columns else []),
            "model_binary": model.model_binary,
            "scaler_binary": model.scaler_binary,
            "trained_at": model.trained_at.isoformat() if model.trained_at else None,
        }

    async def set_active(self, model_name: str) -> bool:
        """Set a model as the active model (deactivates others of same type)."""
        model = await self.get_by_name(model_name)
        if not model:
            return False

        # Deactivate other models of same type
        await self.update_many("model_type", model.model_type, is_active=False)

        # Activate this model
        model.is_active = True
        await self.session.flush()
        return True

    async def get_by_type(self, model_type: str) -> Sequence[MLModel]:
        """Get all models of a specific type."""
        return await self.get_many_by_field("model_type", model_type)

    async def get_best_model(self, model_type: str) -> MLModel | None:
        """Get the model with highest accuracy for a type."""
        stmt = (
            select(MLModel)
            .where(MLModel.model_type == model_type)
            .where(MLModel.accuracy.isnot(None))
            .order_by(MLModel.accuracy.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
