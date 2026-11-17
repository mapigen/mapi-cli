from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from mapi.models.request import RequestConfig
from mapi.models.response import MapiResult
from rich.markup import escape
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from mapi_cli.commands.download import _download_and_compile
from mapi_cli.operations import (
    OperationRequirementCheck,
    check_operation_requirements,
    execute_operation_call,
    parse_operation_call_args,
)
from mapi_cli.paths import resolve_data_dir
from mapi_cli.storage import get_api_storage_tier
from mapi_cli.ui.banner import render_banner
from mapi_cli.ui.command_palette import filter_commands
from mapi_cli.ui.operation_view import OperationRunnerPage, safe_markup
from mapi_cli.ui.styles import CELADON_DARK, CELADON_LIGHT, build_app_tcss, method_style


class MapiTUIApp(App[None]):
    """Default interactive Command Center & Exploration TUI for MAPI.

    Features:
        - '/' based intelligent command search with live auto-complete
        - Celadon Green light & dark mode themes (toggle with 't')
        - MAPI ASCII text art header
        - Interactive provider & API exploration
        - Seamless spec downloads
        - Direct operation call execution with requirement & auth inspection
    """

    TITLE = "MAPI"
    SUB_TITLE = "Type '/' for commands • Enter: open / select • c: call • Ctrl+← / Ctrl+→: pages • t: theme"
    CSS = build_app_tcss()

    BINDINGS = [
        Binding("enter", "select_row", "Select / Open"),
        Binding("ctrl+left", "page_back", "Back / Prev Page", key_display="Ctrl+←"),
        Binding("ctrl+right", "page_forward", "Forward / Next Page", key_display="Ctrl+→"),
        Binding("c", "call_action", "Call Endpoint"),
        Binding("i", "inspect_action", "Inspect Reqs & Auth"),
        Binding("slash", "focus_command_palette", "Commands / Search", key_display="/"),
        Binding("t", "toggle_theme", "Toggle Celadon Theme"),
        Binding("d", "download_selected", "Download"),
        Binding("a", "download_all", "Download All"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("escape", "escape_action", "Back / Clear"),
        Binding("backspace", "back_action", "Back", show=False),
        Binding("b", "back_action", "Back", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        client: Any,
        data_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.client = client
        self.data_dir = data_dir or resolve_data_dir()[0]
        self.is_dark: bool = True
        self._all_items: list[dict[str, Any]] = []
        self._current_operations: list[dict[str, Any]] = []
        self._is_busy: bool = False
        self.current_view: str = "providers"  # "providers", "operations", or "operation_detail"
        self.selected_provider: str | None = None
        self.selected_api: str | None = None
        self.selected_operation: str | None = None
        self._current_filter: str = ""
        self.page_number: int = 1
        self.page_size: int = 25
        self.total_pages: int = 1
        self._last_op_pages: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="header_container"):
            yield Static(render_banner(self.is_dark), id="banner_static")
        with Vertical(id="table_container"):
            yield DataTable(id="catalog_table", cursor_type="row")
            with Vertical(id="operation_runner_container"):
                pass
        with Vertical(id="command_container"):
            with Vertical(id="suggestions_container"):
                yield OptionList(id="suggestions_list")
            yield Input(
                placeholder="Type '/' for intelligent commands (e.g. /apis, /download, /theme) or type to filter...",
                id="command_input",
            )
        with Vertical(id="status_panel"):
            yield LoadingIndicator(id="loader")
            yield Static(
                "[dim]Ready. Press [bold]Enter[/] to inspect operations, [bold]d[/] to download, or [bold]/[/] for commands.[/]",
                id="status_text",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._setup_catalog_columns()
        self._load_data()
        self._populate_catalog()
        self.query_one("#catalog_table", DataTable).focus()

    def set_loading(self, visible: bool) -> None:
        """Safe thread helper to toggle loading spinner."""
        loader = self.query_one("#loader", LoadingIndicator)
        loader.styles.display = "block" if visible else "none"

    def _setup_catalog_columns(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.clear(columns=True)
        table.add_column("Provider", key="provider", width=16)
        table.add_column("API", key="api", width=14)
        table.add_column("Status", key="status", width=16)
        table.add_column("Operations", key="ops", width=12)
        table.add_column("Primary Auth", key="auth", width=14)
        table.add_column("Specification Source", key="url")

    def _load_data(self) -> None:
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
                    auth_type = getattr(info, "primary_auth", "none") or "none"
                    tier = get_api_storage_tier(self.client, self.data_dir, p, a, source)
                    tier_status = tier.status
                    is_cached = tier.is_cached
                    is_comp = tier.is_compressed
                    is_local = tier.is_downloaded
                except Exception:
                    source = "github"
                    spec_url = ""
                    ops_count = 0
                    auth_type = "none"
                    tier_status = "Not Downloaded"
                    is_cached = False
                    is_comp = False
                    is_local = False

                self._all_items.append(
                    {
                        "provider": p,
                        "api": a,
                        "source": source,
                        "spec_url": spec_url,
                        "operations": ops_count,
                        "auth": auth_type,
                        "status": tier_status,
                        "is_cached": is_cached,
                        "is_compressed": is_comp,
                        "downloaded": is_local,
                    }
                )

    def _populate_catalog(self, query: str = "") -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.clear()

        q = query.strip().lower()
        if q.startswith("/"):
            q = ""

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

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        for item in page_items:
            p = item["provider"]
            a = item["api"]
            url = item["spec_url"]
            ops = str(item["operations"])
            auth = item["auth"]
            is_dl = item["downloaded"]

            row_key = f"{p}/{a}"
            status_str = item.get("status", "Downloaded" if is_dl else "Not Downloaded")
            if status_str == "Cached":
                status_style = f"bold {pal.secondary}"
            elif status_str == "Compressed":
                status_style = f"bold {pal.primary}"
            elif status_str == "Downloaded":
                status_style = "bold green"
            else:
                status_style = f"dim {pal.text_muted}"

            table.add_row(
                Text(p, style=f"bold {pal.text}"),
                Text(a, style=pal.secondary),
                Text(status_str, style=status_style),
                Text(ops, style=pal.text_muted),
                Text(auth, style=f"dim {pal.text_muted}"),
                Text(url or "(no remote spec)", style=f"dim {pal.text_muted}"),
                key=row_key,
            )

    def _setup_operations_columns(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.clear(columns=True)
        table.add_column("Method", key="method", width=10)
        table.add_column("Operation ID", key="op", width=30)
        table.add_column("Path", key="path", width=42)
        table.add_column("Summary", key="summary")

    def _populate_operations(self, query: str = "") -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.clear()

        q = query.strip().lower()
        if q.startswith("/"):
            q = ""

        matching = []
        for item in self._current_operations:
            op_id = item["id"]
            op_name = item["operation_id"]
            m = item["method"]
            path = item["path"]
            summary = item["summary"]

            if q and (
                q not in op_id.lower()
                and q not in op_name.lower()
                and q not in m.lower()
                and q not in path.lower()
                and q not in summary.lower()
            ):
                continue
            matching.append(item)

        self.total_pages = max(1, (len(matching) + self.page_size - 1) // self.page_size)
        self.page_number = max(1, min(self.page_number, self.total_pages))
        start_idx = (self.page_number - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(matching))
        page_items = matching[start_idx:end_idx]

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        for item in page_items:
            op_id = item["id"]
            op_name = item["operation_id"]
            m = item["method"]
            path = item["path"]
            summary = item["summary"]

            table.add_row(
                Text(m, style=method_style(m)),
                Text(op_name, style=pal.text),
                Text(path, style=pal.text_muted),
                Text(summary, style=f"italic {pal.text_muted}"),
                key=op_id,
            )

        status_text = self.query_one("#status_text", Static)
        p_name = self.selected_provider or ""
        a_name = self.selected_api or ""
        total_ops = len(matching)
        range_str = f"{start_idx + 1}-{end_idx} of {total_ops}" if total_ops > 0 else "0 operations"
        status_text.update(
            f"[bold {pal.secondary}]{escape(p_name)}/{escape(a_name)}:[/] "
            f"Page [bold {pal.primary}]{self.page_number}[/] of [bold]{self.total_pages}[/] "
            f"({range_str}). "
            f"[dim]Ctrl+← / Ctrl+→: pages • ↑/↓: cursor • c: call • i: reqs[/]"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "command_input":
            val = event.value
            self._update_suggestions(val)
            if not val.startswith("/") and val != self._current_filter:
                self._current_filter = val
                if self.current_view == "operations":
                    self._populate_operations(query=val)
                else:
                    self._populate_catalog(query=val)

    def _update_suggestions(self, query: str) -> None:
        container = self.query_one("#suggestions_container", Vertical)
        opt_list = self.query_one("#suggestions_list", OptionList)

        if query.startswith("/"):
            matches = filter_commands(query)
            if matches:
                opt_list.clear_options()
                pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
                for cmd in matches:
                    line = Text()
                    line.append(f"{cmd.command:<14}", style=f"bold {pal.secondary}")
                    line.append(f"{cmd.title:<24}", style=f"bold {pal.text}")
                    line.append(f" {cmd.description}", style=f"dim {pal.text_muted}")
                    opt_list.add_option(Option(prompt=line, id=cmd.command))
                opt_list.highlighted = 0
                container.styles.display = "block"
                return
        container.styles.display = "none"

    def on_key(self, event: events.Key) -> None:
        input_widget = self.query_one("#command_input", Input)
        suggestions_container = self.query_one("#suggestions_container", Vertical)
        opt_list = self.query_one("#suggestions_list", OptionList)

        # 1. Page navigation via Ctrl+Left / Alt+Left (Back)
        if event.key in ("ctrl+left", "alt+left"):
            self.action_page_back()
            event.prevent_default()
            event.stop()
            return

        # 2. Page navigation via Ctrl+Right / Alt+Right (Forward)
        if event.key in ("ctrl+right", "alt+right"):
            self.action_page_forward()
            event.prevent_default()
            event.stop()
            return

        # 3. Input widget handling: Up/Down for suggestions or focus shift; Left/Right stay horizontal cursor movement
        if input_widget.has_focus:
            if suggestions_container.styles.display == "block" and opt_list.option_count > 0:
                if event.key == "down":
                    curr = opt_list.highlighted if opt_list.highlighted is not None else -1
                    opt_list.highlighted = (curr + 1) % opt_list.option_count
                    event.prevent_default()
                    event.stop()
                    return
                elif event.key == "up":
                    curr = opt_list.highlighted if opt_list.highlighted is not None else 0
                    opt_list.highlighted = (opt_list.option_count - 1) if curr <= 0 else curr - 1
                    event.prevent_default()
                    event.stop()
                    return
                elif event.key == "tab":
                    idx = opt_list.highlighted if opt_list.highlighted is not None else 0
                    opt = opt_list.get_option_at_index(idx)
                    input_widget.value = f"{opt.id} "
                    input_widget.cursor_position = len(input_widget.value)
                    event.prevent_default()
                    event.stop()
                    return
            elif event.key == "down":
                self.query_one("#catalog_table", DataTable).focus()
                event.prevent_default()
                event.stop()
                return

        table = self.query_one("#catalog_table", DataTable)
        if table.has_focus and event.key in ("backspace", "b") and self.current_view == "operations":
            self.action_page_back()
            event.prevent_default()
            event.stop()
            return

        if self.current_view == "operation_detail":
            focused = self.focused
            if not isinstance(focused, Input) and event.key in ("backspace", "b"):
                self.action_page_back()
                event.prevent_default()
                event.stop()
                return

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        cmd_id = event.option_id
        if cmd_id:
            self._execute_command(str(cmd_id))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        suggestions_container = self.query_one("#suggestions_container", Vertical)
        opt_list = self.query_one("#suggestions_list", OptionList)

        if suggestions_container.styles.display == "block" and opt_list.option_count > 0:
            idx = opt_list.highlighted if opt_list.highlighted is not None else 0
            opt = opt_list.get_option_at_index(idx)
            cmd_to_run = str(opt.id)
            tokens = val.split(maxsplit=1)
            if len(tokens) > 1:
                cmd_to_run = f"{cmd_to_run} {tokens[1]}"
            self._execute_command(cmd_to_run)
            return

        if val.startswith("/"):
            self._execute_command(val)
        else:
            self.query_one("#catalog_table", DataTable).focus()

    def _execute_command(self, cmd_str: str) -> None:
        container = self.query_one("#suggestions_container", Vertical)
        container.styles.display = "none"
        self._current_filter = ""
        input_widget = self.query_one("#command_input", Input)
        input_widget.value = ""

        tokens = cmd_str.split()
        if not tokens:
            self.query_one("#catalog_table", DataTable).focus()
            return

        root_cmd = tokens[0].lower()

        if root_cmd in ("/theme", "/mode", "/dark", "/light"):
            self.action_toggle_theme()
        elif root_cmd in ("/quit", "/exit", "/q"):
            self.exit()
        elif root_cmd in ("/download", "/sync", "/fetch"):
            if len(tokens) > 1:
                self._run_single_download_by_name(tokens[1])
            else:
                self.action_download_selected()
        elif root_cmd in ("/refresh", "/reload"):
            self.action_refresh_data()
        elif root_cmd in ("/apis", "/providers", "/catalog"):
            self.action_back_to_catalog()
        elif root_cmd in ("/ops", "/operations", "/endpoints"):
            if len(tokens) > 1:
                self._show_operations_for(tokens[1])
            else:
                self.action_select_row()
        elif root_cmd in ("/search", "/find", "/query"):
            query_term = " ".join(tokens[1:]) if len(tokens) > 1 else ""
            if self.current_view == "operations":
                self._populate_operations(query=query_term)
                self.notify(f"Filtering operations by '{query_term}'" if query_term else "Cleared operations filter")
            else:
                self._populate_catalog(query=query_term)
                self.notify(f"Filtering catalog by '{query_term}'" if query_term else "Cleared catalog filter")
        elif root_cmd in ("/call", "/run", "/execute", "/dry-run", "/dry", "/curl"):
            self._handle_call_command(cmd_str)
        elif root_cmd in ("/inspect", "/reqs", "/params"):
            if len(tokens) > 1:
                target_op = tokens[1]
                if self.selected_provider and self.selected_api:
                    self._inspect_requirements_for_op(self.selected_provider, self.selected_api, target_op)
                else:
                    self.notify("Open an API to inspect operations", severity="warning")
            else:
                self.action_inspect_action()
        elif root_cmd in ("/next", "/forward", "/n"):
            self.action_page_forward()
        elif root_cmd in ("/prev", "/back", "/p"):
            self.action_page_back()
        elif root_cmd in ("/help", "/?"):
            self.notify(
                "Commands: /call, /dry-run, /curl, /inspect, /next, /prev, /apis, /ops, /download, /search, /theme, /quit\n"
                "Shortcuts: Ctrl+← / Ctrl+→ (pages), c (call), i (inspect), Enter (select), ↑/↓ (cursor), d (download), t (theme)",
                title="MAPI Help",
                timeout=8,
            )
        else:
            self.notify(f"Unknown command '{cmd_str}'. Type '/' for list of commands.", severity="warning", markup=False)

        self.query_one("#catalog_table", DataTable).focus()

    def action_focus_command_palette(self) -> None:
        input_widget = self.query_one("#command_input", Input)
        input_widget.value = "/"
        input_widget.focus()
        input_widget.cursor_position = 1

    def action_back_to_catalog(self) -> None:
        if self.current_view == "operation_detail":
            self._close_operation_page()

        last_provider = self.selected_provider
        last_api = self.selected_api
        self.current_view = "providers"
        self.selected_provider = None
        self.selected_api = None
        self.selected_operation = None
        self._current_filter = ""
        self.page_number = 1
        input_widget = self.query_one("#command_input", Input)
        input_widget.value = ""
        self._setup_catalog_columns()
        self._populate_catalog()

        # Restore cursor to previous provider
        if last_provider and last_api:
            table = self.query_one("#catalog_table", DataTable)
            target_key = f"{last_provider}/{last_api}"
            try:
                row_idx = table.get_row_index(target_key)
                table.move_cursor(row=row_idx)
            except Exception:
                pass

        status_text = self.query_one("#status_text", Static)
        status_text.update(
            "[dim]Ready. Select an API and press [bold]Enter[/] or [bold]Ctrl+→[/] to explore endpoints, "
            "[bold]Ctrl+←[/] to go back, [bold]c[/] to call, or [bold]/[/] for commands.[/]"
        )
        self.query_one("#catalog_table", DataTable).focus()
        self.notify("Returned to Providers & APIs catalog")

    def action_back_action(self) -> None:
        if self.current_view == "operation_detail":
            self._close_operation_page()
        elif self.current_view == "operations":
            self.action_back_to_catalog()

    def action_escape_action(self) -> None:
        container = self.query_one("#suggestions_container", Vertical)
        if container.styles.display == "block":
            container.styles.display = "none"
            if self.current_view == "operation_detail":
                try:
                    page = self.query_one(OperationRunnerPage)
                    self._focus_first_input(page)
                except Exception:
                    pass
            else:
                self.query_one("#catalog_table", DataTable).focus()
            return

        input_widget = self.query_one("#command_input", Input)
        if input_widget.value:
            input_widget.value = ""
            if self.current_view == "operations":
                self._populate_operations()
                self.query_one("#catalog_table", DataTable).focus()
            elif self.current_view == "providers":
                self._populate_catalog()
                self.query_one("#catalog_table", DataTable).focus()
            return

        if self.current_view == "operation_detail":
            self._close_operation_page()
            return

        if self.current_view == "operations":
            self.action_back_to_catalog()
            return

        self.query_one("#catalog_table", DataTable).focus()

    def action_toggle_theme(self) -> None:
        self.is_dark = not self.is_dark
        if self.is_dark:
            self.screen.remove_class("light-mode")
        else:
            self.screen.add_class("light-mode")

        banner = self.query_one("#banner_static", Static)
        banner.update(render_banner(self.is_dark))
        if self.current_view == "operations":
            self._populate_operations()
        elif self.current_view == "operation_detail":
            try:
                page = self.query_one(OperationRunnerPage)
                page.set_theme(self.is_dark)
            except Exception:
                pass
        else:
            self._populate_catalog()
        mode_name = "Celadon Dark" if self.is_dark else "Celadon Light"
        self.notify(f"Theme switched to {mode_name}")

    def action_refresh_data(self) -> None:
        self._load_data()
        if self.current_view == "operations" and self.selected_provider:
            self._show_operations_for(self.selected_provider, self.selected_api)
        elif self.current_view == "operation_detail" and self.selected_operation:
            self._open_operation_page(self.selected_operation)
        else:
            self._populate_catalog()
        self.notify("Registry and local specifications reloaded")

    def action_select_row(self) -> None:
        if self.current_view == "operation_detail":
            try:
                page = self.query_one(OperationRunnerPage)
                self.post_message(
                    OperationRunnerPage.RunRequested(
                        chk=page.chk,
                        kwargs=page.get_collected_inputs(),
                        dry_run=False,
                        emit_curl=False,
                    )
                )
            except Exception:
                pass
            return

        table = self.query_one("#catalog_table", DataTable)
        if table.row_count == 0:
            return
        coordinate = table.cursor_coordinate
        row_key_obj = table.coordinate_to_cell_key(coordinate).row_key
        if not row_key_obj:
            return
        key_str = str(getattr(row_key_obj, "value", row_key_obj))

        if self.current_view == "providers":
            if "/" not in key_str:
                return
            provider, api = key_str.split("/", 1)
            self._show_operations_for(provider, api)
        elif self.current_view == "operations":
            self.selected_operation = key_str
            self._open_operation_page(key_str)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key_str = str(getattr(event.row_key, "value", event.row_key))
        if self.current_view == "providers":
            if "/" in key_str:
                provider, api = key_str.split("/", 1)
                self._show_operations_for(provider, api)
        elif self.current_view == "operations":
            self.selected_operation = key_str
            self._open_operation_page(key_str)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self.current_view == "operations" and event.row_key:
            self.selected_operation = str(getattr(event.row_key, "value", event.row_key))

    def _get_selected_operation_id(self) -> str | None:
        table = self.query_one("#catalog_table", DataTable)
        if table.row_count > 0:
            coordinate = table.cursor_coordinate
            row_key_obj = table.coordinate_to_cell_key(coordinate).row_key
            if row_key_obj:
                key_str = str(getattr(row_key_obj, "value", row_key_obj))
                self.selected_operation = key_str
                return key_str
        return self.selected_operation

    def _get_selected_provider_key(self) -> str | None:
        table = self.query_one("#catalog_table", DataTable)
        if table.row_count > 0:
            coordinate = table.cursor_coordinate
            row_key_obj = table.coordinate_to_cell_key(coordinate).row_key
            if row_key_obj:
                return str(getattr(row_key_obj, "value", row_key_obj))
        if self._all_items:
            first = self._all_items[0]
            return f"{first['provider']}/{first['api']}"
        return None

    def action_page_forward(self) -> None:
        if self.current_view == "providers":
            if self.page_number < self.total_pages:
                self.page_number += 1
                self._populate_catalog(query=self._current_filter)
                self.notify(f"Providers Catalog: Page {self.page_number}/{self.total_pages}")
            else:
                key_str = self._get_selected_provider_key()
                if key_str and "/" in key_str:
                    provider, api = key_str.split("/", 1)
                    self._show_operations_for(provider, api)
                else:
                    self.notify("Select an API to explore operations", severity="information")
        elif self.current_view == "operations":
            if self.page_number < self.total_pages:
                self.page_number += 1
                if self.selected_provider and self.selected_api:
                    self._last_op_pages[f"{self.selected_provider}/{self.selected_api}"] = self.page_number
                self._populate_operations(query=self._current_filter)
                table = self.query_one("#catalog_table", DataTable)
                if table.row_count > 0:
                    table.move_cursor(row=0)
                self.notify(f"Operations: Page {self.page_number}/{self.total_pages}")
            else:
                op_id = self._get_selected_operation_id()
                if op_id:
                    self._open_operation_page(op_id)
                else:
                    self.notify(f"Already on the last page ({self.total_pages}/{self.total_pages})", severity="information")
        elif self.current_view == "operation_detail":
            self.notify("Already on Operation Runner page", severity="information")

    def action_page_back(self) -> None:
        if self.current_view == "operation_detail":
            self._close_operation_page()
            return
        elif self.current_view == "operations":
            if self.page_number > 1:
                self.page_number -= 1
                if self.selected_provider and self.selected_api:
                    self._last_op_pages[f"{self.selected_provider}/{self.selected_api}"] = self.page_number
                self._populate_operations(query=self._current_filter)
                table = self.query_one("#catalog_table", DataTable)
                if table.row_count > 0:
                    table.move_cursor(row=0)
                self.notify(f"Operations: Page {self.page_number}/{self.total_pages}")
            else:
                self.action_back_to_catalog()
        elif self.current_view == "providers":
            if self.page_number > 1:
                self.page_number -= 1
                self._populate_catalog(query=self._current_filter)
                self.notify(f"Providers Catalog: Page {self.page_number}/{self.total_pages}")
            else:
                self.notify("Already at top level (Providers & APIs catalog)", severity="information")

    def action_inspect_action(self) -> None:
        if self.current_view != "operations" or not self.selected_provider or not self.selected_api:
            self.notify(
                "Open an API operation to inspect requirements (press Enter on an API)",
                severity="warning",
            )
            return
        op_id = self._get_selected_operation_id()
        if not op_id:
            return
        self._inspect_requirements_for_op(self.selected_provider, self.selected_api, op_id, show_popup=True)

    def action_call_action(self) -> None:
        if self.current_view == "operation_detail":
            try:
                page = self.query_one(OperationRunnerPage)
                page.post_message(
                    OperationRunnerPage.RunRequested(
                        chk=page.chk,
                        kwargs=page.get_collected_inputs(),
                        dry_run=False,
                        emit_curl=False,
                    )
                )
            except Exception:
                pass
            return

        if self.current_view != "operations" or not self.selected_provider or not self.selected_api:
            self.notify(
                "Select an API operation to call (press Enter to explore endpoints, then press 'c')",
                severity="warning",
            )
            return

        op_id = self._get_selected_operation_id()
        if not op_id:
            return

        chk = self._inspect_requirements_for_op(
            self.selected_provider, self.selected_api, op_id, show_popup=False
        )
        if not chk:
            return

        input_widget = self.query_one("#command_input", Input)
        if chk.missing_parameters:
            arg_hints = " ".join([f"{p.name}=" for p in chk.missing_parameters])
            input_widget.value = f"/call {arg_hints}"
            input_widget.focus()
            input_widget.cursor_position = len(input_widget.value)
            self.notify(
                f"Enter required parameters: {', '.join([p.name for p in chk.missing_parameters])}",
                title="Arguments Required",
                severity="warning",
            )
        elif chk.auth.is_required and not chk.auth.is_configured:
            input_widget.value = "/call token="
            input_widget.focus()
            input_widget.cursor_position = len(input_widget.value)
            self.notify(
                f"Authentication required. Enter token or set {chk.auth.env_var_name}",
                title="Auth Required",
                severity="warning",
            )
        else:
            input_widget.value = "/call "
            input_widget.focus()
            input_widget.cursor_position = len(input_widget.value)
            self.notify(
                f"Ready to call {chk.operation_id}. Press Enter to execute or type additional args.",
                title="Ready to Call",
            )

    def _inspect_requirements_for_op(
        self,
        provider: str,
        api: str,
        op_id: str,
        kwargs: dict[str, Any] | None = None,
        show_popup: bool = True,
    ) -> OperationRequirementCheck | None:
        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        status_text = self.query_one("#status_text", Static)
        try:
            chk = check_operation_requirements(self.client, provider, api, op_id, kwargs=kwargs)
        except Exception:
            self._inspect_operation_fallback(op_id, show_popup=show_popup)
            return None

        if chk.required_parameters:
            req_list = [
                f"[bold red]{safe_markup(p.name)}[/]({safe_markup(p.in_)}:{safe_markup(p.type_str)})"
                for p in chk.required_parameters
            ]
            req_str = ", ".join(req_list)
        else:
            req_str = "[dim]None[/]"

        if chk.optional_parameters:
            opt_list = [
                f"{safe_markup(p.name)}({safe_markup(p.in_)}:{safe_markup(p.type_str)})"
                for p in chk.optional_parameters
            ]
            opt_str = ", ".join(opt_list[:4])
            if len(opt_list) > 4:
                opt_str += f" (+{len(opt_list) - 4} more)"
        else:
            opt_str = "[dim]None[/]"

        auth_msg = chk.auth.message
        if chk.auth.is_required and not chk.auth.is_configured:
            auth_display = f"[bold yellow]Auth:[/] {safe_markup(auth_msg)}"
        elif chk.auth.is_required:
            auth_display = f"[bold green]Auth:[/] {safe_markup(auth_msg)}"
        else:
            auth_display = f"[dim]Auth:[/] {safe_markup(auth_msg)}"

        status_text.update(
            f"[bold green]{safe_markup(chk.method)}[/] [bold {pal.secondary}]{safe_markup(chk.path)}[/] • "
            f"ID: [bold {pal.text}]{safe_markup(chk.operation_id)}[/] • "
            f"[bold]Req:[/] {req_str} • "
            f"[dim]Opt:[/] {opt_str} • "
            f"{auth_display}"
        )

        if show_popup:
            notify_lines = [
                f"{chk.method} {chk.path} (ID: {chk.operation_id})",
                f"Required: {', '.join([p.name for p in chk.required_parameters]) or 'None'}",
                f"Auth: {chk.auth.message}",
                f"Status: {'Ready' if chk.can_execute else 'Missing inputs'}",
                f"Call: {chk.example_call}",
            ]
            self.notify(
                "\n".join(notify_lines),
                title=f"Operation: {chk.operation_id}",
                timeout=8,
            )
        return chk

    def _inspect_operation_by_id(self, op_id: str) -> None:
        if self.selected_provider and self.selected_api:
            chk = self._inspect_requirements_for_op(
                self.selected_provider,
                self.selected_api,
                op_id,
                show_popup=True,
            )
            if chk:
                return
        self._inspect_operation_fallback(op_id, show_popup=True)

    def _inspect_operation_fallback(self, op_id: str, show_popup: bool = True) -> None:
        op_item = next((op for op in self._current_operations if op["id"] == op_id), None)
        if not op_item:
            return

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        m = op_item["method"]
        path = op_item["path"]
        op_name = op_item["operation_id"]
        summary = op_item["summary"] or "No summary provided"

        param_strs = []
        for p in op_item["parameters"]:
            p_name = getattr(p, "name", None) or getattr(p, "component_name", str(p))
            p_in = getattr(p, "in_", "")
            is_req = getattr(p, "is_required", False)
            req_tag = "*" if is_req else ""
            param_strs.append(f"{p_name}{req_tag}({p_in})")

        params_display = ", ".join(param_strs[:6]) if param_strs else "None"
        if len(param_strs) > 6:
            params_display += f" (+{len(param_strs) - 6} more)"

        status_text = self.query_one("#status_text", Static)
        status_text.update(
            f"[bold green]{escape(m)}[/] [bold {pal.secondary}]{escape(path)}[/] • "
            f"ID: [bold {pal.text}]{escape(op_name)}[/] • "
            f"Params: [dim]{escape(params_display)}[/] • "
            f"[italic {pal.text_muted}]{escape(summary)}[/]"
        )
        if show_popup:
            self.notify(
                f"{m} {path}\nOp: {op_name}\nParams: {params_display}\n{summary}",
                title=f"Operation: {op_name}",
                timeout=6,
            )

    def _open_operation_page(
        self,
        op_id: str,
        initial_kwargs: dict[str, Any] | None = None,
    ) -> None:
        if not self.selected_provider or not self.selected_api:
            return

        chk = self._inspect_requirements_for_op(
            self.selected_provider,
            self.selected_api,
            op_id,
            kwargs=initial_kwargs,
            show_popup=False,
        )
        if not chk:
            return

        table = self.query_one("#catalog_table", DataTable)
        table.styles.display = "none"

        container = self.query_one("#operation_runner_container", Vertical)
        container.remove_children()

        page = OperationRunnerPage(
            chk=chk,
            is_dark=self.is_dark,
            initial_kwargs=initial_kwargs,
        )
        container.mount(page)
        container.styles.display = "block"

        self.current_view = "operation_detail"
        self.selected_operation = op_id

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        status_text = self.query_one("#status_text", Static)
        status_text.update(
            f"[bold {pal.secondary}]{escape(chk.provider)}/{escape(chk.api)}:[/] "
            f"ID: [bold {pal.text}]{escape(chk.operation_id)}[/] • "
            f"[dim]Fill in inputs and press Run Request or Ctrl+← to return.[/]"
        )

        self._focus_first_input(page)

    def _focus_first_input(self, page: OperationRunnerPage) -> None:
        if page.chk.required_parameters:
            first_p = page.chk.required_parameters[0]
            with contextlib.suppress(Exception):
                page.query_one(f"#op_input_{first_p.name}", Input).focus()
                return
        elif page.chk.optional_parameters:
            first_p = page.chk.optional_parameters[0]
            with contextlib.suppress(Exception):
                page.query_one(f"#op_input_{first_p.name}", Input).focus()
                return
        with contextlib.suppress(Exception):
            page.query_one("#btn_run", Button).focus()

    def _close_operation_page(self) -> None:
        if self.current_view != "operation_detail":
            return

        container = self.query_one("#operation_runner_container", Vertical)
        container.styles.display = "none"
        container.remove_children()

        table = self.query_one("#catalog_table", DataTable)
        table.styles.display = "block"

        self.current_view = "operations"

        if self.selected_operation:
            try:
                row_idx = table.get_row_index(self.selected_operation)
                table.move_cursor(row=row_idx)
            except Exception:
                pass

        table.focus()

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        status_text = self.query_one("#status_text", Static)
        p_name = self.selected_provider or ""
        a_name = self.selected_api or ""
        total_ops = len(self._current_operations)
        start_idx = (self.page_number - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_ops)
        range_str = f"{start_idx + 1}-{end_idx} of {total_ops}" if total_ops > 0 else "0 operations"
        status_text.update(
            f"[bold {pal.secondary}]{escape(p_name)}/{escape(a_name)}:[/] "
            f"Page [bold {pal.primary}]{self.page_number}[/] of [bold]{self.total_pages}[/] "
            f"({range_str}). "
            f"[dim]Ctrl+← / Ctrl+→: pages • ↑/↓: cursor • Enter: open page • c: call[/]"
        )
        self.notify("Returned to operations list")

    def on_operation_runner_page_run_requested(
        self,
        event: OperationRunnerPage.RunRequested,
    ) -> None:
        chk = check_operation_requirements(
            self.client,
            event.chk.provider,
            event.chk.api,
            event.chk.operation_id,
            kwargs=event.kwargs,
        )

        if not chk.can_execute and not (event.dry_run or event.emit_curl):
            try:
                page = self.query_one(OperationRunnerPage)
                page.display_error(
                    chk.status_summary,
                    f"{chk.provider}/{chk.api}/{chk.operation_id}",
                )
            except Exception:
                pass
            status_text = self.query_one("#status_text", Static)
            status_text.update(f"[bold red]Cannot Call:[/] {safe_markup(chk.status_summary)}")
            self.notify(chk.status_summary, title="Requirements Not Met", severity="warning", markup=False)
            return

        self._run_call(
            chk=chk,
            kwargs=event.kwargs,
            dry_run=event.dry_run,
            emit_curl=event.emit_curl,
        )

    def on_operation_runner_page_back_requested(
        self,
        event: OperationRunnerPage.BackRequested,
    ) -> None:
        self._close_operation_page()

    def _handle_call_command(self, cmd_str: str) -> None:
        tokens = cmd_str.split()
        if not tokens:
            return
        root_cmd = tokens[0].lower()
        dry_run = root_cmd in ("/dry-run", "/dry")
        emit_curl = root_cmd == "/curl"

        args_tokens = tokens[1:]

        provider = self.selected_provider
        api = self.selected_api
        target_op = None

        if args_tokens and not args_tokens[0].startswith("-") and "=" not in args_tokens[0]:
            candidate = args_tokens[0]
            if "/" in candidate:
                parts = candidate.strip("/").split("/")
                if len(parts) >= 3:
                    provider = parts[0]
                    api = parts[1]
                    target_op = parts[2]
                    args_tokens = args_tokens[1:]
                elif len(parts) == 2:
                    provider = parts[0]
                    api = parts[1]
                    args_tokens = args_tokens[1:]
            elif self.current_view in ("operations", "operation_detail"):
                matching_op = next(
                    (
                        op["id"]
                        for op in self._current_operations
                        if op["id"] == candidate or op["operation_id"] == candidate
                    ),
                    None,
                )
                if matching_op:
                    target_op = matching_op
                    args_tokens = args_tokens[1:]

        if not target_op:
            if self.current_view == "operation_detail":
                target_op = self.selected_operation
            elif self.current_view == "operations":
                target_op = self._get_selected_operation_id()

        if not provider or not api or not target_op:
            self.notify(
                "Specify target operation (e.g. /call pokeapi/REST/pokemon_retrieve id=25) "
                "or open an operation in the TUI.",
                severity="warning",
            )
            return

        try:
            temp_chk = check_operation_requirements(self.client, provider, api, target_op)
        except Exception as exc:
            self.notify(f"Could not load operation '{target_op}': {exc}", severity="error", markup=False)
            return

        form_kwargs: dict[str, Any] = {}
        if self.current_view == "operation_detail":
            try:
                page = self.query_one(OperationRunnerPage)
                form_kwargs = page.get_collected_inputs()
            except Exception:
                pass

        parsed_kwargs = parse_operation_call_args(args_tokens, params_spec=temp_chk.parameters)
        kwargs = {**form_kwargs, **parsed_kwargs}
        chk = check_operation_requirements(self.client, provider, api, target_op, kwargs=kwargs)

        if not chk.can_execute and not (dry_run or emit_curl):
            status_text = self.query_one("#status_text", Static)
            status_text.update(f"[bold red]Cannot Call:[/] {safe_markup(chk.status_summary)}")
            if self.current_view == "operation_detail":
                try:
                    page = self.query_one(OperationRunnerPage)
                    page.display_error(
                        chk.status_summary,
                        f"{chk.provider}/{chk.api}/{chk.operation_id}",
                    )
                except Exception:
                    pass
            self.notify(chk.status_summary, title="Requirements Not Met", severity="warning", markup=False)
            return

        self._run_call(chk, kwargs, dry_run=dry_run, emit_curl=emit_curl)

    @work(thread=True, exclusive=True)
    def _run_call(
        self,
        chk: OperationRequirementCheck,
        kwargs: dict[str, Any],
        dry_run: bool = False,
        emit_curl: bool = False,
    ) -> None:
        self._is_busy = True
        status_text = self.query_one("#status_text", Static)
        self.call_from_thread(self.set_loading, True)

        call_target = f"{chk.provider}/{chk.api}/{chk.operation_id}"
        kwargs_desc = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        action_name = "Dry-run" if dry_run else ("cURL" if emit_curl else "Calling")
        self.call_from_thread(
            status_text.update,
            f"[bold cyan]{action_name}:[/] [bold]{call_target}[/]({kwargs_desc})...",
        )

        runner_page = None
        try:
            runner_page = self.query_one(OperationRunnerPage)
            self.call_from_thread(runner_page.set_executing, f"{action_name}...")
        except Exception:
            pass

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT

        try:
            res = execute_operation_call(
                self.client,
                chk,
                kwargs,
                dry_run=dry_run,
                emit_curl=emit_curl,
            )
            if emit_curl and isinstance(res, RequestConfig):
                curl_cmd = res.to_curl()
                self.call_from_thread(
                    status_text.update,
                    f"[bold green]cURL:[/] {escape(curl_cmd)}",
                )
                self.notify(f"cURL ready for {chk.operation_id}", title="cURL Generated")
                if runner_page:
                    self.call_from_thread(
                        runner_page.display_result,
                        res,
                        call_target,
                        None,
                        True,
                    )
            elif dry_run and isinstance(res, RequestConfig):
                self.call_from_thread(
                    status_text.update,
                    f"[bold green]✓ Dry-Run:[/] {res.method} {escape(res.url)} • Headers: {len(res.headers)}",
                )
                self.notify(f"Dry run ready: {res.method} {res.url}", title="Dry Run", markup=False)
                if runner_page:
                    self.call_from_thread(runner_page.display_result, res, f"Dry-Run {call_target}")
            elif isinstance(res, MapiResult):
                status_code = getattr(res.metadata, "http_status", 200) or 200
                duration_ms = getattr(res.metadata, "duration_ms", 0)
                data = res.data
                if isinstance(data, dict):
                    data_summary = ", ".join(
                        f"{k}={repr(v)[:24]}" for k, v in list(data.items())[:4]
                    )
                elif isinstance(data, list):
                    data_summary = f"list of {len(data)} items"
                else:
                    data_summary = repr(data)[:80]

                self.call_from_thread(
                    status_text.update,
                    f"[bold green]✓ {status_code} OK[/] [dim]({duration_ms}ms)[/] • "
                    f"[bold {pal.secondary}]{call_target}[/] • [dim]{safe_markup(data_summary)}[/]",
                )
                self.notify(
                    f"{status_code} OK ({duration_ms}ms)\n{data_summary}",
                    title=f"Call Succeeded: {chk.operation_id}",
                    timeout=8,
                    markup=False,
                )
                if runner_page:
                    self.call_from_thread(runner_page.display_result, res, call_target, duration_ms)
        except Exception as exc:
            err_msg = str(exc)
            self.call_from_thread(
                status_text.update,
                f"[bold red]✗ Call Failed:[/] {safe_markup(err_msg)}",
            )
            self.notify(f"Call failed: {err_msg}", title="Call Error", severity="error", markup=False)
            if runner_page:
                self.call_from_thread(runner_page.display_error, err_msg, call_target)
        finally:
            self.call_from_thread(self.set_loading, False)
            self._is_busy = False

    def _show_operations_for(self, provider: str, api: str | None = None) -> None:
        if self.current_view == "operation_detail":
            container = self.query_one("#operation_runner_container", Vertical)
            container.styles.display = "none"
            container.remove_children()
            table = self.query_one("#catalog_table", DataTable)
            table.styles.display = "block"

        status_text = self.query_one("#status_text", Static)
        try:
            if "/" in provider and not api:
                provider, api = provider.split("/", 1)

            if not api:
                apis = self.client.discovery.list_apis(provider)
                if not apis:
                    self.notify(f"No APIs found for provider '{provider}'", severity="warning")
                    return
                api = apis[0]

            src = self.client.discovery._resolve_source(provider, api, None)
            sd = self.client.discovery._get_service_data(provider, api, src)

            self.current_view = "operations"
            self.selected_provider = provider
            self.selected_api = api

            op_key = f"{provider}/{api}"
            self.page_number = self._last_op_pages.get(op_key, 1)

            self._current_operations.clear()
            for op_id, op in sd.operations.items():
                self._current_operations.append({
                    "id": op_id,
                    "operation_id": op.operation_id or op_id,
                    "method": op.method.upper(),
                    "path": op.path,
                    "summary": op.summary or "",
                    "description": op.description or "",
                    "parameters": op.parameters,
                })

            self._setup_operations_columns()
            self._populate_operations()
            self.notify(f"Loaded {len(self._current_operations)} operations for {provider}/{api}")
            self.query_one("#catalog_table", DataTable).focus()
        except Exception:
            self.notify(
                f"Specification for '{provider}' is not downloaded yet. Press 'd' to download.",
                severity="warning",
            )
            status_text.update(
                f"[yellow]'{escape(provider)}' not downloaded.[/] Press [bold]d[/] or run [bold]/download {escape(provider)}[/] to sync."
            )

    def action_download_selected(self) -> None:
        if self._is_busy:
            self.notify("A download task is already running...", severity="warning")
            return
        if self.current_view == "operations":
            if self.selected_provider and self.selected_api:
                self._run_single_download(self.selected_provider, self.selected_api)
            return

        table = self.query_one("#catalog_table", DataTable)
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

    def _run_single_download_by_name(self, target: str) -> None:
        if "/" in target:
            provider, api = target.split("/", 1)
        else:
            provider = target
            apis = self.client.discovery.list_apis(provider)
            api = apis[0] if apis else "REST"
        self._run_single_download(provider, api)

    @work(thread=True, exclusive=True)
    def _run_single_download(self, provider: str, api: str) -> None:
        self._is_busy = True
        status_text = self.query_one("#status_text", Static)
        self.call_from_thread(self.set_loading, True)
        self.call_from_thread(
            status_text.update,
            f"[bold cyan]Downloading:[/] Fetching and compiling [bold]{provider}/{api}[/]...",
        )

        res = _download_and_compile(
            client=self.client,
            data_dir=self.data_dir,
            provider=provider,
            api=api,
            force=False,
        )

        status = res.get("status", "unknown")
        if status == "downloaded":
            self.call_from_thread(
                status_text.update,
                f"[bold green]✓ Downloaded {provider}/{api} successfully![/] "
                f"({res.get('operations', 0)} operations compiled)",
            )
            self.notify(f"Successfully downloaded {provider}/{api}", severity="information")
            self.call_from_thread(self._load_data)
            self.call_from_thread(self._populate_catalog)
        elif status == "skipped":
            self.call_from_thread(
                status_text.update,
                f"[yellow]{provider}/{api} is already downloaded.[/]",
            )
            self.notify(f"{provider}/{api} already downloaded", severity="warning")
        else:
            err = res.get("message", "Error")
            self.call_from_thread(
                status_text.update,
                f"[bold red]✗ Failed to download {provider}/{api}:[/] {err}",
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
        self.call_from_thread(self.set_loading, True)

        items_to_sync = [item for item in self._all_items if not item["downloaded"]]
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
                force=False,
            )
            if res.get("status") == "downloaded":
                success_count += 1

        self.call_from_thread(
            status_text.update,
            f"[bold green]Batch download complete![/] {success_count}/{total} specifications downloaded.",
        )
        self.call_from_thread(self.set_loading, False)
        self.notify(f"Batch completed: {success_count}/{total} downloaded")
        self.call_from_thread(self._load_data)
        self.call_from_thread(self._populate_catalog)
        self._is_busy = False
