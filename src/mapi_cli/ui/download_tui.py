from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Static,
)

from mapi_cli.commands.download import _download_and_compile, _is_api_local
from mapi_cli.paths import resolve_data_dir


class DownloadTUIApp(App[None]):
    """Interactive Textual TUI for browsing and downloading MAPI API specifications."""

    TITLE = "MAPI Specification Manager"
    SUB_TITLE = "Arrow Keys (↑/↓) to navigate • Enter to download"

    CSS = """
    Screen {
        background: #0d1117;
        color: #c9d1d9;
    }

    #header_container {
        height: auto;
        padding: 0 1;
        background: #161b22;
        border-bottom: heavy #30363d;
    }

    #path_label {
        color: #8b949e;
        padding-top: 1;
    }

    #filter_input {
        margin: 1 0;
        background: #0d1117;
        border: tall #30363d;
        color: #58a6ff;
    }

    #filter_input:focus {
        border: tall #58a6ff;
    }

    #table_container {
        height: 1fr;
        padding: 0 1;
    }

    #providers_table {
        height: 1fr;
        background: #161b22;
        border: round #30363d;
    }

    #providers_table:focus {
        border: round #58a6ff;
    }

    #status_panel {
        height: auto;
        min-height: 4;
        max-height: 6;
        background: #161b22;
        border-top: heavy #30363d;
        padding: 0 1;
    }

    #status_text {
        color: #8b949e;
        padding-top: 1;
    }

    #loader {
        height: 2;
        color: #58a6ff;
        display: none;
    }
    """

    BINDINGS = [
        Binding("enter", "download_selected", "Download Selected", priority=True),
        Binding("a", "download_all", "Download All"),
        Binding("f", "toggle_force", "Toggle Force"),
        Binding("slash", "focus_filter", "Search / Filter", key_display="/"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "escape_action", "Clear / Quit", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, client: Any, data_dir: Path | None = None) -> None:
        super().__init__()
        self.client = client
        self.data_dir: Path = data_dir or resolve_data_dir()[0]
        self.force: bool = False
        self._is_busy: bool = False
        self._all_items: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="header_container"):
            yield Label(
                f"[bold cyan]Active Storage:[/] [white]{self.data_dir}[/]",
                id="path_label",
            )
            yield Input(
                placeholder="Search or filter providers (press / to focus, Esc to return)...",
                id="filter_input",
            )

        with Vertical(id="table_container"):
            yield DataTable[str](id="providers_table")

        with Vertical(id="status_panel"):
            yield LoadingIndicator(id="loader")
            yield Static(
                "[bold cyan]Tip:[/] Use [bold]↑/↓[/] to navigate rows, [bold]Enter[/] to download, [bold]a[/] for all, [bold]f[/] for force.",
                id="status_text",
            )

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#providers_table", DataTable)
        table.cursor_type = "row"
        table.add_column("Provider", key="provider")
        table.add_column("API", key="api")
        table.add_column("Status", key="status")
        table.add_column("Operations", key="ops")
        table.add_column("Auth", key="auth")
        table.add_column("Description", key="desc")

        self._load_registry_items()
        self._populate_table()
        table.focus()

    def _load_registry_items(self) -> None:
        discovery = self.client.discovery
        items: list[dict[str, Any]] = []
        for p in discovery.list_providers():
            for a in discovery.list_apis(p):
                info = discovery.get_api_info(p, a)
                src = (getattr(info, "sources", []) or ["github"])[0]
                is_dl = _is_api_local(self.data_dir, p, src, a)
                items.append(
                    {
                        "provider": p,
                        "api": a,
                        "source": src,
                        "downloaded": is_dl,
                        "operations": getattr(info, "operation_count", 0),
                        "auth": getattr(info, "primary_auth", "none"),
                        "description": getattr(info, "description", ""),
                        "spec_url": getattr(info, "spec_url", None),
                    }
                )
        self._all_items = items

    def _populate_table(self, query: str = "") -> None:
        table = self.query_one("#providers_table", DataTable)
        table.clear()

        q = query.strip().lower()
        for item in self._all_items:
            p = item["provider"]
            a = item["api"]
            desc = item["description"]
            if q and q not in p.lower() and q not in a.lower() and q not in desc.lower():
                continue

            row_key = f"{p}/{a}"
            status_text = (
                Text("Downloaded", style="bold green")
                if item["downloaded"]
                else Text("Not Downloaded", style="bold yellow")
            )

            table.add_row(
                Text(p, style="bold cyan"),
                Text(a, style="white"),
                status_text,
                Text(str(item["operations"]), style="green"),
                Text(item["auth"], style="yellow"),
                Text(desc, style="dim"),
                key=row_key,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter_input":
            self._populate_table(query=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        table = self.query_one("#providers_table", DataTable)
        table.focus()

    def action_focus_filter(self) -> None:
        self.query_one("#filter_input", Input).focus()

    def action_escape_action(self) -> None:
        filter_input = self.query_one("#filter_input", Input)
        if filter_input.has_focus:
            filter_input.value = ""
            self.query_one("#providers_table", DataTable).focus()
        else:
            self.exit()

    def action_toggle_force(self) -> None:
        self.force = not self.force
        status_label = self.query_one("#status_text", Static)
        if self.force:
            status_label.update("[bold yellow]Force mode ON:[/] Will re-download and re-compile existing specs.")
            self.notify("Force re-download enabled", severity="warning")
        else:
            status_label.update("[bold cyan]Force mode OFF:[/] Will skip already downloaded specs.")
            self.notify("Force mode disabled")

    def action_refresh_data(self) -> None:
        self._load_registry_items()
        filter_val = self.query_one("#filter_input", Input).value
        self._populate_table(query=filter_val)
        self.notify("Registry reloaded")

    def action_cursor_up(self) -> None:
        table = self.query_one("#providers_table", DataTable)
        table.action_cursor_up()

    def action_cursor_down(self) -> None:
        table = self.query_one("#providers_table", DataTable)
        table.action_cursor_down()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_download_selected()

    def action_download_selected(self) -> None:
        if self._is_busy:
            self.notify("A download task is already running...", severity="warning")
            return

        table = self.query_one("#providers_table", DataTable)
        if table.row_count == 0:
            return

        coordinate = table.cursor_coordinate
        row_key = table.coordinate_to_cell_key(coordinate).row_key
        if not row_key or not row_key.value:
            return

        key_str = str(row_key.value)
        provider, api = key_str.split("/", 1)
        self._run_single_download(provider, api)

    @work(thread=True, exclusive=True)
    def _run_single_download(self, provider: str, api: str) -> None:
        self._is_busy = True
        loader = self.query_one("#loader", LoadingIndicator)
        status_text = self.query_one("#status_text", Static)

        self.call_from_thread(loader.styles.display.__setattr__, "value", "block")
        self.call_from_thread(
            status_text.update,
            f"[bold cyan]Loading:[/] Fetching and compiling [bold]{provider}/{api}[/]...",
        )

        res = _download_and_compile(
            client=self.client,
            data_dir=self.data_dir,
            provider=provider,
            api=api,
            force=self.force,
        )

        status = res.get("status", "unknown")
        table = self.query_one("#providers_table", DataTable)
        row_key = f"{provider}/{api}"

        if status == "downloaded":
            new_status = Text("Downloaded", style="bold green")
            ops_text = Text(str(res.get("operations", 0)), style="green")
            self.call_from_thread(table.update_cell, row_key, "status", new_status)
            self.call_from_thread(table.update_cell, row_key, "ops", ops_text)
            self.call_from_thread(
                status_text.update,
                f"[bold green]✓ Downloaded {provider}/{api} successfully![/] "
                f"({res.get('operations', 0)} operations, {res.get('bytes', 0):,} bytes compiled)",
            )
            self.notify(f"Successfully downloaded {provider}/{api}", severity="information")
        elif status == "skipped":
            self.call_from_thread(
                status_text.update,
                f"[yellow]Skipped {provider}/{api}:[/] Already downloaded (press 'f' to force re-download).",
            )
            self.notify(f"{provider}/{api} is already downloaded", severity="warning")
        else:
            err_msg = res.get("message", "Unknown error")
            self.call_from_thread(
                status_text.update,
                f"[bold red]✗ Failed to download {provider}/{api}:[/] {err_msg}",
            )
            self.notify(f"Error downloading {provider}/{api}", severity="error")

        self.call_from_thread(loader.styles.display.__setattr__, "value", "none")
        self._is_busy = False

    def action_download_all(self) -> None:
        if self._is_busy:
            self.notify("A download task is already running...", severity="warning")
            return
        self._run_all_downloads()

    @work(thread=True, exclusive=True)
    def _run_all_downloads(self) -> None:
        self._is_busy = True
        loader = self.query_one("#loader", LoadingIndicator)
        status_text = self.query_one("#status_text", Static)
        table = self.query_one("#providers_table", DataTable)

        self.call_from_thread(loader.styles.display.__setattr__, "value", "block")

        items_to_sync = [
            item for item in self._all_items if self.force or not item["downloaded"]
        ]

        if not items_to_sync:
            self.call_from_thread(
                status_text.update,
                "[bold green]All specifications are already downloaded locally![/]",
            )
            self.call_from_thread(loader.styles.display.__setattr__, "value", "none")
            self._is_busy = False
            return

        total = len(items_to_sync)
        success_count = 0

        for idx, item in enumerate(items_to_sync, start=1):
            p = item["provider"]
            a = item["api"]
            self.call_from_thread(
                status_text.update,
                f"[bold cyan]Downloading ({idx}/{total}):[/] [bold]{p}/{a}[/]...",
            )

            res = _download_and_compile(
                client=self.client,
                data_dir=self.data_dir,
                provider=p,
                api=a,
                force=self.force,
            )

            row_key = f"{p}/{a}"
            if res.get("status") == "downloaded":
                success_count += 1
                new_status = Text("Downloaded", style="bold green")
                ops_text = Text(str(res.get("operations", 0)), style="green")
                self.call_from_thread(table.update_cell, row_key, "status", new_status)
                self.call_from_thread(table.update_cell, row_key, "ops", ops_text)

        self.call_from_thread(
            status_text.update,
            f"[bold green]Batch download complete![/] {success_count}/{total} specifications downloaded.",
        )
        self.call_from_thread(loader.styles.display.__setattr__, "value", "none")
        self.notify(f"Batch completed: {success_count}/{total} downloaded")
        self._is_busy = False
