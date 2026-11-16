from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import platformdirs

log = logging.getLogger(__name__)

APP_NAME = "mapi"
CONFIG_FILENAME = "config.json"


def get_config_dir() -> Path:
    """Return platform-standard user configuration directory."""
    return Path(platformdirs.user_config_dir(APP_NAME))


def get_config_path() -> Path:
    """Return full path to the user configuration file."""
    return get_config_dir() / CONFIG_FILENAME


def load_config() -> dict[str, Any]:
    """Load configuration from disk, returning empty dict if missing or invalid."""
    config_file = get_config_path()
    if not config_file.exists():
        return {}
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as e:
        log.warning("Failed to parse config file at %s: %s", config_file, e)
    return {}


def save_config(config_data: dict[str, Any]) -> Path:
    """Save configuration dictionary to disk."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = get_config_path()
    config_file.write_text(json.dumps(config_data, indent=2) + "\n", encoding="utf-8")
    return config_file


def get_config_value(key: str, default: Any = None) -> Any:
    """Get single value from config."""
    cfg = load_config()
    return cfg.get(key, default)


def set_config_value(key: str, value: Any) -> Path:
    """Set single value in config and persist."""
    cfg = load_config()
    cfg[key] = value
    return save_config(cfg)


def reset_config() -> bool:
    """Remove user configuration file if it exists."""
    config_file = get_config_path()
    if config_file.exists():
        config_file.unlink()
        return True
    return False
