from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from mapi_cli.ui.models import CommandItem

DEFAULT_COMMANDS: list[CommandItem] = [
    CommandItem(
        command="/apis",
        title="List Providers & APIs",
        description="Browse all available API specifications and local download status",
        category="Discovery",
        shortcut="a",
        aliases=["/providers", "/catalog"],
        handler_action="action_show_apis",
    ),
    CommandItem(
        command="/ops",
        title="Explore Operations",
        description="Inspect operations, HTTP methods, and URL endpoints",
        category="Discovery",
        shortcut="o",
        aliases=["/operations", "/endpoints"],
        handler_action="action_show_ops",
    ),
    CommandItem(
        command="/download",
        title="Download Manager",
        description="Download and compile remote API specifications into local storage",
        category="Execution",
        shortcut="d",
        aliases=["/sync", "/fetch"],
        handler_action="action_show_downloads",
    ),
    CommandItem(
        command="/search",
        title="Global Search",
        description="Fuzzy search across all providers, APIs, operations, and methods",
        category="Discovery",
        shortcut="s",
        aliases=["/find", "/query"],
        handler_action="action_focus_search",
    ),
    CommandItem(
        command="/theme",
        title="Toggle Celadon Theme",
        description="Switch between Celadon Dark and Celadon Light mode",
        category="System",
        shortcut="t",
        aliases=["/mode", "/dark", "/light"],
        handler_action="action_toggle_theme",
    ),
    CommandItem(
        command="/refresh",
        title="Reload Registry",
        description="Re-read mapi-registry.json and refresh local spec status",
        category="System",
        shortcut="r",
        aliases=["/reload"],
        handler_action="action_refresh_data",
    ),
    CommandItem(
        command="/help",
        title="Help & Shortcuts",
        description="Show keyboard navigation, commands, and CLI options",
        category="System",
        shortcut="h",
        aliases=["/?"],
        handler_action="action_show_help",
    ),
    CommandItem(
        command="/quit",
        title="Exit Mapi",
        description="Close the interactive TUI and return to terminal",
        category="System",
        shortcut="q",
        aliases=["/exit", "/q"],
        handler_action="action_quit",
    ),
]


def filter_commands(query: str) -> list[CommandItem]:
    """Filter commands dynamically as the user types (prefix, alias, or description match)."""
    q = query.strip().lower()
    if not q or q == "/":
        return DEFAULT_COMMANDS

    matched = []
    # If starts with '/', strip it for fuzzy matching
    term = q[1:] if q.startswith("/") else q

    for cmd in DEFAULT_COMMANDS:
        cmd_bare = cmd.command.lstrip("/")
        if (
            cmd_bare.startswith(term)
            or term in cmd_bare
            or any(term in alias.lstrip("/") for alias in cmd.aliases)
            or term in cmd.title.lower()
            or term in cmd.description.lower()
        ):
            matched.append(cmd)
    return matched


class CommandPaletteWidget(Widget):
    """Interactive '/' command palette and live search bar."""

    DEFAULT_CSS = """
    CommandPaletteWidget {
        height: auto;
        margin: 0 1;
        background: transparent;
    }

    #command_input {
        width: 100%;
        border: tall #2E4A40;
        background: #111C18;
        color: #E1F4E2;
    }

    #command_input:focus {
        border: tall #7EE0D2;
    }

    #suggestions_container {
        height: auto;
        max-height: 8;
        display: none;
        background: #1B2A25;
        border: solid #2E4A40;
        margin: 0 1;
    }

    #suggestions_list {
        background: transparent;
        height: auto;
        max-height: 7;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Type '/' for intelligent commands (e.g. /apis, /download, /theme) or type to filter...",
            id="command_input",
        )
        with Vertical(id="suggestions_container"):
            yield OptionList(id="suggestions_list")

    def update_suggestions(self, query: str) -> None:
        """Update suggestion list dynamically as user types."""
        container = self.query_one("#suggestions_container", Vertical)
        opt_list = self.query_one("#suggestions_list", OptionList)

        if query.startswith("/"):
            matches = filter_commands(query)
            if matches:
                opt_list.clear_options()
                for cmd in matches:
                    line = Text()
                    line.append(f"{cmd.command:<12}", style="bold #7EE0D2")
                    line.append(f"{cmd.title:<24}", style="bold #ACE1AF")
                    line.append(f" {cmd.description}", style="dim #7E9F93")
                    opt_list.add_option(Option(prompt=line, id=cmd.command))
                container.styles.display = "block"
                return
        container.styles.display = "none"
