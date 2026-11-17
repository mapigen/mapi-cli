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
        command="/call",
        title="Execute API Call",
        description="Call selected operation with arguments and inspect response (e.g. /call id=25)",
        category="Execution",
        shortcut="c",
        aliases=["/run", "/execute"],
        handler_action="action_call_operation",
    ),
    CommandItem(
        command="/inspect",
        title="Inspect Requirements & Auth",
        description="View required arguments, parameters, types, and auth schemes",
        category="Discovery",
        shortcut="i",
        aliases=["/reqs", "/params"],
        handler_action="action_inspect_requirements",
    ),
    CommandItem(
        command="/dry-run",
        title="Dry Run Inspection",
        description="Prepare and validate operation request without sending network traffic",
        category="Execution",
        shortcut="",
        aliases=["/dry"],
        handler_action="action_dry_run_operation",
    ),
    CommandItem(
        command="/curl",
        title="Generate cURL",
        description="Generate equivalent curl command for the operation",
        category="Execution",
        shortcut="",
        aliases=[],
        handler_action="action_curl_operation",
    ),
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
    """Filter and rank commands dynamically as the user types (prefix, alias, title, or description match)."""
    q = query.strip().lower()
    if not q or q == "/":
        return DEFAULT_COMMANDS

    is_slash = q.startswith("/")
    term = q[1:] if is_slash else q

    scored: list[tuple[int, CommandItem]] = []
    for cmd in DEFAULT_COMMANDS:
        cmd_bare = cmd.command.lstrip("/")
        score = 0
        if cmd_bare == term or cmd.command == q:
            score = 100
        elif cmd_bare.startswith(term):
            score = 80
        elif any(alias.lstrip("/").startswith(term) for alias in cmd.aliases):
            score = 60
        elif term in cmd_bare:
            score = 50
        elif any(term in alias.lstrip("/") for alias in cmd.aliases):
            score = 40
        elif not is_slash or len(term) >= 3:
            if term in cmd.title.lower():
                score = 30
            elif term in cmd.description.lower():
                score = 20

        if score > 0:
            scored.append((score, cmd))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [cmd for _, cmd in scored]


class CommandPaletteWidget(Widget):
    """Interactive '/' command palette and live search bar."""

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
                opt_list.highlighted = 0
                container.styles.display = "block"
                return
        container.styles.display = "none"
