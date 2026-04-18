from __future__ import annotations

from typing import Literal

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
    cors_origins: str = Field(default="*", alias="APP_CORS_ORIGINS")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")
    anthropic_model: str | None = Field(default=None, alias="ANTHROPIC_MODEL")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    anthropic_base_url: str | None = Field(default=None, alias="ANTHROPIC_BASE_URL")
    llm_provider: Literal["openai", "anthropic"] | None = Field(default=None, alias="LLM_PROVIDER")
    llm_request_timeout_ms: int = Field(default=120000, alias="LLM_REQUEST_TIMEOUT_MS")
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    simulation_stale_timeout_seconds: int = Field(default=1200, alias="SIMULATION_STALE_RUN_TIMEOUT_SECONDS")

    def allowed_cors_origins(self) -> list[str]:
        raw = [item.strip() for item in self.cors_origins.split(",")]
        values = [item for item in raw if item]
        return values or ["*"]


def load_config(overrides: dict[str, object] | None = None) -> BackendConfig:
    """Load and validate backend config from environment with optional overrides."""

    if overrides is None:
        overrides = {}
    return BackendConfig(**overrides)
