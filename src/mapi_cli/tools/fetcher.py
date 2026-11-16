from __future__ import annotations

import time
from pathlib import Path

import niquests

from mapi_cli.tools.models import FetchResult


def fetch_spec(
    url: str,
    output_path: Path,
    provider: str = "",
    api: str = "",
    source: str = "url",
    timeout: float = 30.0,
) -> FetchResult:
    """Download an upstream specification from a remote URL."""
    start = time.perf_counter()
    try:
        resp = niquests.get(url, timeout=timeout)
        resp.raise_for_status()
        content: bytes = resp.content or b""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)

        return FetchResult(
            provider=provider,
            api=api,
            source=source,
            status="downloaded",
            bytes_downloaded=len(content),
            duration_sec=time.perf_counter() - start,
            output_path=str(output_path),
        )
    except Exception as e:
        return FetchResult(
            provider=provider,
            api=api,
            source=source,
            status="failure",
            duration_sec=time.perf_counter() - start,
            error_message=str(e),
        )
