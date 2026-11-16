from __future__ import annotations

from pathlib import Path
from typing import Any

import msgspec


class StateManifest(msgspec.Struct):
    """Manifest tracking upstream content hashes and ETags for incremental builds."""

    version: int = 1
    entries: dict[str, dict[str, Any]] = msgspec.field(default_factory=dict)


class StateManager:
    """Manages reading and updating .mapi_state.json for fast incremental sync."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.manifest = self._load()

    def _load(self) -> StateManifest:
        if self.state_file.exists():
            try:
                data = self.state_file.read_bytes()
                return msgspec.json.decode(data, type=StateManifest)
            except Exception:
                pass
        return StateManifest()

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_bytes(msgspec.json.encode(self.manifest))

    def get_hash(self, key: str) -> str | None:
        entry = self.manifest.entries.get(key)
        return entry.get("hash") if entry else None

    def set_entry(self, key: str, content_hash: str, etag: str | None = None) -> None:
        self.manifest.entries[key] = {
            "hash": content_hash,
            "etag": etag,
        }
