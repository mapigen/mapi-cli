from __future__ import annotations

from rich.text import Text

from mapi_cli.ui.styles.palette import CELADON_DARK, CELADON_LIGHT

# Slim, compact modern ASCII text art (mimics Claude-CLI / Gemini-CLI ergonomics)
MAPI_ASCII_ART_SLIM = r"""
  __  __   _   ___ ___
 |  \/  | /_\ | _ \_ _|
 | |\/| |/ _ \|  _/| |
 |_|  |_/_/ \_\_| |___|
""".strip("\n")

# Legacy block art preserved for backwards compatibility
MAPI_ASCII_ART = MAPI_ASCII_ART_SLIM


def render_banner(is_dark: bool = True) -> Text:
    """Render slim, elegant MAPI ASCII text art with calm styling."""
    palette = CELADON_DARK if is_dark else CELADON_LIGHT
    art_text = Text()

    lines = MAPI_ASCII_ART_SLIM.split("\n")
    for line in lines:
        art_text.append(line + "\n", style=f"bold {palette.primary}")

    art_text.append("  ⬡ Universal API Discovery Engine", style=f"bold {palette.text}")
    art_text.append(" • Type ", style=f"{palette.text_muted}")
    art_text.append("/", style=f"bold {palette.secondary}")
    art_text.append(" for commands\n", style=f"{palette.text_muted}")
    art_text.append(
        "  Tip: Pass --no-tui to use direct CLI mode.\n",
        style=f"dim {palette.text_muted}",
    )
    return art_text
