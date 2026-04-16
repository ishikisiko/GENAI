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
