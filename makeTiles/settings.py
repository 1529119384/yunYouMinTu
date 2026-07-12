from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "app" / "data"
CONFIG_PATH = DATA_DIR / "config.json"

_lock = threading.Lock()

DEFAULTS: dict[str, Any] = {
    "max_image_bytes": 200 * 1024 * 1024,
    "cors_origins": ["*"],
    "tile_cache_max_age": 365 * 24 * 60 * 60,
    "max_job_age_seconds": 3600,
    "subprocess_timeout": 600,
}

_settings: dict[str, Any] = dict(DEFAULTS)


def load_settings() -> None:
    global _settings
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            _settings = {**DEFAULTS, **saved}
        except Exception:
            _settings = dict(DEFAULTS)
    else:
        _settings = dict(DEFAULTS)


def get_settings() -> dict[str, Any]:
    with _lock:
        return dict(_settings)


def update_settings(data: dict[str, Any]) -> dict[str, Any]:
    global _settings
    with _lock:
        allowed = set(DEFAULTS.keys())
        filtered = {k: v for k, v in data.items() if k in allowed}
        _settings = {**DEFAULTS, **filtered}
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(_settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(_settings)
