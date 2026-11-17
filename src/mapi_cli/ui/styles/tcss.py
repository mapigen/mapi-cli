from __future__ import annotations

from mapi_cli.ui.styles.palette import CELADON_DARK, CELADON_LIGHT, CeladonPalette


def build_app_tcss(
    dark: CeladonPalette = CELADON_DARK,
    light: CeladonPalette = CELADON_LIGHT,
) -> str:
    """Build unified, slim, modular Textual CSS (TCSS) from CeladonPalette design tokens."""
    return f"""
    /* =========================================================================
       1. Base Dark Mode Canvas (Transparent shell following user's terminal)
       ========================================================================= */
    Screen {{
        background: {dark.bg};
        color: {dark.text};
    }}

    Header {{
        dock: top;
        height: 1;
        background: {dark.bg};
        color: {dark.text_muted};
    }}

    HeaderTitle {{
        color: {dark.text};
        text-style: bold;
    }}

    Footer {{
        dock: bottom;
        height: 1;
        background: {dark.bg};
    }}

    Footer > .footer--key {{
        background: {dark.bg};
        color: {dark.secondary};
        text-style: bold;
    }}

    Footer > .footer--description {{
        color: {dark.text_muted};
    }}

    #header_container {{
        height: auto;
        padding: 0 1;
        background: {dark.surface};
        border-bottom: none;
    }}

    #banner_static {{
        margin: 0;
        padding: 0;
    }}

    #path_label {{
        color: {dark.text_muted};
        padding: 0;
        margin: 0;
    }}

    /* Data Tables - Center Canvas */
    #table_container {{
        height: 1fr;
        padding: 0 1;
        background: {dark.surface};
    }}

    #catalog_table, #providers_table {{
        height: 1fr;
        background: {dark.surface};
        border: round {dark.border};
    }}

    #catalog_table:focus, #providers_table:focus {{
        border: round {dark.border_focus};
    }}

    DataTable > .datatable--cursor {{
        background: {dark.highlight};
        color: #FFFFFF;
        text-style: bold;
    }}

    DataTable > .datatable--header {{
        background: {dark.surface};
        color: {dark.text_muted};
        text-style: bold;
    }}

    /* Bottom Command & Search Bar */
    #command_container {{
        height: auto;
        padding: 0 1;
        margin: 0;
        background: {dark.surface};
    }}

    #command_input, #filter_input {{
        margin: 0;
        padding: 0 1;
        background: {dark.bg};
        border: round {dark.border};
        color: {dark.text};
        height: 3;
    }}

    #command_input:focus, #filter_input:focus {{
        border: round {dark.border_focus};
    }}

    /* Suggestions Dropdown (Pops up above bottom input) */
    #suggestions_container {{
        height: auto;
        max-height: 8;
        display: none;
        background: {dark.surface_active};
        border: round {dark.border_focus};
        margin: 0 0 1 0;
        padding: 0;
    }}

    #suggestions_list {{
        background: transparent;
        height: auto;
        max-height: 7;
        color: {dark.text};
    }}

    /* Status & Loading Indicator - Slim bottom layout */
    #status_panel {{
        height: auto;
        min-height: 1;
        max-height: 3;
        background: {dark.surface};
        border-top: solid {dark.border};
        padding: 0 1;
    }}

    #status_text {{
        color: {dark.text_muted};
        padding: 0;
    }}

    #loader {{
        height: 1;
        color: {dark.secondary};
        display: none;
    }}

    /* =========================================================================
       2. Light Mode Overrides (.light-mode)
       ========================================================================= */
    Screen.light-mode {{
        background: {light.bg};
        color: {light.text};
    }}

    Screen.light-mode Header {{
        background: {light.bg};
        color: {light.text_muted};
    }}

    Screen.light-mode HeaderTitle {{
        color: {light.text};
    }}

    Screen.light-mode Footer {{
        background: {light.bg};
    }}

    Screen.light-mode Footer > .footer--key {{
        background: {light.bg};
        color: {light.secondary};
    }}

    Screen.light-mode Footer > .footer--description {{
        color: {light.text_muted};
    }}

    Screen.light-mode #header_container {{
        background: {light.surface};
        border-bottom: none;
    }}

    Screen.light-mode #path_label {{
        color: {light.text_muted};
    }}

    Screen.light-mode #table_container {{
        background: {light.surface};
    }}

    Screen.light-mode #catalog_table, Screen.light-mode #providers_table {{
        background: {light.surface};
        border: round {light.border};
    }}

    Screen.light-mode #catalog_table:focus, Screen.light-mode #providers_table:focus {{
        border: round {light.border_focus};
    }}

    Screen.light-mode DataTable > .datatable--cursor {{
        background: {light.highlight};
        color: #000000;
        text-style: bold;
    }}

    Screen.light-mode DataTable > .datatable--header {{
        background: {light.surface};
        color: {light.text_muted};
        text-style: bold;
    }}

    Screen.light-mode #command_container {{
        background: {light.surface};
    }}

    Screen.light-mode #command_input, Screen.light-mode #filter_input {{
        background: {light.bg};
        border: round {light.border};
        color: {light.text};
    }}

    Screen.light-mode #command_input:focus, Screen.light-mode #filter_input:focus {{
        border: round {light.border_focus};
    }}

    Screen.light-mode #suggestions_container {{
        background: {light.surface_active};
        border: round {light.border_focus};
        margin: 0 0 1 0;
    }}

    Screen.light-mode #suggestions_list {{
        color: {light.text};
    }}

    Screen.light-mode #status_panel {{
        background: {light.surface};
        border-top: solid {light.border};
    }}

    Screen.light-mode #status_text {{
        color: {light.text};
    }}

    Screen.light-mode #loader {{
        color: {light.secondary};
    }}
    """.strip()
