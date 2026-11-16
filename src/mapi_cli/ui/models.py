from __future__ import annotations

from dataclasses import dataclass, field

from mapi_cli.ui.styles.palette import CELADON_DARK, CELADON_LIGHT, CeladonPalette


@dataclass(frozen=True)
class CommandItem:
    """Intelligent command model for the '/' command palette."""

    command: str  # e.g. "/apis", "/ops", "/download", "/search", "/theme", "/quit"
    title: str
    description: str
    category: str = "General"  # Discovery, Execution, System
    shortcut: str = ""
    aliases: list[str] = field(default_factory=list)
    handler_action: str = ""  # Method name to invoke on App


__all__ = [
    "CELADON_DARK",
    "CELADON_LIGHT",
    "CeladonPalette",
    "CommandItem",
]
