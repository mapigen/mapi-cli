from __future__ import annotations

from mapi_cli.ui.styles.palette import CELADON_DARK, CELADON_LIGHT, CeladonPalette


def build_app_tcss(
    dark: CeladonPalette = CELADON_DARK,
    light: CeladonPalette = CELADON_LIGHT,
) -> str:
    """Build unified, modular Textual CSS (TCSS) from CeladonPalette design tokens."""
    return f"""
    /* =========================================================================
       1. Base Dark Mode Canvas (Default)
       ========================================================================= */
    Screen {{
        background: {dark.bg};
        color: {dark.text};
    }}

    #header_container {{
        height: auto;
        padding: 0 1;
        background: {dark.surface};
        border-bottom: heavy {dark.border};
    }}

    #banner_static {{
        margin: 0;
        padding: 0;
    }}

    #path_label {{
        color: {dark.text_muted};
        padding-top: 0;
    }}

    /* Inputs (Command Palette & Filter) */
    #command_input, #filter_input {{
        margin: 1 0 0 0;
        background: {dark.bg};
        border: tall {dark.border};
        color: {dark.secondary};
    }}

    #command_input:focus, #filter_input:focus {{
        border: tall {dark.border_focus};
    }}

    /* Suggestions Dropdown */
    #suggestions_container {{
        height: auto;
        max-height: 8;
        display: none;
        background: {dark.surface};
        border: solid {dark.border};
        margin: 0;
    }}

    #suggestions_list {{
        background: transparent;
        height: auto;
        max-height: 7;
    }}

    /* Data Tables */
    #table_container {{
        height: 1fr;
        padding: 0 1;
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
        color: {dark.secondary};
        text-style: bold;
    }}

    /* Status & Loading Indicator */
    #status_panel {{
        height: auto;
        min-height: 3;
        max-height: 5;
        background: {dark.surface};
        border-top: heavy {dark.border};
        padding: 0 1;
    }}

    #status_text {{
        color: {dark.text_muted};
        padding-top: 0;
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

    Screen.light-mode #header_container {{
        background: {light.surface};
        border-bottom: heavy {light.border};
    }}

    Screen.light-mode #path_label {{
        color: {light.text_muted};
    }}

    Screen.light-mode #command_input, Screen.light-mode #filter_input {{
        background: #FFFFFF;
        border: tall {light.border};
        color: {light.text};
    }}

    Screen.light-mode #command_input:focus, Screen.light-mode #filter_input:focus {{
        border: tall {light.border_focus};
    }}

    Screen.light-mode #suggestions_container {{
        background: {light.surface};
        border: solid {light.border};
    }}

    Screen.light-mode #catalog_table, Screen.light-mode #providers_table {{
        background: #FFFFFF;
        border: round {light.border};
    }}

    Screen.light-mode #catalog_table:focus, Screen.light-mode #providers_table:focus {{
        border: round {light.border_focus};
    }}

    Screen.light-mode DataTable > .datatable--cursor {{
        background: {light.highlight};
        color: {light.text};
        text-style: bold;
    }}

    Screen.light-mode DataTable > .datatable--header {{
        background: {light.surface};
        color: {light.primary};
        text-style: bold;
    }}

    Screen.light-mode #status_panel {{
        background: {light.surface};
        border-top: heavy {light.border};
    }}

    Screen.light-mode #status_text {{
        color: {light.text};
    }}

    Screen.light-mode #loader {{
        color: {light.secondary};
    }}
    """.strip()
