from __future__ import annotations

from typing import Any

from mapi.models.domain import Operation
from rich import box
from rich.table import Table

from mapi_cli.ui.theme import method_style


def build_providers_table(provider_data: list[dict[str, Any]]) -> Table:
    """Build a rich table for listing API providers with download status."""
    table = Table(
        title="Available Providers",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Provider", style="provider", no_wrap=True)
    table.add_column("APIs", style="cyan")
    table.add_column("Operations", justify="right", style="green")
    table.add_column("Status", justify="center")

    for item in provider_data:
        raw_status = str(item.get("status", "Not Downloaded"))
        if raw_status == "Downloaded":
            status_badge = "[bold green]Downloaded[/]"
        elif raw_status == "Not Downloaded":
            status_badge = "[dim yellow]Not Downloaded[/]"
        else:
            status_badge = f"[cyan]{raw_status}[/]"

        table.add_row(
            item["provider"],
            ", ".join(item.get("apis", [])),
            str(item.get("operations", 0)),
            status_badge,
        )
    return table


def build_apis_table(provider: str, api_data: list[dict[str, Any]]) -> Table:
    """Build a rich table for listing APIs within a provider."""
    table = Table(
        title=f"APIs for '{provider}'",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("API", style="api", no_wrap=True)
    table.add_column("Sources", style="dim")
    table.add_column("Operations", justify="right", style="green")
    table.add_column("Primary Auth", style="yellow")

    for item in api_data:
        table.add_row(
            item["api"],
            ", ".join(item.get("sources", [])),
            str(item.get("operation_count", 0)),
            item.get("primary_auth", "none"),
        )
    return table


def build_operations_table(
    provider: str, api: str, operations: list[Operation] | list[dict[str, Any]]
) -> Table:
    """Build a rich table for operations with colorized HTTP method badges."""
    table = Table(
        title=f"Operations for {provider}/{api}",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("Method", justify="center", no_wrap=True)
    table.add_column("Operation ID", style="op", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Summary", style="dim")

    for op in operations:
        if isinstance(op, Operation):
            method = op.method.upper()
            op_id = op.operation_id or ""
            path = op.path
            summary = op.summary or ""
        else:
            method = op.get("method", "GET").upper()
            op_id = op.get("operation_id", "")
            path = op.get("path", "")
            summary = op.get("summary", "")

        style = method_style(method)
        table.add_row(
            f"[{style}]{method}[/]",
            op_id,
            path,
            summary[:60] + "..." if len(summary) > 60 else summary,
        )
    return table
