from __future__ import annotations

from typing import Any

import typer
from mapi.models.domain import Operation

from mapi_cli.completion import complete_api, complete_provider
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.resolution import resolve_service_query
from mapi_cli.ui.console import console
from mapi_cli.ui.tables import build_operations_table

HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def filter_operations(
    operations: list[Operation] | list[dict[str, Any]],
    query: str | None = None,
    method: str | None = None,
) -> list[Any]:
    """Filter operations by HTTP method and/or fuzzy query across fields."""
    allowed_methods = (
        {m.strip().upper() for m in method.split(",") if m.strip()}
        if method
        else None
    )

    q_tokens = query.strip().lower().split() if query and query.strip() else []

    filtered: list[Any] = []
    for op in operations:
        if isinstance(op, Operation):
            op_method = op.method.upper()
        else:
            op_method = str(op.get("method", "GET")).upper()

        if allowed_methods and op_method not in allowed_methods:
            continue

        if q_tokens:
            if isinstance(op, Operation):
                op_id = (op.operation_id or "").lower()
                path = (op.path or "").lower()
                summary = (op.summary or "").lower()
                description = (op.description or "").lower()
            else:
                op_id = str(op.get("operation_id") or "").lower()
                path = str(op.get("path") or "").lower()
                summary = str(op.get("summary") or "").lower()
                description = str(op.get("description") or "").lower()

            matched_all_tokens = True
            for token in q_tokens:
                t_upper = token.upper()
                # If token matches an HTTP method, match either that method or text
                if t_upper in HTTP_METHODS and op_method == t_upper:
                    continue
                if (
                    token in op_id
                    or token in path
                    or token in summary
                    or token in description
                    or token in op_method.lower()
                ):
                    continue
                matched_all_tokens = False
                break

            if not matched_all_tokens:
                continue

        filtered.append(op)
    return filtered


def execute_list_operations(
    c_ctx: CliContext,
    provider: str,
    api: str,
    source: str | None = None,
    query: str | None = None,
    method: str | None = None,
) -> None:
    """Core logic to load, filter, and render operations for a given provider/API."""
    client = c_ctx.client

    if not client.discovery.provider_exists(provider):
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(f"Provider '{provider}' not found.")
    if not client.discovery.api_exists(provider, api):
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(f"API '{api}' not found for provider '{provider}'.")

    from mapi.exceptions import ServiceNotFoundError

    try:
        src = client.discovery._resolve_source(provider, api, source)
        sd = client.discovery._get_service_data(provider, api, src)
        all_ops = []
        for op_name, op in sd.operations.items():
            if not op.operation_id:
                all_ops.append(
                    Operation(
                        service=op.service,
                        path=op.path,
                        method=op.method,
                        operation_id=op_name,
                        summary=op.summary,
                        description=op.description,
                        parameters=op.parameters,
                        deprecated=op.deprecated,
                    )
                )
            else:
                all_ops.append(op)
    except ServiceNotFoundError as e:
        if c_ctx.output == "json":
            emit_output(
                {"error": str(e), "provider": provider, "api": api, "downloaded": False},
                format_type="json",
            )
            return
        console.print(
            f"[bold yellow]Specification for '{provider}/{api}' is not downloaded yet.[/]"
        )
        console.print(
            f"Run [bold cyan]mapi download {provider}[/] to download and compile it locally."
        )
        return

    filtered_ops = filter_operations(all_ops, query=query, method=method)

    if not filtered_ops:
        if c_ctx.output == "json":
            emit_output([], format_type="json")
            return
        filter_desc: list[str] = []
        if method:
            filter_desc.append(f"method='{method.upper()}'")
        if query:
            filter_desc.append(f"query='{query}'")
        f_str = f" matching {', '.join(filter_desc)}" if filter_desc else ""
        console.print(f"[yellow]No operations found{f_str} for {provider}/{api}.[/]")
        return

    serialized = [
        {
            "operation_id": (
                (op.operation_id or "")
                if isinstance(op, Operation)
                else str(op.get("operation_id", ""))
            ),
            "method": (
                op.method
                if isinstance(op, Operation)
                else str(op.get("method", "GET"))
            ),
            "path": (
                op.path
                if isinstance(op, Operation)
                else str(op.get("path", ""))
            ),
            "summary": (
                (op.summary or "")
                if isinstance(op, Operation)
                else str(op.get("summary", ""))
            ),
        }
        for op in filtered_ops
    ]

    table = build_operations_table(provider, api, filtered_ops)
    emit_output(serialized, format_type=c_ctx.output, rich_renderable=table)


def list_operations(
    ctx: typer.Context,
    service: str = typer.Argument(
        ...,
        help="Provider / Service name (e.g. discord, pokeapi)",
        autocompletion=complete_provider,
    ),
    api_or_query: str | None = typer.Argument(
        None,
        help="API name (e.g. REST), or search filter / method (e.g. post, get)",
        autocompletion=complete_api,
    ),
    query: str | None = typer.Argument(
        None,
        help="Search filter or method query (e.g. post, message)",
    ),
    source: str | None = typer.Option(None, "--source", "-s", help="Specific spec source"),
    filter_text: str | None = typer.Option(
        None, "--filter", "-f", help="Filter by operation ID, path, summary, or method"
    ),
    method: str | None = typer.Option(
        None, "--method", "-m", help="Filter by HTTP method (e.g. GET, POST, PUT, DELETE, PATCH)"
    ),
) -> None:
    """List operations available for a given provider and API with optional filtering."""
    if service in ("help", "--help", "-h"):
        typer.echo(ctx.get_help())
        raise typer.Exit()

    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    provider, resolved_api, pos_query = resolve_service_query(
        client.discovery, service, api_or_query, query
    )

    if not resolved_api:
        apis = client.discovery.list_apis(provider)
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(
            f"Provider '{provider}' has multiple APIs: {', '.join(apis)}. Please specify an API name."
        )

    combined_query = " ".join(filter(None, [pos_query, filter_text])).strip() or None

    execute_list_operations(
        c_ctx=c_ctx,
        provider=provider,
        api=resolved_api,
        source=source,
        query=combined_query,
        method=method,
    )
