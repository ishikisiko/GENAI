from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_cache_key(feature: str, parts: dict[str, Any], version: str = "v1") -> str:
    normalized = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    safe_feature = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in feature)
    safe_version = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in version)
    return f"genai:{safe_feature}:{safe_version}:{digest}"


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
