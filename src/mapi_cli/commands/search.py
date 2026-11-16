from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from mapi_cli.context import CliContext
from mapi_cli.output import emit_output


def search_all(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search term across providers, APIs, and operations"),
) -> None:
    """Fuzzy search across all registered providers, APIs, and operations."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client
    q = query.lower()

    matches = []
    for prov in client.discovery.list_providers():
        if q in prov.lower():
            matches.append({"type": "provider", "provider": prov, "api": "-", "operation": "-"})

        for api in client.discovery.list_apis(prov):
            if q in api.lower():
                matches.append({"type": "api", "provider": prov, "api": api, "operation": "-"})

            try:
                for op in client.discovery.list_operations(prov, api):
                    if q in op.lower():
                        matches.append(
                            {"type": "operation", "provider": prov, "api": api, "operation": op}
                        )
            except Exception:
                pass

    table = Table(
        title=f"Search Results for '{query}'",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("Type", style="bold yellow")
    table.add_column("Provider", style="provider")
    table.add_column("API", style="api")
    table.add_column("Operation", style="op")

    for m in matches:
        table.add_row(m["type"], m["provider"], m["api"], m["operation"])

    emit_output(matches, format_type=c_ctx.output, rich_renderable=table)
