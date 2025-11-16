"""
Application configuration and settings management.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Artemis Insight"
    app_env: str = "development"
    debug: bool = True

    # MongoDB
    mongo_uri: str

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "artemis-insight"
    minio_secure: bool = False

    # Redis/Celery
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Cost Management
    monthly_budget_zar: int = 1000


# Global settings instance
settings = Settings()
