from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendConfig(BaseSettings):
    """Typed configuration for both API and worker runtimes."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
        validate_default=True,
        populate_by_name=True,
    )

    app_name: str = Field(default="python-backend-foundation", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="APP_HOST")
    port: int = Field(default=8000, alias="APP_PORT")
    request_timeout_seconds: int = Field(default=5, alias="APP_REQUEST_TIMEOUT_SECONDS")
    worker_poll_interval_seconds: float = Field(default=1.0, alias="APP_WORKER_POLL_INTERVAL_SECONDS")
    worker_batch_size: int = Field(default=5, alias="APP_WORKER_BATCH_SIZE")
    database_url: str = Field(..., alias="APP_DATABASE_URL")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")


def load_config(overrides: dict[str, object] | None = None) -> BackendConfig:
    """Load and validate backend config from environment with optional overrides."""

    if overrides is None:
        overrides = {}
    return BackendConfig(**overrides)
