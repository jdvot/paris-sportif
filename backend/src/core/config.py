"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not defined in the model
    )

    # App
    app_name: str = "WinRate AI API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = (
        "postgresql+asyncpg://paris_sportif:paris_sportif_secret@localhost:5432/paris_sportif"
    )

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Qdrant (Vector DB for semantic search)
    qdrant_url: str = "http://localhost:6333"  # Or Qdrant Cloud URL
    qdrant_api_key: str = ""  # Required for Qdrant Cloud

    # External APIs
    football_data_api_key: str = ""
    groq_api_key: str = ""  # Free LLM - https://console.groq.com/
    anthropic_api_key: str = ""  # Optional paid alternative

    # Stripe
    stripe_api_key: str = ""  # sk_test_... or sk_live_...
    stripe_webhook_secret: str = ""  # whsec_...
    stripe_price_premium: str = "price_premium_monthly"  # Price ID for Premium plan
    stripe_price_elite: str = "price_elite_monthly"  # Price ID for Elite plan

    # API Settings
    api_v1_prefix: str = "/api/v1"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Cache TTLs (seconds)
    cache_ttl_matches: int = 300  # 5 minutes
    cache_ttl_predictions: int = 1800  # 30 minutes
    cache_ttl_teams: int = 86400  # 24 hours

    # Prediction Settings
    prediction_min_confidence: float = 0.5
    prediction_min_value: float = 0.05  # 5% minimum value
    daily_picks_count: int = 5

    # LLM Settings
    llm_max_adjustment: float = 0.5  # Maximum LLM adjustment factor
    llm_cache_ttl: int = 3600  # 1 hour

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
