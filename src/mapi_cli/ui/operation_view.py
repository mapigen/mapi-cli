from __future__ import annotations

import json
import re
from typing import Any

from mapi.models.request import RequestConfig
from mapi.models.response import MapiResult
from rich.json import JSON
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label, Static

from mapi_cli.operations import (
    OperationParamDetail,
    OperationRequirementCheck,
    _parse_typed_value,
)
from mapi_cli.ui.styles.palette import CELADON_DARK, CELADON_LIGHT, CeladonPalette


def safe_markup(text: object) -> str:
    """Safely escape literal text for insertion into Rich / Textual markup strings.

    Guarantees no square brackets can corrupt the markup tag stack.
    """
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\")
    return s.replace("[", "\\[")


def make_param_input_id(param_name: str, index: int = 0) -> str:
    """Create a valid Textual DOM identifier matching ^[a-zA-Z_][a-zA-Z0-9_-]*$.

    If param_name is already a valid identifier (e.g. 'id', 'user_id'), returns
    'op_input_{param_name}' to maintain selector compatibility.
    Otherwise replaces invalid characters (such as '[', ']', '.', '$') with underscores
    and prefixes with index to ensure uniqueness and validity.
    """
    if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_-]*", param_name):
        return f"op_input_{param_name}"
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", param_name).strip("_")
    return f"op_input_{index}_{clean}" if clean else f"op_input_{index}"


def get_http_method_color(method: str) -> str:
    """Return standard rich color for HTTP methods."""
    m = method.upper()
    colors = {
        "GET": "green",
        "POST": "blue",
        "PUT": "yellow",
        "DELETE": "red",
        "PATCH": "magenta",
        "HEAD": "cyan",
        "OPTIONS": "cyan",
    }
    return colors.get(m, "white")


