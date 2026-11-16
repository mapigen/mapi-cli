from __future__ import annotations

from typing import Any

from mapi.models.domain import Operation, Parameter, ParameterRef
from mapi.models.request import RequestConfig
from rich import box
from rich.panel import Panel
from rich.table import Table

from mapi_cli.ui.theme import method_style


def build_describe_panel(
    provider: str,
    api: str,
    op: Operation,
    servers: list[str] | None = None,
    resolved_parameters: list[Any] | None = None,
) -> Panel:
    """Build a detailed description card for an operation."""
    m_style = method_style(op.method)
    header = f"[{m_style}]{op.method.upper()}[/] [bold white]{op.path}[/]"

    content: list[str] = [
        f"[bold]Operation ID:[/] [op]{op.operation_id}[/]",
        f"[bold]Summary:[/] {op.summary or 'No summary'}",
    ]
    if op.description:
        content.append(f"[bold]Description:[/] {op.description}")

    if servers:
        content.append(f"[bold]Servers:[/] {', '.join(servers)}")

    # Parameters table
    param_table = Table(
        title="Parameters",
        box=box.SIMPLE,
        header_style="bold yellow",
        show_edge=False,
    )
    param_table.add_column("Name", style="param.name")
    param_table.add_column("Location", style="param.type")
    param_table.add_column("Required", style="param.required")
    param_table.add_column("Description", style="dim")

    params_to_display = resolved_parameters if resolved_parameters is not None else op.parameters
    example_args = []
    for p in params_to_display:
        if isinstance(p, Parameter):
            req_str = "[bold red]Yes[/]" if p.required else "No"
            desc = p.description or ""
            param_table.add_row(p.name, p.in_, req_str, desc)
            if p.required:
                example_args.append(f"{p.name}=<val>")
        elif isinstance(p, ParameterRef):
            ref_name = p.component_name
            param_table.add_row(f"${ref_name}", "ref", "-", f"Ref: {p.ref}")

    op_name = op.operation_id or "operation"
    example_call = f"mapi call {provider} {api} {op_name} {' '.join(example_args)}"
    content.append(f"\n[bold green]Example Call:[/] [dim]{example_call}[/]")

    return Panel(
        param_table,
        title=header,
        subtitle=f"[dim]Provider: {provider} | API: {api}[/]",
        box=box.ROUNDED,
    )


def build_dry_run_panel(config: RequestConfig) -> Panel:
    """Build a panel displaying dry-run request configuration without execution."""
    m_style = method_style(config.method)
    lines = [
        f"[bold]Method:[/] [{m_style}]{config.method.upper()}[/]",
        f"[bold]URL:[/] [cyan]{config.url}[/]",
    ]

    if config.params:
        lines.append(f"[bold]Query Parameters:[/] {config.params}")

    if config.headers:
        lines.append("[bold]Headers:[/]")
        for k, v in config.headers.items():
            lines.append(f"  [kv.key]{k}[/]: [kv.val]{v}[/]")

    if config.json_body is not None:
        lines.append(f"[bold]JSON Body:[/] {config.json_body}")

    curl_cmd = config.to_curl()
    lines.append(f"\n[bold green]cURL Representation:[/] [dim]{curl_cmd}[/]")

    return Panel(
        "\n".join(lines),
        title="[bold magenta]DRY RUN (No request dispatched)[/]",
        box=box.ROUNDED,
    )
