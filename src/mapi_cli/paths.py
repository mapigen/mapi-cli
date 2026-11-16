from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import platformdirs

from mapi_cli.config import get_config_value

PRIMARY_REGISTRY_FILENAME: str = "mapi-registry.json"
LEGACY_REGISTRY_FILENAME: str = "services.json"
DEFAULT_DATA_DIR_NAME: str = "data"

MAPI_EXT_JSON: str = ".mapi.json"
MAPI_EXT_ZST: str = ".mapi.json.zst"
MAPI_EXT_MSGPACK: str = ".mapi.msgpack"
MAPI_EXT_MSGPACK_ZST: str = ".mapi.msgpack.zst"


def find_installed_mapi_sdk() -> tuple[bool, str | None, Path | None]:
    """Detect if the core mapi SDK is installed and return (is_installed, version, path)."""
    try:
        spec = importlib.util.find_spec("mapi")
        if spec is None:
            return False, None, None

        import mapi

        version = getattr(mapi, "__version__", "unknown")
        pkg_file = getattr(mapi, "__file__", None)
        pkg_path = Path(pkg_file).parent if pkg_file else None
        return True, str(version), pkg_path
    except Exception:
        return False, None, None


def find_registry_in_dir(directory: Path) -> Path | None:
    """Check directory for primary mapi-registry.json, falling back to services.json."""
    if not directory.exists() or not directory.is_dir():
        return None

    primary = directory / PRIMARY_REGISTRY_FILENAME
    if primary.is_file():
        return primary

    legacy = directory / LEGACY_REGISTRY_FILENAME
    if legacy.is_file():
        return legacy

    return None


def get_system_user_data_dir() -> Path:
    """Return platformdirs data directory for mapi."""
    return Path(platformdirs.user_data_dir("mapi")) / DEFAULT_DATA_DIR_NAME


def auto_discover_candidates() -> list[dict[str, Any]]:
    """Scan environment, config, workspace, and packages for candidate MAPI data directories."""
    candidates: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()

    def add_candidate(path: Path, source: str) -> None:
        resolved = path.resolve()
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        exists = resolved.exists()
        reg_file = find_registry_in_dir(resolved) if exists else None
        if not reg_file and exists:
            # check parent directory for registry as well
            reg_file = find_registry_in_dir(resolved.parent)

        candidates.append(
            {
                "path": resolved,
                "source": source,
                "exists": exists,
                "is_dir": resolved.is_dir() if exists else False,
                "registry_file": reg_file,
            }
        )

    # 1. Environment variable
    env_dir = os.environ.get("MAPI_DATA_DIR")
    if env_dir:
        add_candidate(Path(env_dir), "Environment (MAPI_DATA_DIR)")

    # 2. Check CWD and walk up parents (Local Workspace takes precedence over global config)
    current = Path.cwd().resolve()
    for parent in [current, *current.parents[:4]]:
        data_sub = parent / DEFAULT_DATA_DIR_NAME
        if data_sub.is_dir():
            add_candidate(data_sub, f"Local Workspace ({parent.name}/data)")
        reg = find_registry_in_dir(parent)
        if reg:
            add_candidate(parent, f"Local Workspace ({parent.name})")

    # 3. Check installed mapi package
    installed, _, pkg_path = find_installed_mapi_sdk()
    if installed and pkg_path:
        pkg_data = pkg_path / DEFAULT_DATA_DIR_NAME
        if pkg_data.is_dir():
            add_candidate(pkg_data, "Installed MAPI Package")

    # 4. Persisted user configuration (~/.config/mapi)
    cfg_dir = get_config_value("data_dir")
    if cfg_dir:
        add_candidate(Path(cfg_dir), "User Config (~/.config/mapi)")

    # 5. System user data dir
    user_data = get_system_user_data_dir()
    if user_data.exists():
        add_candidate(user_data, "System User Data Dir")

    return candidates


def resolve_data_dir(explicit: Path | None = None) -> tuple[Path, str]:
    """Resolve data directory using precedence: Explicit > ENV > Explicit User Config > Auto-discovery > Fallback."""
    if explicit is not None:
        return explicit, "cli_argument"

    env_dir = os.environ.get("MAPI_DATA_DIR")
    if env_dir:
        return Path(env_dir), "env_var"

    cfg_dir = get_config_value("data_dir")
    if cfg_dir:
        p = Path(cfg_dir)
        if p.exists():
            return p, "user_config"

    # Auto-discovery (Local Workspace & Installed Package first, before System Fallback)
    for candidate in auto_discover_candidates():
        if (
            candidate["exists"]
            and candidate["is_dir"]
            and (candidate["registry_file"] or any(candidate["path"].iterdir()))
        ):
            return candidate["path"], candidate["source"]

    user_data = get_system_user_data_dir()
    if user_data.exists():
        return user_data, "system_user_data"

    return Path(DEFAULT_DATA_DIR_NAME), "default_fallback"


def resolve_registry_path(
    data_dir: Path | None = None, explicit: Path | None = None
) -> tuple[Path, str]:
    """Resolve registry path using precedence: Explicit > Config > Directory Search > Default."""
    if explicit is not None:
        return explicit, "cli_argument"

    cfg_reg = get_config_value("registry_path")
    if cfg_reg:
        p = Path(cfg_reg)
        if p.exists():
            return p, "user_config"

    target_dir = data_dir if data_dir else resolve_data_dir()[0]

    # Check target_dir
    reg = find_registry_in_dir(target_dir)
    if reg:
        return reg, "data_dir"

    # Check target_dir.parent
    if target_dir.parent.exists():
        reg_parent = find_registry_in_dir(target_dir.parent)
        if reg_parent:
            return reg_parent, "parent_dir"

    # Check current directory
    reg_cwd = find_registry_in_dir(Path.cwd())
    if reg_cwd:
        return reg_cwd, "cwd"

    # Default to primary filename in data_dir (or parent if data_dir is "data")
    if target_dir.name == DEFAULT_DATA_DIR_NAME:
        return target_dir.parent / PRIMARY_REGISTRY_FILENAME, "default_primary"
    return target_dir / PRIMARY_REGISTRY_FILENAME, "default_primary"