class OperationRunnerPage(VerticalScroll):
    """Interactive full-page view for inspecting and executing an API operation.

    Features:
        - Operation Header: Method badge, path, operation ID, summary, and description
        - Auth status badge & preconfigured token detection
        - Form inputs for all OpenAPI parameters with type validation & required flags
        - Optional Auth override and JSON Request Body inputs
        - Action Buttons: Run Request, Dry-Run, cURL, and Back to Operations
        - Live Response & Result Viewer with status codes, latency, headers, and formatted JSON
    """

    DEFAULT_CSS = """
    OperationRunnerPage {
        height: 1fr;
        padding: 0 1;
        background: transparent;
    }
    """

    class RunRequested(Message):
        """Dispatched when the user clicks Run, Dry-Run, or cURL."""

        def __init__(
            self,
            chk: OperationRequirementCheck,
            kwargs: dict[str, Any],
            dry_run: bool = False,
            emit_curl: bool = False,
        ) -> None:
            super().__init__()
            self.chk = chk
            self.kwargs = kwargs
            self.dry_run = dry_run
            self.emit_curl = emit_curl

    class BackRequested(Message):
        """Dispatched when the user clicks the Back button."""

    def __init__(
        self,
        chk: OperationRequirementCheck,
        is_dark: bool = True,
        initial_kwargs: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(id="operation_runner_page")
        self.chk = chk
        self.is_dark = is_dark
        self.initial_kwargs = initial_kwargs or {}
        self._param_index_map: dict[int, int] = {
            id(p): idx for idx, p in enumerate(self.chk.parameters)
        }

    def compose(self) -> ComposeResult:
        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT

        # 1. Operation Header Panel
        with Vertical(id="op_header_card", classes="op-card"):
            yield Static(self._build_header_text(pal), id="op_header_static")

        # 2. Parameters & Request Inputs Form
        with Vertical(id="op_form_card", classes="op-card"):
            yield Static(
                f"[bold {pal.primary}]Parameters & Request Inputs[/] "
                f"[dim]({len(self.chk.parameters)} parameters declared)[/]",
                classes="op-section-title",
            )

            # Required parameters
            if self.chk.required_parameters:
                yield Static(
                    f"[bold red]Required Parameters ({len(self.chk.required_parameters)}):[/]",
                    classes="op-group-title",
                )
                for p in self.chk.required_parameters:
                    yield from self._compose_param_row(p, pal, is_required=True)

            # Optional parameters
            if self.chk.optional_parameters:
                yield Static(
                    f"[bold {pal.secondary}]Optional Parameters ({len(self.chk.optional_parameters)}):[/]",
                    classes="op-group-title",
                )
                for p in self.chk.optional_parameters:
                    yield from self._compose_param_row(p, pal, is_required=False)

            if not self.chk.parameters:
                yield Static(
                    "[dim italic]No URL, path, or query parameters required for this operation.[/]",
                    classes="op-param-desc",
                )

            # Authentication Token Input (if required)
            if self.chk.auth.is_required:
                yield Static(
                    f"[bold {pal.secondary}]Authentication ({safe_markup(self.chk.auth.primary_auth)}):[/]",
                    classes="op-group-title",
                )
                status_badge = "[CONFIGURED]" if self.chk.auth.is_configured else "[REQUIRED]"
                status_color = "green" if self.chk.auth.is_configured else "yellow"
                yield Static(
                    f"[{status_color}]{safe_markup(status_badge)} {safe_markup(self.chk.auth.message)}[/] • "
                    f"Env var: [cyan]{safe_markup(self.chk.auth.env_var_name)}[/]",
                    classes="op-param-desc",
                )
                init_tok = str(self.initial_kwargs.get("token", ""))
                yield Input(
                    placeholder="Enter auth token to override...",
                    value=init_tok,
                    password=True,
                    id="op_input__token",
                    classes="op-param-input",
                )

            # Request Body input (if POST / PUT / PATCH or body param exists)
            needs_body = (
                self.chk.method.upper() in ("POST", "PUT", "PATCH")
                or any(p.in_ == "body" for p in self.chk.parameters)
            )
            if needs_body:
                yield Static(
                    f"[bold {pal.secondary}]Request Body (JSON):[/]",
                    classes="op-group-title",
                )
                yield Static(
                    "[dim]Pass JSON payload dictionary or raw payload object[/]",
                    classes="op-param-desc",
                )
                init_body = ""
                if "json_body" in self.initial_kwargs:
                    init_body = json.dumps(self.initial_kwargs["json_body"])
                elif "data" in self.initial_kwargs:
                    init_body = json.dumps(self.initial_kwargs["data"])
                yield Input(
                    placeholder='{"key": "value"} or raw JSON string...',
                    value=init_body,
                    id="op_input__body",
                    classes="op-param-input",
                )

        # 3. Action Buttons Bar
        with Horizontal(id="op_button_bar"):
            yield Button("Run Request", id="btn_run", variant="success")
            yield Button("Dry Run", id="btn_dry", variant="primary")
            yield Button("cURL", id="btn_curl", variant="default")
            yield Button("Back to Operations", id="btn_back", variant="default")

        # 4. Live Result / Response Viewer
        with Vertical(id="op_result_card", classes="op-card"):
            yield Static(
                f"[bold {pal.primary}]Response & Output[/]",
                classes="op-section-title",
            )
            yield Static(
                "[dim]Ready. Fill in inputs above and press [bold]Run Request[/], [bold]Dry Run[/], or [bold]cURL[/].[/]",
                id="op_result_header",
            )
            yield Static("", id="op_result_body")

    def _compose_param_row(
        self,
        p: OperationParamDetail,
        pal: CeladonPalette,
        is_required: bool,
    ) -> ComposeResult:
        """Compose label and input for a single parameter."""
        req_marker = "[bold red]*[/]" if is_required else "[dim](opt)[/]"
        in_color = "cyan" if p.in_ == "path" else "yellow"
        in_escaped = safe_markup(f"[{p.in_}]")
        label_text = (
            f"[bold {pal.text}]{safe_markup(p.name)}[/] {req_marker} "
            f"[{in_color}]{in_escaped}[/] "
            f"[dim]({safe_markup(p.type_str)})[/]"
        )
        if p.description:
            label_text += f" • [italic dim]{safe_markup(p.description)}[/]"

        yield Label(label_text, classes="op-param-label")

        init_val = ""
        if p.name in self.initial_kwargs:
            init_val = str(self.initial_kwargs[p.name])
        elif p.default is not None:
            init_val = str(p.default)

        canonical_idx = self._param_index_map.get(id(p), 0)
        input_id = make_param_input_id(p.name, index=canonical_idx)
        yield Input(
            placeholder=f"Enter {p.name} ({p.type_str})...",
            value=init_val,
            id=input_id,
            name=p.name,
            classes="op-param-input",
        )

    def _build_header_text(self, pal: CeladonPalette) -> str:
        chk = self.chk
        m = chk.method.upper()
        m_color = get_http_method_color(m)

        summary_line = f"[italic {pal.text}]{safe_markup(chk.summary)}[/]" if chk.summary else ""
        desc_line = (
            f"[dim {pal.text_muted}]{safe_markup(chk.description)}[/]"
            if chk.description and chk.description != chk.summary
            else ""
        )

        auth_line = (
            f"[bold green]Auth:[/] [green]{safe_markup(chk.auth.message)}[/]"
            if chk.auth.is_configured
            else (
                f"[bold yellow]Auth:[/] [yellow]{safe_markup(chk.auth.message)}[/]"
                if chk.auth.is_required
                else "[dim]Public Endpoint • No authentication required[/]"
            )
        )

        tier_styles = {
            "Cached": f"bold {pal.secondary}",
            "Compressed": f"bold {pal.primary}",
            "Downloaded": "bold green",
            "Not Downloaded": f"dim {pal.text_muted}",
        }
        tier_style = tier_styles.get(chk.storage_tier, f"dim {pal.text_muted}")
        tier_badge = f"[dim]Tier:[/] [{tier_style}]{safe_markup(chk.storage_tier)}[/]"

        parts = [
            f"[dim]Back: Ctrl+Left / Esc[/]  •  [dim]API:[/] [bold {pal.secondary}]{safe_markup(chk.provider)}/{safe_markup(chk.api)}[/]  •  {tier_badge}",
            f"[bold {m_color}]{safe_markup(m)}[/]  [bold {pal.text}]{safe_markup(chk.operation_id)}[/]  [dim {pal.text_muted}]{safe_markup(chk.path)}[/]",
            auth_line,
        ]
        if summary_line:
            parts.append(summary_line)
        if desc_line:
            parts.append(desc_line)

        return "\n".join(parts)

    def set_theme(self, is_dark: bool) -> None:
        """Update palette styles when theme is toggled."""
        self.is_dark = is_dark
        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        try:
            header = self.query_one("#op_header_static", Static)
            header.update(self._build_header_text(pal))
        except Exception:
            pass

    def get_collected_inputs(self) -> dict[str, Any]:
        """Collect and type-cast parameter inputs from the form."""
        kwargs: dict[str, Any] = {}

        for idx, p in enumerate(self.chk.parameters):
            canonical_idx = self._param_index_map.get(id(p), idx)
            input_id = make_param_input_id(p.name, index=canonical_idx)
            raw_val = ""
            try:
                inp = self.query_one(f"#{input_id}", Input)
                raw_val = inp.value.strip()
            except Exception:
                # Fallback: search by input widget name attribute
                try:
                    for candidate in self.query(Input):
                        if candidate.name == p.name:
                            raw_val = candidate.value.strip()
                            break
                except Exception:
                    pass

            if raw_val:
                kwargs[p.name] = _parse_typed_value(raw_val, p.type_str)

        if self.chk.auth.is_required:
            try:
                tok_inp = self.query_one("#op_input__token", Input)
                tok_val = tok_inp.value.strip()
                if tok_val:
                    kwargs["token"] = tok_val
            except Exception:
                pass

        try:
            body_inp = self.query_one("#op_input__body", Input)
            body_val = body_inp.value.strip()
            if body_val:
                try:
                    kwargs["json_body"] = json.loads(body_val)
                except Exception:
                    kwargs["json_body"] = body_val
        except Exception:
            pass

        return kwargs

        if self.chk.auth.is_required:
            try:
                tok_inp = self.query_one("#op_input__token", Input)
                tok_val = tok_inp.value.strip()
                if tok_val:
                    kwargs["token"] = tok_val
            except Exception:
                pass

        try:
            body_inp = self.query_one("#op_input__body", Input)
            body_val = body_inp.value.strip()
            if body_val:
                try:
                    kwargs["json_body"] = json.loads(body_val)
                except Exception:
                    kwargs["json_body"] = body_val
        except Exception:
            pass

        return kwargs

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_run":
            self.post_message(
                self.RunRequested(
                    chk=self.chk,
                    kwargs=self.get_collected_inputs(),
                    dry_run=False,
                    emit_curl=False,
                )
            )
        elif btn_id == "btn_dry":
            self.post_message(
                self.RunRequested(
                    chk=self.chk,
                    kwargs=self.get_collected_inputs(),
                    dry_run=True,
                    emit_curl=False,
                )
            )
        elif btn_id == "btn_curl":
            self.post_message(
                self.RunRequested(
                    chk=self.chk,
                    kwargs=self.get_collected_inputs(),
                    dry_run=False,
                    emit_curl=True,
                )
            )
        elif btn_id == "btn_back":
            self.post_message(self.BackRequested())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Pressing Enter in an input field triggers execution."""
        self.post_message(
            self.RunRequested(
                chk=self.chk,
                kwargs=self.get_collected_inputs(),
                dry_run=False,
                emit_curl=False,
            )
        )

    def set_executing(self, action_name: str = "Executing request...") -> None:
        header = self.query_one("#op_result_header", Static)
        header.update(f"[bold cyan]{safe_markup(action_name)}[/]")
        body = self.query_one("#op_result_body", Static)
        body.update("")

    def display_result(
        self,
        res: Any,
        call_target: str,
        duration_ms: float | None = None,
        is_curl: bool = False,
    ) -> None:
        pal = CELADON_DARK if self.is_dark else CELADON_LIGHT
        header = self.query_one("#op_result_header", Static)
        body = self.query_one("#op_result_body", Static)

        if isinstance(res, RequestConfig):
            curl_cmd = res.to_curl()
            if is_curl or "curl" in call_target.lower():
                header.update(
                    f"[bold green]cURL Command Generated[/] • [dim]{safe_markup(call_target)}[/]"
                )
                body.update(f"[bold green]cURL Command:[/] {safe_markup(curl_cmd)}")
            else:
                header.update(
                    f"[bold green]Dry-Run Prepared[/] • "
                    f"Method: [bold {pal.secondary}]{safe_markup(res.method)}[/] • "
                    f"URL: [dim]{safe_markup(res.url)}[/]"
                )
                details = [
                    f"[bold]Method:[/] {safe_markup(res.method)}",
                    f"[bold]URL:[/] {safe_markup(res.url)}",
                ]
                if res.headers:
                    details.append(f"[bold]Headers:[/] {safe_markup(json.dumps(res.headers, indent=2))}")
                if res.params:
                    details.append(f"[bold]Query Params:[/] {safe_markup(json.dumps(res.params, indent=2))}")
                if res.json_body is not None:
                    details.append(f"[bold]JSON Body:[/] {safe_markup(json.dumps(res.json_body, indent=2))}")
                details.append(f"\n[bold green]cURL:[/] {safe_markup(curl_cmd)}")
                body.update("\n".join(details))
        elif isinstance(res, MapiResult):
            status_code = getattr(res.metadata, "http_status", 200) or 200
            dur = duration_ms if duration_ms is not None else getattr(res.metadata, "duration_ms", 0)
            status_color = "green" if status_code < 400 else "red"
            header.update(
                f"[bold {status_color}]{status_code} OK[/] • "
                f"Latency: [cyan]{dur}ms[/] • "
                f"Target: [bold {pal.secondary}]{safe_markup(call_target)}[/]"
            )
            if isinstance(res.data, (dict, list)):
                body.update(JSON.from_data(res.data, indent=2))
            else:
                body.update(safe_markup(str(res.data)))
        else:
            header.update(
                f"[bold green]Result[/] • Target: [bold {pal.secondary}]{safe_markup(call_target)}[/]"
            )
            body.update(safe_markup(str(res)))

    def display_error(self, error_msg: str, call_target: str) -> None:
        header = self.query_one("#op_result_header", Static)
        header.update(f"[bold red]Request Failed[/] • Target: [bold]{safe_markup(call_target)}[/]")
        body = self.query_one("#op_result_body", Static)
        body.update(f"[red]{safe_markup(error_msg)}[/]")
