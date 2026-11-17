from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CeladonPalette:
    """Color palette design tokens for slim, transparent-shell Celadon Green theme."""

    name: str
    is_dark: bool
    bg: str              # "transparent" to respect host terminal emulator theme
    surface: str         # "transparent" to avoid bulky opaque boxes
    surface_active: str  # Elevated surface for dropdowns/modals
    border: str          # Subtle component border
    border_focus: str    # Focus border (vibrant green)
    primary: str         # Primary green
    secondary: str       # Secondary mint/bright green
    accent: str          # Classic Celadon highlight
    text: str            # High-contrast readable green text
    text_muted: str      # Subtitles, hints, and secondary sage text
    highlight: str       # Table cursor selection highlight


CELADON_DARK = CeladonPalette(
    name="Celadon Dark",
    is_dark=True,
    bg="transparent",       # Inherit user's dark shell background
    surface="transparent",  # Slim & non-bulky layout
    surface_active="#1B2A25",# Translucent dark green for menus
    border="#2E4A40",       # Slim celadon border
    border_focus="#7EE0D2", # Mint glow focus border
    primary="#7EE0D2",      # Vibrant mint green
    secondary="#55FF99",    # Bright terminal green
    accent="#ACE1AF",       # Classic pale celadon
    text="#ACE1AF",         # Primary celadon green text
    text_muted="#7E9F93",   # Soft sage green for secondary text
    highlight="#1E3A32",    # Subtle table cursor highlight
)

CELADON_LIGHT = CeladonPalette(
    name="Celadon Light",
    is_dark=False,
    bg="transparent",       # Inherit user's light shell background
    surface="transparent",  # Slim & non-bulky layout
    surface_active="#DDECE6",# Translucent light celadon for menus
    border="#A4C2B7",       # Slim sage border
    border_focus="#2F847C", # Deep jade focus border
    primary="#2F847C",      # Deep jade green
    secondary="#1A524C",    # Deep forest green
    accent="#263832",       # Slate green accent
    text="#1B3B32",         # High-contrast dark green text
    text_muted="#5C7A70",   # Muted sage green
    highlight="#CCE3DC",    # Soft light green cursor highlight
)
