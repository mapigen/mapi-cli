from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.markup import escape
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
    LoadingIndicator,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from mapi_cli.commands.download import _download_and_compile, _is_api_local
from mapi_cli.paths import resolve_data_dir
from mapi_cli.ui.banner import render_banner
from mapi_cli.ui.command_palette import filter_commands
from mapi_cli.ui.styles import CELADON_DARK, CELADON_LIGHT, build_app_tcss, method_style


class MapiTUIApp(App[None]):
    """Default interactive Command Center & Exploration TUI for MAPI.

    Features:
        - '/' based intelligent command search with live auto-complete
        - Celadon Green light & dark mode themes (toggle with 't')
        - MAPI ASCII text art header
        - Interactive provider & API exploration
        - Seamless spec downloads
    """

    TITLE = "MAPI"
    SUB_TITLE = "Type '/' for commands • Arrow keys to navigate • Enter to inspect/download • t: theme"
    CSS = build_app_tcss()

    BINDINGS = [
        Binding("enter", "select_row", "Select / Inspect"),
        Binding("slash", "focus_command_palette", "Commands / Search", key_display="/"),
        Binding("t", "toggle_theme", "Toggle Celadon Theme"),
        Binding("d", "download_selected", "Download"),
        Binding("a", "download_all", "Download All"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("escape", "escape_action", "Back / Clear"),
        Binding("backspace", "back_action", "Back to Catalog", show=False),
        Binding("b", "back_action", "Back to Catalog", show=False),
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
        self.current_view: str = "providers"  # "providers" or "operations"
        self.selected_provider: str | None = None
        self.selected_api: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="header_container"):
            yield Static(render_banner(self.is_dark), id="banner_static")
            yield Input(
                placeholder="Type '/' for intelligent commands (e.g. /apis, /download, /theme) or type to filter...",
                id="command_input",
            )
            with Vertical(id="suggestions_container"):
                yield OptionList(id="suggestions_list")
        with Vertical(id="table_container"):
            yield DataTable(id="catalog_table", cursor_type="row")
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
                    is_local = _is_api_local(self.data_dir, p, source, a)
                except Exception:
                    source = "github"
                    spec_url = ""
                    ops_count = 0
                    auth_type = "none"
                    is_local = False

                self._all_items.append(
                    {
                        "provider": p,
                        "api": a,
                        "source": source,
                        "spec_url": spec_url,
                        "operations": ops_count,
                        "auth": auth_type,
                        "downloaded": is_local,
                    }
                )

    def _populate_catalog(self, query: str = "") -> None:
        table = self.query_one("#catalog_table", DataTable)
        table.clear()

        q = query.strip().lower()
        if q.startswith("/"):
            # When typing a slash command, do not filter table out
            q = ""

        for item in self._all_items:
            p = item["provider"]
            a = item["api"]
            url = item["spec_url"]
            ops = str(item["operations"])
            auth = item["auth"]
            is_dl = item["downloaded"]

            if q and (q not in p.lower() and q not in a.lower() and q not in url.lower()):
                continue

            pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
            row_key = f"{p}/{a}"
            status_style = "bold green" if is_dl else f"dim {pal.text_muted}"
            status_str = "Downloaded" if is_dl else "Not Downloaded"

            table.add_row(
                Text(p, style=f"bold {pal.secondary}"),
                Text(a, style=pal.text),
                Text(status_str, style=status_style),
                Text(ops, style=pal.primary),
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

        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
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

            table.add_row(
                Text(m, style=method_style(m)),
                Text(op_name, style=pal.text),
                Text(path, style=pal.text_muted),
                Text(summary, style=f"italic {pal.text_muted}"),
                key=op_id,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "command_input":
            val = event.value
            self._update_suggestions(val)
            if not val.startswith("/"):
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
                    line.append(f"{cmd.command:<14}", style=f"bold {pal.primary}")
                    line.append(f"{cmd.title:<24}", style=f"bold {pal.secondary}")
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
            self.action_back_to_catalog()
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
        elif root_cmd in ("/help", "/?"):
            self.notify(
                "Commands: /apis, /ops, /download, /search, /theme, /refresh, /quit\n"
                "Shortcuts: / (commands), d (download), a (all), t (theme), b/Esc (back), q (quit)",
                title="MAPI Help",
                timeout=8,
            )
        else:
            self.notify(f"Unknown command '{cmd_str}'. Type '/' for list of commands.", severity="warning")

        self.query_one("#catalog_table", DataTable).focus()

    def action_focus_command_palette(self) -> None:
        input_widget = self.query_one("#command_input", Input)
        input_widget.value = "/"
        input_widget.focus()
        input_widget.cursor_position = 1

    def action_back_to_catalog(self) -> None:
        self.current_view = "providers"
        self.selected_provider = None
        self.selected_api = None
        input_widget = self.query_one("#command_input", Input)
        input_widget.value = ""
        self._setup_catalog_columns()
        self._populate_catalog()
        status_text = self.query_one("#status_text", Static)
        status_text.update(
            "[dim]Ready. Press [bold]Enter[/] to inspect operations, [bold]d[/] to download, or [bold]/[/] for commands.[/]"
        )
        self.query_one("#catalog_table", DataTable).focus()
        self.notify("Returned to Providers & APIs catalog")

    def action_back_action(self) -> None:
        if self.current_view == "operations":
            self.action_back_to_catalog()

    def action_escape_action(self) -> None:
        container = self.query_one("#suggestions_container", Vertical)
        if container.styles.display == "block":
            container.styles.display = "none"
            self.query_one("#catalog_table", DataTable).focus()
            return

        input_widget = self.query_one("#command_input", Input)
        if input_widget.value:
            input_widget.value = ""
            if self.current_view == "operations":
                self._populate_operations()
            else:
                self._populate_catalog()
            self.query_one("#catalog_table", DataTable).focus()
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
        else:
            self._populate_catalog()
        mode_name = "Celadon Dark" if self.is_dark else "Celadon Light"
        self.notify(f"Theme switched to {mode_name}")

    def action_refresh_data(self) -> None:
        self._load_data()
        if self.current_view == "operations" and self.selected_provider:
            self._show_operations_for(self.selected_provider, self.selected_api)
        else:
            self._populate_catalog()
        self.notify("Registry and local specifications reloaded")

    def action_select_row(self) -> None:
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
        else:
            self._inspect_operation_by_id(key_str)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key_str = str(getattr(event.row_key, "value", event.row_key))
        if self.current_view == "providers":
            if "/" in key_str:
                provider, api = key_str.split("/", 1)
                self._show_operations_for(provider, api)
        else:
            self._inspect_operation_by_id(key_str)

    def action_inspect_operation(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        if table.row_count == 0:
            return
        coordinate = table.cursor_coordinate
        row_key_obj = table.coordinate_to_cell_key(coordinate).row_key
        if not row_key_obj:
            return
        key_str = str(getattr(row_key_obj, "value", row_key_obj))
        self._inspect_operation_by_id(key_str)

    def _inspect_operation_by_id(self, op_id: str) -> None:
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
        self.notify(
            f"{m} {path}\nOp: {op_name}\nParams: {params_display}\n{summary}",
            title=f"Operation: {op_name}",
            timeout=6,
        )

    def _show_operations_for(self, provider: str, api: str | None = None) -> None:
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

            pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
            status_text.update(
                f"[bold {pal.secondary}]{escape(provider)}/{escape(api or '')}:[/] Displaying {len(self._current_operations)} operations. "
                f"Press [bold {pal.primary}]Enter[/] to inspect, [bold {pal.primary}]Esc[/] or [bold {pal.primary}]b[/] to go back, or type to filter."
            )
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
