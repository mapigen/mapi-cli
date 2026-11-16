from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass(frozen=True)
class CeladonPalette:
    """Color palette definition for Celadon Green theme."""

    name: str
    is_dark: bool
    bg: str
    surface: str
    border: str
    primary: str
    secondary: str
    accent: str
    text: str
    text_muted: str
    highlight: str


CELADON_DARK = CeladonPalette(
    name="Celadon Dark",
    is_dark=True,
    bg="#111C18",        # Deep Charcoal Green
    surface="#1B2A25",   # Muted Forest Surface
    border="#2E4A40",    # Celadon Border
    primary="#2F847C",   # Celadon Jade Primary
    secondary="#7EE0D2", # Mint Glow
    accent="#ACE1AF",    # Classic Pale Celadon
    text="#E1F4E2",      # Pale Celadon High-Contrast Text
    text_muted="#7E9F93",# Soft Sage
    highlight="#3A6054", # Selection Highlight
)

CELADON_LIGHT = CeladonPalette(
    name="Celadon Light",
    is_dark=False,
    bg="#F7F4EF",        # Off-White Cream
    surface="#DDECE6",   # Mist White / Pale Celadon Surface
    border="#B2D0C5",    # Subtle Sage Border
    primary="#4A7569",   # Deep Celadon Slate Primary
    secondary="#2F847C", # Jade Secondary
    accent="#263832",    # Deep Accent
    text="#263832",      # Deep Slate Green Text
    text_muted="#5C736B",# Muted Sage
    highlight="#C8DFD7", # Soft Selection Highlight
)
