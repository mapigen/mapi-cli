from __future__ import annotations

from rich.text import Text

from mapi_cli.ui.models import CELADON_DARK, CELADON_LIGHT

MAPI_ASCII_ART = """
 ███╗   ███╗  █████╗  ██████╗  ██╗
 ████╗ ████║ ██╔══██╗ ██╔══██╗ ██║
 ██╔████╔██║ ███████║ ██████╔╝ ██║
 ██║╚██╔╝██║ ██╔══██║ ██╔═══╝  ██║
 ██║ ╚═╝ ██║ ██║  ██║ ██║      ██║
 ╚═╝     ╚═╝ ╚═╝  ╚═╝ ╚═╝      ╚═╝
""".strip("\n")


def render_banner(is_dark: bool = True) -> Text:
    """Render the MAPI ASCII text art with Celadon Green gradient styling."""
    palette = CELADON_DARK if is_dark else CELADON_LIGHT
    art_text = Text()

    # Apply stylish celadon gradient across the banner lines
    lines = MAPI_ASCII_ART.split("\n")
    accent_colors = (
        [palette.accent, palette.secondary, palette.primary, palette.secondary, palette.accent, palette.text]
        if is_dark
        else [palette.primary, palette.secondary, palette.accent, palette.primary, palette.secondary, palette.text]
    )

    for i, line in enumerate(lines):
        color = accent_colors[i % len(accent_colors)]
        art_text.append(line + "\n", style=f"bold {color}")

    art_text.append("  Universal API Discovery Engine & Toolchain\n", style=f"italic {palette.text_muted}")
    art_text.append(
        "  Tip: You can pass --no-tui (or set MAPI_NO_TUI=1) to run in plain CLI mode.\n",
        style=f"dim {palette.text_muted}",
    )
    return art_text
