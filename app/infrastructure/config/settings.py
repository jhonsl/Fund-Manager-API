"""Application configuration loaded from environment variables.

Uses pydantic-settings so values can come from a local ``.env`` file during
development or from real environment variables in AWS. Never hardcode secrets.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    environment: str = "local"  # local | dev | prod
    debug: bool = False
    port: int = 8080

    # --- AWS / DynamoDB ---
    aws_region: str = "us-east-1"
    dynamodb_table_name: str = "fund_manager"
    # Optional local DynamoDB endpoint (e.g. http://localhost:8000). Empty = real AWS.
    dynamodb_endpoint_url: str | None = None

    # --- Security (placeholders; wired up when auth is implemented) ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth)."""
    return Settings()
