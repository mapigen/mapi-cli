from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mapi import Mapi
from mapi.models.config import ClientConfig

from mapi_cli.paths import resolve_data_dir


@dataclass
class CliContext:
    """Execution context passed through Typer callbacks."""

    data_dir: Path | None = None
    base_url: str | None = None
    timeout: float = 30.0
    output: str = "auto"
    show_meta: bool = False
    _client: Mapi | None = None

    @property
    def client(self) -> Mapi:
        """Lazily instantiate the Mapi SDK client so --help and completion stay fast."""
        if self._client is None:
            effective_dir, _ = resolve_data_dir(self.data_dir)
            cfg = ClientConfig(base_url=self.base_url, default_timeout=self.timeout)
            self._client = Mapi(config=cfg, data_dir=effective_dir)
        return self._client
