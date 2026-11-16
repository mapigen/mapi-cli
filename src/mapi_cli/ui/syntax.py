from __future__ import annotations

import json
from typing import Any

import msgspec
from rich.syntax import Syntax


def render_json(data: Any, indent: int = 2) -> Syntax:
    """Render syntax-highlighted JSON."""
    if isinstance(data, (bytes, bytearray)):
        try:
            parsed = msgspec.json.decode(data)
            text = json.dumps(parsed, indent=indent)
        except Exception:
            text = data.decode("utf-8", errors="replace")
    elif isinstance(data, str):
        try:
            parsed = json.loads(data)
            text = json.dumps(parsed, indent=indent)
        except Exception:
            text = data
    else:
        try:
            text = msgspec.json.encode(data).decode("utf-8")
            parsed = json.loads(text)
            text = json.dumps(parsed, indent=indent)
        except Exception:
            text = str(data)

    return Syntax(text, "json", theme="monokai", word_wrap=True)
