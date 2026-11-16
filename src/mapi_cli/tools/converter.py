from __future__ import annotations

from pathlib import Path
from typing import Any

import msgspec
import yaml

from mapi_cli.tools.utils import decompress_zstd


def normalize_spec(
    path: Path | None = None,
    compressed_content: bytes | None = None,
) -> dict[str, Any]:
    """Load and parse an OpenAPI specification from file path or compressed bytes."""
    if not path and compressed_content is None:
        raise ValueError("Either 'path' or 'compressed_content' must be provided.")

    if compressed_content is not None:
        decompressed = decompress_zstd(compressed_content)
        return msgspec.json.decode(decompressed)
    elif path:
        content = path.read_bytes()
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        else:
            return msgspec.json.decode(content)
    return {}
