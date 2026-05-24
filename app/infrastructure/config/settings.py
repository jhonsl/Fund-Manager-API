"""Application configuration loaded from environment variables.

Uses pydantic-settings so values can come from a local ``.env`` file during
development or from real environment variables in AWS. Never hardcode secrets.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-production"


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

    # --- Security ---
    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    @model_validator(mode="after")
    def _reject_default_secret_in_prod(self) -> "Settings":
        if self.environment == "prod" and self.jwt_secret_key == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY must be overridden in production "
                "(set it via env var / AWS Secrets Manager)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth)."""
    return Settings()
