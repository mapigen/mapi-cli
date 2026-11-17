from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CeladonPalette:
    """Color palette design tokens for calm, simple, transparent-shell theme."""

    name: str
    is_dark: bool
    bg: str              # "transparent" to respect host terminal emulator theme
    surface: str         # "transparent" to avoid bulky opaque boxes
    surface_active: str  # Elevated surface for dropdowns/modals
    border: str          # Subtle neutral component border
    border_focus: str    # Clean accent focus border
    primary: str         # Calm brand accent (soft sage celadon)
    secondary: str       # Secondary calm accent for shortcuts/badges
    accent: str          # Soft highlight
    text: str            # High-contrast readable calm neutral text
    text_muted: str      # Calm muted text for secondary details
    highlight: str       # Subtle cursor selection highlight


CELADON_DARK = CeladonPalette(
    name="Calm Dark",
    is_dark=True,
    bg="transparent",        # Inherit user's dark shell background
    surface="transparent",   # Slim & non-bulky layout
    surface_active="#161B22",# Calm dark slate surface for dropdowns
    border="#30363D",        # Subtle slate gray border
    border_focus="#58A6FF",  # Clean focus border
    primary="#6CB6A8",       # Soft, calm sage celadon
    secondary="#79C0FF",     # Calm soft blue for commands/shortcuts
    accent="#A5D6A7",        # Soft calm mint accent
    text="#E6EDF3",          # Crisp readable neutral text
    text_muted="#8B949E",    # Calm neutral muted gray
    highlight="#21262D",     # Subtle table cursor highlight
)

CELADON_LIGHT = CeladonPalette(
    name="Calm Light",
    is_dark=False,
    bg="transparent",        # Inherit user's light shell background
    surface="transparent",   # Slim & non-bulky layout
    surface_active="#F6F8FA",# Clean off-white surface for dropdowns
    border="#D0D7DE",        # Subtle light gray border
    border_focus="#0969DA",  # Clean blue focus border
    primary="#2D6A5D",       # Soft slate celadon
    secondary="#0969DA",     # Clean blue for commands/shortcuts
    accent="#1A7F37",        # Soft green accent
    text="#1F2328",          # Crisp readable dark slate text
    text_muted="#656D76",    # Calm muted slate
    highlight="#EAEEF2",     # Soft light gray cursor highlight
)
