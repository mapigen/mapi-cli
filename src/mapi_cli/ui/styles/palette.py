from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CeladonPalette:
    """Color palette design tokens for Celadon Green theme."""

    name: str
    is_dark: bool
    bg: str              # Main canvas background
    surface: str         # Cards, panels, tables
    surface_active: str  # Active / focused card surface
    border: str          # Subtle component borders
    border_focus: str    # Focus / active borders
    primary: str         # Primary branding / buttons
    secondary: str       # Secondary accents / glowing focus
    accent: str          # Highlights and text accents
    text: str            # High-contrast readable text
    text_muted: str      # Subtitles, hints, and secondary text
    highlight: str       # Row selection cursor highlight


CELADON_DARK = CeladonPalette(
    name="Celadon Dark",
    is_dark=True,
    bg="#111C18",           # Deep Charcoal Green
    surface="#1B2A25",      # Muted Forest Surface
    surface_active="#243831",# Elevated Surface
    border="#2E4A40",       # Celadon Slate Border
    border_focus="#7EE0D2", # Mint Glow Focus Border
    primary="#2F847C",      # Celadon Jade Primary
    secondary="#7EE0D2",    # Mint Glow Accent
    accent="#ACE1AF",       # Classic Pale Celadon
    text="#E1F4E2",         # High-contrast Pale Celadon Text
    text_muted="#7E9F93",   # Soft Sage
    highlight="#3A6054",    # Table Cursor Selection
)

CELADON_LIGHT = CeladonPalette(
    name="Celadon Light",
    is_dark=False,
    bg="#F7F4EF",           # Off-White Cream
    surface="#DDECE6",      # Mist White / Pale Celadon Surface
    surface_active="#D0E4DC",# Elevated Surface
    border="#B2D0C5",       # Subtle Sage Border
    border_focus="#2F847C", # Deep Jade Focus Border
    primary="#4A7569",      # Celadon Slate Primary
    secondary="#2F847C",    # Deep Jade Secondary
    accent="#263832",       # Deep Green Accent
    text="#263832",         # Deep Slate Green Text
    text_muted="#5C736B",   # Muted Sage
    highlight="#C8DFD7",    # Soft Cursor Selection
)
