from __future__ import annotations

from rich.theme import Theme

MAPI_THEME = Theme(
    {
        "method.get": "bold cyan",
        "method.post": "bold green",
        "method.put": "bold yellow",
        "method.patch": "bold magenta",
        "method.delete": "bold red",
        "method.head": "dim cyan",
        "method.options": "dim cyan",
        "status.success": "bold green",
        "status.client_error": "bold yellow",
        "status.server_error": "bold red",
        "status.dry_run": "bold magenta",
        "provider": "bold bright_white",
        "api": "bold cyan",
        "op": "bold green",
        "param.name": "bold yellow",
        "param.required": "bold red",
        "param.type": "dim cyan",
        "hint": "dim italic",
        "kv.key": "cyan",
        "kv.val": "white",
    }
)


def method_style(method: str) -> str:
    """Return rich theme style for an HTTP method."""
    m = method.upper()
    return f"method.{m.lower()}" if f"method.{m.lower()}" in MAPI_THEME.styles else "bold white"


def status_style(status: str) -> str:
    """Return rich theme style for download or execution status."""
    st = status.lower()
    if st in ("downloaded", "success"):
        return "bold green"
    if st in ("skipped", "warning"):
        return "bold yellow"
    if st in ("error", "failed"):
        return "bold red"
    return "dim"
