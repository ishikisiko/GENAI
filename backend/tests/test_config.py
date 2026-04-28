from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.shared.config import load_config


def test_config_requires_database_url():
    with pytest.raises(ValidationError):
        load_config({"APP_NAME": "backend-test", "APP_ENV": "test"})


def test_config_accepts_override_values():
    cfg = load_config(
        {
            "APP_DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "APP_NAME": "backend-test",
            "APP_PORT": 9001,
        }
    )
    assert cfg.app_name == "backend-test"
    assert cfg.port == 9001


def test_config_defaults_to_real_external_providers():
    cfg = load_config({"APP_DATABASE_URL": "postgresql+asyncpg://localhost/db"})

    assert cfg.source_discovery_search_provider == "brave"
    assert cfg.source_discovery_content_fetcher == "http"
    assert cfg.semantic_embedding_provider == "openai_compatible"
    assert cfg.semantic_embedding_model == "text-embedding-3-small"
    assert cfg.semantic_fragment_maintenance_batch_size == 5


def test_config_accepts_semantic_embedding_overrides():
    cfg = load_config(
        {
            "APP_DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "SEMANTIC_EMBEDDING_PROVIDER": "openai_compatible",
            "SEMANTIC_EMBEDDING_BASE_URL": "https://ark.cn-beijing.volces.com/api/coding/v3",
            "SEMANTIC_EMBEDDING_MODEL": "doubao-embedding-vision",
            "SEMANTIC_EMBEDDING_API_KEY": "test-key",
        }
    )

    assert cfg.semantic_embedding_provider == "openai_compatible"
    assert cfg.semantic_embedding_model == "doubao-embedding-vision"
