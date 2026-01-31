"""Custom exceptions for the application."""

from typing import Any


class ParisportifError(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DataSourceError(ParisportifError):
    """Error fetching data from external source."""

    pass


class FootballDataAPIError(DataSourceError):
    """Error from football-data.org API."""

    pass


class PredictionError(ParisportifError):
    """Error during prediction calculation."""

    pass


class InsufficientDataError(PredictionError):
    """Not enough data to make a prediction."""

    pass


class ModelNotTrainedError(PredictionError):
    """ML model not trained yet."""

    pass


class LLMError(ParisportifError):
    """Error from LLM API."""

    pass


class CacheError(ParisportifError):
    """Error with cache operations."""

    pass


class DatabaseError(ParisportifError):
    """Database operation error."""

    pass


class ValidationError(ParisportifError):
    """Data validation error."""

    pass


class RateLimitError(ParisportifError):
    """Rate limit exceeded."""

    pass
