from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.text import Text
from textual import events, work
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
from mapi_cli.ui.banner import render_banner
from mapi_cli.ui.styles import CELADON_DARK, CELADON_LIGHT, build_app_tcss


class DownloadTUIApp(App[None]):
    """Interactive Textual TUI for browsing and downloading MAPI API specifications."""

    TITLE = "MAPI Specification Manager"
    SUB_TITLE = "Arrow Keys (↑/↓) navigate • Ctrl+← / Ctrl+→ pages • Enter download • t: theme • /: search"
    CSS = build_app_tcss()

    BINDINGS = [
        Binding("enter", "download_selected", "Download Selected", priority=True),
        Binding("ctrl+left", "page_back", "Prev Page", key_display="Ctrl+←"),
        Binding("ctrl+right", "page_forward", "Next Page", key_display="Ctrl+→"),
        Binding("a", "download_all", "Download All"),
        Binding("f", "toggle_force", "Toggle Force"),
        Binding("t", "toggle_theme", "Toggle Celadon Theme"),
        Binding("slash", "focus_filter", "Search / Filter", key_display="/"),
        Binding("escape", "clear_filter", "Clear Filter / Unfocus"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        client: Any,
        data_dir: Path | None = None,
        force: bool = False,
    ) -> None:
        super().__init__()
        self.client = client
        self.data_dir = data_dir or resolve_data_dir()[0]
        self.force = force
        self.is_dark: bool = True
        self._all_items: list[dict[str, Any]] = []
        self._is_busy = False
        self.page_number: int = 1
        self.page_size: int = 25
        self.total_pages: int = 1

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="header_container"):
            yield Static(render_banner(self.is_dark), id="banner_static")
            yield Label(
                f"Platform Storage: [dim]{self.data_dir}[/] • Force mode: [{'bold yellow' if self.force else 'dim'}{'ON' if self.force else 'OFF'}[/]",
                id="path_label",
            )
        with Vertical(id="table_container"):
            yield DataTable(id="providers_table", cursor_type="row")
        with Vertical(id="command_container"):
            yield Input(
                placeholder="Type '/' or text to filter providers/APIs (Press 'Enter' to download selected)...",
                id="filter_input",
            )
        with Vertical(id="status_panel"):
            yield LoadingIndicator(id="loader")
            yield Static(
                "[dim]Ready. Select an API with ↑/↓ and press [bold]Enter[/] to download, or [bold]a[/] to download all.[/]",
                id="status_text",
            )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#providers_table", DataTable)
        table.add_column("Provider", key="provider", width=16)
        table.add_column("API", key="api", width=14)
        table.add_column("Status", key="status", width=16)
        table.add_column("Operations", key="ops", width=12)
        table.add_column("Upstream Specification URL", key="url")

        self._load_registry_data()
        self._populate_table()
        table.focus()

    def set_loading(self, visible: bool) -> None:
        """Thread-safe and exception-free loader display toggle."""
        loader = self.query_one("#loader", LoadingIndicator)
        loader.styles.display = "block" if visible else "none"

    def _load_registry_data(self) -> None:
        self._all_items.clear()
        providers = self.client.discovery.list_providers()

        for p in providers:
            apis = self.client.discovery.list_apis(p)
            for a in apis:
                try:
                    info = self.client.discovery.get_api_info(p, a)
                    sources = getattr(info, "sources", ["github"])
                    source = sources[0] if sources else "github"
                    spec_url = getattr(info, "spec_url", "") or ""
                    ops_count = getattr(info, "operation_count", 0)
                    is_local = _is_api_local(self.data_dir, p, source, a)
                except Exception:
                    source = "github"
                    spec_url = ""
                    ops_count = 0
                    is_local = False

                self._all_items.append(
                    {
                        "provider": p,
                        "api": a,
                        "source": source,
                        "spec_url": spec_url,
                        "operations": ops_count,
                        "downloaded": is_local,
                    }
                )

    def _populate_table(self, query: str = "") -> None:
        table = self.query_one("#providers_table", DataTable)
        table.clear()

        q = query.strip().lower()
        if q.startswith("/"):
            q = q[1:]

        matching = []
        for item in self._all_items:
            p = item["provider"]
            a = item["api"]
            url = item["spec_url"]
            if q and (q not in p.lower() and q not in a.lower() and q not in url.lower()):
                continue
            matching.append(item)

        self.total_pages = max(1, (len(matching) + self.page_size - 1) // self.page_size)
        self.page_number = max(1, min(self.page_number, self.total_pages))
        start_idx = (self.page_number - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(matching))
        page_items = matching[start_idx:end_idx]

        for item in page_items:
            p = item["provider"]
            a = item["api"]
            url = item["spec_url"]
            ops = str(item["operations"])
            is_dl = item["downloaded"]

            row_key = f"{p}/{a}"
            pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
            status_style = "bold green" if is_dl else f"dim {pal.text_muted}"
            status_str = "Downloaded" if is_dl else "Not Downloaded"

            table.add_row(
                Text(p, style=f"bold {pal.text}"),
                Text(a, style=pal.secondary),
                Text(status_str, style=status_style),
                Text(ops, style=pal.text_muted),
                Text(url or "(no remote spec)", style=f"dim {pal.text_muted}"),
                key=row_key,
            )

    def on_key(self, event: events.Key) -> None:
        if event.key in ("ctrl+left", "alt+left"):
            self.action_page_back()
            event.prevent_default()
            event.stop()
            return
        elif event.key in ("ctrl+right", "alt+right"):
            self.action_page_forward()
            event.prevent_default()
            event.stop()
            return

    def action_page_forward(self) -> None:
        if self.page_number < self.total_pages:
            self.page_number += 1
            input_widget = self.query_one("#filter_input", Input)
            self._populate_table(query=input_widget.value)
            self.notify(f"Page {self.page_number}/{self.total_pages}")
        else:
            self.notify(f"Already on last page ({self.total_pages}/{self.total_pages})", severity="information")

    def action_page_back(self) -> None:
        if self.page_number > 1:
            self.page_number -= 1
            input_widget = self.query_one("#filter_input", Input)
            self._populate_table(query=input_widget.value)
            self.notify(f"Page {self.page_number}/{self.total_pages}")
        else:
            self.notify("Already on first page", severity="information")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter_input":
            self._populate_table(query=event.value)

    def action_focus_filter(self) -> None:
        input_widget = self.query_one("#filter_input", Input)
        input_widget.focus()

    def action_clear_filter(self) -> None:
        filter_input = self.query_one("#filter_input", Input)
        if filter_input.value:
            filter_input.value = ""
        table = self.query_one("#providers_table", DataTable)
        table.focus()

    def action_toggle_theme(self) -> None:
        """Toggle Celadon Green theme between Dark and Light mode."""
        self.is_dark = not self.is_dark
        if self.is_dark:
            self.screen.remove_class("light-mode")
        else:
            self.screen.add_class("light-mode")

        banner = self.query_one("#banner_static", Static)
        banner.update(render_banner(self.is_dark))
        self._populate_table()
        mode_name = "Celadon Dark" if self.is_dark else "Celadon Light"
        self.notify(f"Theme switched to {mode_name}")

    def action_toggle_force(self) -> None:
        self.force = not self.force
        label = self.query_one("#path_label", Label)
        label.update(
            f"Platform Storage: [cyan]{self.data_dir}[/] • Force mode: [yellow]{'ON' if self.force else 'OFF'}[/]"
        )
        status_label = self.query_one("#status_text", Static)
        if self.force:
            status_label.update("[bold yellow]Force mode ON:[/] Will re-download and re-compile existing specs.")
            self.notify("Force mode enabled", severity="warning")
        else:
            status_label.update("[dim]Force mode OFF: Existing specs will be skipped.[/]")
            self.notify("Force mode disabled")

    def action_download_selected(self) -> None:
        if self._is_busy:
            self.notify("A download task is already running...", severity="warning")
            return

        table = self.query_one("#providers_table", DataTable)
        if table.row_count == 0:
            return

        coordinate = table.cursor_coordinate
        row_key_obj = table.coordinate_to_cell_key(coordinate).row_key
        if not row_key_obj:
            return

        key_str = str(getattr(row_key_obj, "value", row_key_obj))
        if "/" not in key_str:
            return

        provider, api = key_str.split("/", 1)
        self._run_single_download(provider, api)

    @work(thread=True, exclusive=True)
    def _run_single_download(self, provider: str, api: str) -> None:
        self._is_busy = True
        status_text = self.query_one("#status_text", Static)

        self.call_from_thread(self.set_loading, True)
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

        self.call_from_thread(self.set_loading, False)
        self._is_busy = False

    def action_download_all(self) -> None:
        if self._is_busy:
            self.notify("A download task is already running...", severity="warning")
            return
        self._run_all_downloads()

    @work(thread=True, exclusive=True)
    def _run_all_downloads(self) -> None:
        self._is_busy = True
        status_text = self.query_one("#status_text", Static)
        table = self.query_one("#providers_table", DataTable)

        self.call_from_thread(self.set_loading, True)

        items_to_sync = [
            item for item in self._all_items if self.force or not item["downloaded"]
        ]

        if not items_to_sync:
            self.call_from_thread(
                status_text.update,
                "[bold green]All specifications are already downloaded locally![/]",
            )
            self.call_from_thread(self.set_loading, False)
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
        self.call_from_thread(self.set_loading, False)
        self.notify(f"Batch completed: {success_count}/{total} downloaded")
        self._is_busy = False
