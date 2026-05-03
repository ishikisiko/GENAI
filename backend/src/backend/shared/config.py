from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _BACKEND_ROOT.parent


class BackendConfig(BaseSettings):
    """Typed configuration for both API and worker runtimes."""

    model_config = SettingsConfigDict(
        env_file=(
            _REPO_ROOT / ".env",
            _REPO_ROOT / ".env.local",
            _BACKEND_ROOT / ".env",
        ),
        env_prefix="",
        extra="ignore",
        validate_default=True,
        populate_by_name=False,
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
    product_auth_mode: Literal["public", "require_bearer"] = Field(default="public", alias="APP_PRODUCT_AUTH_MODE")
    database_url: str = Field(..., alias="APP_DATABASE_URL")
    cors_origins: str = Field(default="*", alias="APP_CORS_ORIGINS")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")
    redis_requirement_mode: Literal["optional", "required"] = Field(default="optional", alias="REDIS_REQUIREMENT_MODE")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    redis_operation_timeout_seconds: float = Field(default=1.0, gt=0.0, alias="REDIS_OPERATION_TIMEOUT_SECONDS")
    redis_rate_limit_enabled: bool = Field(default=False, alias="REDIS_RATE_LIMIT_ENABLED")
    redis_rate_limit_window_seconds: int = Field(default=60, ge=1, alias="REDIS_RATE_LIMIT_WINDOW_SECONDS")
    redis_rate_limit_simulations: int = Field(default=5, ge=1, alias="REDIS_RATE_LIMIT_SIMULATIONS")
    redis_rate_limit_agent_generation: int = Field(default=5, ge=1, alias="REDIS_RATE_LIMIT_AGENT_GENERATION")
    redis_rate_limit_source_discovery_jobs: int = Field(
        default=10,
        ge=1,
        alias="REDIS_RATE_LIMIT_SOURCE_DISCOVERY_JOBS",
    )
    redis_rate_limit_source_discovery_assistant: int = Field(
        default=10,
        ge=1,
        alias="REDIS_RATE_LIMIT_SOURCE_DISCOVERY_ASSISTANT",
    )
    redis_cache_enabled: bool = Field(default=False, alias="REDIS_CACHE_ENABLED")
    redis_cache_llm_ttl_seconds: int = Field(default=300, ge=0, alias="REDIS_CACHE_LLM_TTL_SECONDS")
    redis_cache_search_ttl_seconds: int = Field(default=600, ge=0, alias="REDIS_CACHE_SEARCH_TTL_SECONDS")
    redis_cache_content_ttl_seconds: int = Field(default=3600, ge=0, alias="REDIS_CACHE_CONTENT_TTL_SECONDS")
    redis_stream_dispatch_enabled: bool = Field(default=False, alias="REDIS_STREAM_DISPATCH_ENABLED")
    redis_stream_name: str = Field(default="genai:jobs", alias="REDIS_STREAM_NAME")
    redis_stream_group: str = Field(default="genai-workers", alias="REDIS_STREAM_GROUP")
    redis_stream_read_block_ms: int = Field(default=100, ge=0, alias="REDIS_STREAM_READ_BLOCK_MS")
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
    source_discovery_search_provider: Literal["mock", "brave"] = Field(
        default="brave",
        alias="SOURCE_DISCOVERY_SEARCH_PROVIDER",
    )
    source_discovery_content_fetcher: Literal["http", "mock"] = Field(
        default="http",
        alias="SOURCE_DISCOVERY_CONTENT_FETCHER",
    )
    brave_search_api_key: str | None = Field(default=None, alias="BRAVE_SEARCH_API_KEY")
    brave_search_endpoint: str = Field(
        default="https://api.search.brave.com/res/v1/web/search",
        alias="BRAVE_SEARCH_ENDPOINT",
    )
    brave_search_count: int = Field(default=10, ge=1, le=20, alias="BRAVE_SEARCH_COUNT")
    brave_search_country: str = Field(default="us", alias="BRAVE_SEARCH_COUNTRY")
    brave_search_lang: str = Field(default="en", alias="BRAVE_SEARCH_LANG")
    brave_search_rate_limit_seconds: float = Field(
        default=1.0,
        ge=0.0,
        alias="BRAVE_SEARCH_RATE_LIMIT_SECONDS",
    )
    semantic_embedding_provider: Literal["local", "openai_compatible"] = Field(
        default="openai_compatible",
        alias="SEMANTIC_EMBEDDING_PROVIDER",
    )
    semantic_embedding_api_key: str | None = Field(default=None, alias="SEMANTIC_EMBEDDING_API_KEY")
    semantic_embedding_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="SEMANTIC_EMBEDDING_BASE_URL",
    )
    semantic_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="SEMANTIC_EMBEDDING_MODEL",
    )
    semantic_embedding_timeout_seconds: float = Field(
        default=10.0,
        gt=0.0,
        alias="SEMANTIC_EMBEDDING_TIMEOUT_SECONDS",
    )
    semantic_fragment_maintenance_batch_size: int = Field(
        default=5,
        ge=0,
        le=50,
        alias="SEMANTIC_FRAGMENT_MAINTENANCE_BATCH_SIZE",
    )

    def __init__(self, **values: object) -> None:
        alias_by_name = {
            name: field.alias
            for name, field in type(self).model_fields.items()
            if isinstance(field.alias, str)
        }
        normalized_values = {
            alias_by_name.get(key, key) if not key.startswith("_") else key: value
            for key, value in values.items()
        }
        super().__init__(**normalized_values)

    def allowed_cors_origins(self) -> list[str]:
        raw = [item.strip() for item in self.cors_origins.split(",")]
        values = [item for item in raw if item]
        return values or ["*"]


def load_config(overrides: dict[str, object] | None = None) -> BackendConfig:
    """Load and validate backend config from environment with optional overrides."""

    if overrides is None:
        return BackendConfig()
    overrides = {"_env_file": None, **overrides}
    return BackendConfig(**overrides)
