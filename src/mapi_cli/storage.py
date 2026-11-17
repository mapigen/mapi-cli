from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mapi_cli.paths import (
    MAPI_EXT_JSON,
    MAPI_EXT_MSGPACK,
    MAPI_EXT_MSGPACK_ZST,
    MAPI_EXT_ZST,
)


@dataclass(frozen=True)
class ApiStorageTier:
    """Storage and caching tier inspection for an API specification."""

    status: str  # "Cached", "Compressed", "Downloaded", "Not Downloaded"
    is_cached: bool
    is_compressed: bool
    is_downloaded: bool
    format: str | None = None  # "zst", "msgpack.zst", "json", "msgpack", "packfile", None


def get_api_storage_tier(
    client: Any,
    data_dir: Path | None,
    provider: str,
    api: str,
    source: str | None = None,
) -> ApiStorageTier:
    """Inspect the local storage and in-memory cache tier for an API.

    Tiers (in order of priority):
        - Cached: Currently loaded in memory RAM cache (ServiceCache)
        - Compressed: Stored locally in zstd-compressed packfile or file format (.zst)
        - Downloaded: Stored locally in uncompressed format (.mapi.json)
        - Not Downloaded: Not stored locally
    """
    if data_dir is None:
        from mapi_cli.paths import resolve_data_dir

        resolved_dir = resolve_data_dir()[0]
    else:
        resolved_dir = data_dir

    src = source or "github"
    if client is not None:
        try:
            src = client.discovery._resolve_source(provider, api, source)
        except Exception:
            src = source or "github"

    # 1. Check in-memory cache (Tier 3: Cached)
    is_cached = False
    if client is not None:
        try:
            if hasattr(client, "is_cached"):
                is_cached = bool(client.is_cached(provider, api, src))
            elif hasattr(client, "discovery") and hasattr(client.discovery, "is_cached"):
                is_cached = bool(client.discovery.is_cached(provider, api, src))
            elif hasattr(client, "_service_cache") and hasattr(client._service_cache, "is_cached"):
                is_cached = bool(client._service_cache.is_cached(provider, api, src))
        except Exception:
            is_cached = False

    # 2. Check disk formats
    s_dir = resolved_dir / provider / src / api
    is_compressed = False
    is_downloaded = False
    disk_format = None

    if (s_dir / f"{api}{MAPI_EXT_MSGPACK_ZST}").exists():
        is_compressed = True
        is_downloaded = True
        disk_format = "msgpack.zst"
    elif (s_dir / f"{api}{MAPI_EXT_ZST}").exists():
        is_compressed = True
        is_downloaded = True
        disk_format = "zst"
    elif (resolved_dir / "mapi.pack").exists():
        packfile = getattr(getattr(client, "_loader", None), "_packfile", None)
        if packfile is not None and (provider, api, src) in getattr(packfile, "_index", {}):
            is_compressed = True
            is_downloaded = True
            disk_format = "packfile"
    elif (s_dir / f"{api}{MAPI_EXT_JSON}").exists():
        is_downloaded = True
        disk_format = "json"
    elif (s_dir / f"{api}{MAPI_EXT_MSGPACK}").exists():
        is_downloaded = True
        disk_format = "msgpack"

    # Determine highest tier
    if is_cached:
        status = "Cached"
    elif is_compressed:
        status = "Compressed"
    elif is_downloaded:
        status = "Downloaded"
    else:
        status = "Not Downloaded"

    return ApiStorageTier(
        status=status,
        is_cached=is_cached,
        is_compressed=is_compressed,
        is_downloaded=is_downloaded or is_cached,
        format=disk_format,
    )


def is_api_local(
    data_dir: Path | None,
    provider: str,
    source: str,
    api: str,
    client: Any = None,
) -> bool:
    """Check whether an API specification is available locally (downloaded, compressed, or cached)."""
    tier = get_api_storage_tier(client, data_dir, provider, api, source)
    return tier.is_downloaded
