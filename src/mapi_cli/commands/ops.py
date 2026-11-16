from __future__ import annotations

import typer

from mapi_cli.completion import complete_api, complete_provider
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.resolution import resolve_provider_and_api
from mapi_cli.ui.tables import build_operations_table


def list_operations(
    ctx: typer.Context,
    provider: str = typer.Argument(..., help="Provider name", autocompletion=complete_provider),
    api: str = typer.Argument(..., help="API name", autocompletion=complete_api),
    source: str | None = typer.Option(None, "--source", "-s", help="Specific spec source"),
    filter_text: str | None = typer.Option(
        None, "--filter", "-f", help="Filter by operation name or path"
    ),
) -> None:
    """List operations available for a given provider and API."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    provider, api = resolve_provider_and_api(client.discovery, provider, api)

    if not client.discovery.provider_exists(provider):
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(f"Provider '{provider}' not found.")
    if not client.discovery.api_exists(provider, api):
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(f"API '{api}' not found for provider '{provider}'.")

    op_names = client.discovery.list_operations(provider, api, source=source)
    operations = []
    for name in op_names:
        if filter_text and filter_text.lower() not in name.lower():
            continue
        try:
            op = client.discovery.get_operation(provider, api, name, source=source)
            operations.append(
                {
                    "operation_id": op.operation_id or name,
                    "method": op.method,
                    "path": op.path,
                    "summary": op.summary,
                }
            )
        except Exception:
            operations.append({"operation_id": name, "method": "GET", "path": "", "summary": ""})

    table = build_operations_table(provider, api, operations)

    # For JSON serialization
    serialized = [
        {
            "operation_id": op.operation_id
            if hasattr(op, "operation_id")
            else op.get("operation_id"),
            "method": op.method if hasattr(op, "method") else op.get("method"),
            "path": op.path if hasattr(op, "path") else op.get("path"),
            "summary": op.summary if hasattr(op, "summary") else op.get("summary"),
        }
        for op in operations
    ]

    emit_output(serialized, format_type=c_ctx.output, rich_renderable=table)
