from __future__ import annotations

import re

from mapi_cli.ui.styles import (
    CELADON_DARK,
    CELADON_LIGHT,
    build_app_tcss,
    method_style,
    status_style,
)

HEX_COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_palette_token_integrity():
    """Verify that all CeladonPalette design tokens are valid 6-digit hex color strings."""
    for pal in (CELADON_DARK, CELADON_LIGHT):
        for field in (
            pal.bg,
            pal.surface,
            pal.surface_active,
            pal.border,
            pal.border_focus,
            pal.primary,
            pal.secondary,
            pal.accent,
            pal.text,
            pal.text_muted,
            pal.highlight,
        ):
            assert HEX_COLOR_REGEX.match(field), f"Invalid hex color token '{field}' in {pal.name}"


def test_tcss_generation():
    """Verify build_app_tcss generates modular Textual CSS containing both theme rules."""
    tcss = build_app_tcss()
    assert "Screen {" in tcss
    assert "Screen.light-mode {" in tcss
    assert CELADON_DARK.bg in tcss
    assert CELADON_LIGHT.bg in tcss
    assert "#catalog_table" in tcss
    assert "#command_input" in tcss
    assert "#loader" in tcss


def test_rich_theme_styling():
    """Verify method and status style lookups."""
    assert "method.get" in method_style("GET")
    assert "method.post" in method_style("POST")
    assert method_style("UNKNOWN_METHOD") == "bold white"

    assert status_style("Downloaded") == "bold green"
    assert status_style("Skipped") == "bold yellow"
    assert status_style("Error") == "bold red"
