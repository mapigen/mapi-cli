from __future__ import annotations

import io
import sys
from typing import Any

import msgspec
from mapi.models.response import MapiResult
from rich.console import RenderableType

from mapi_cli.ui.console import console
from mapi_cli.ui.syntax import render_json


def emit_output(
    data: Any,
    format_type: str = "auto",
    rich_renderable: RenderableType | None = None,
    show_meta: bool = False,
) -> None:
    """Emit data to stdout adhering to formatting rules (auto / json / table / raw).

    - When stdout is a pipe or format is 'json', emit plain JSON (perfect for jq/scripts).
    - When stdout is a TTY and rich_renderable is provided, render visually pleasing Rich tables/panels.
    - If format is 'raw', print raw bytes or strings directly.
    """
    is_tty = console.is_terminal

    # Handle MapiResult
    payload = data
    if isinstance(data, MapiResult):
        if show_meta:
            payload = {
                "data": data.data,
                "metadata": {
                    "service": data.metadata.service,
                    "operation": data.metadata.operation,
                    "status": data.metadata.status,
                    "http_status": data.metadata.http_status,
                    "duration_ms": data.metadata.duration_ms,
                    "network_duration_ms": data.metadata.network_duration_ms,
                    "headers": dict(data.metadata.headers),
                },
            }
        else:
            payload = data.data

    if format_type == "json" or (format_type == "auto" and not is_tty and rich_renderable is None):
        try:
            encoded = msgspec.json.encode(payload)
            text = encoded.decode("utf-8")
            try:
                sys.stdout.buffer.write(encoded + b"\n")
                sys.stdout.buffer.flush()
            except (AttributeError, io.UnsupportedOperation):
                sys.stdout.write(text + "\n")
                sys.stdout.flush()
        except Exception:
            console.print(str(payload))
        return

    if format_type == "raw":
        if isinstance(payload, bytes):
            try:
                sys.stdout.buffer.write(payload)
                sys.stdout.buffer.flush()
            except (AttributeError, io.UnsupportedOperation):
                sys.stdout.write(payload.decode("utf-8", errors="replace"))
        else:
            sys.stdout.write(str(payload))
        sys.stdout.flush()
        return

    # TTY or explicit table format
    if rich_renderable is not None:
        console.print(rich_renderable)
    elif isinstance(payload, (dict, list)):
        console.print(render_json(payload))
    else:
        console.print(str(payload))
