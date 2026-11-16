from __future__ import annotations

import typer

from mapi_cli.commands.ops import execute_list_operations
from mapi_cli.commands.providers import execute_list_providers
from mapi_cli.completion import complete_api, complete_provider
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.resolution import resolve_service_query
from mapi_cli.ui.tables import build_apis_table


def list_apis(
    ctx: typer.Context,
    service: str | None = typer.Argument(
        None,
        help="Service / Provider name (e.g. discord, pokeapi, stripe). Omit to list all available providers.",
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
    """List all available providers, or inspect APIs and operations for a specific service.

    Examples:
        mapi apis                     # List all providers and their download status
        mapi apis discord             # List all operations for discord
        mapi apis discord post        # List operations for discord matching 'post'
        mapi apis discord -m post     # List only POST operations for discord
        mapi apis pokeapi REST        # List operations for pokeapi/REST
    """
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    # 1. No service argument -> List all providers (the "providers list")
    if service is None or service.strip() == "":
        execute_list_providers(ctx)
        return

    if service in ("help", "--help", "-h"):
        typer.echo(ctx.get_help())
        raise typer.Exit()

    # 2. Resolve service, API, and query
    provider, resolved_api, pos_query = resolve_service_query(
        client.discovery, service, api_or_query, query
    )

    combined_query = " ".join(filter(None, [pos_query, filter_text])).strip() or None

    # If provider has multiple APIs and user didn't specify one: list APIs
    if not resolved_api:
        apis = client.discovery.list_apis(provider)
        api_data = []
        for a in apis:
            try:
                info = client.discovery.get_api_info(provider, a)
                api_data.append(
                    {
                        "api": a,
                        "sources": info.sources,
                        "operation_count": info.operation_count,
                        "primary_auth": info.primary_auth,
                    }
                )
            except Exception:
                api_data.append(
                    {
                        "api": a,
                        "sources": [],
                        "operation_count": 0,
                        "primary_auth": "none",
                    }
                )
        table = build_apis_table(provider, api_data)
        emit_output(api_data, format_type=c_ctx.output, rich_renderable=table)
        if c_ctx.output == "auto":
            from mapi_cli.ui.console import console

            console.print(
                f"[dim]Tip: Run 'mapi apis {provider} <api>' to inspect operations.[/]"
            )
        return

    # Provider has a resolved API -> Directly list operations!
    execute_list_operations(
        c_ctx=c_ctx,
        provider=provider,
        api=resolved_api,
        source=source,
        query=combined_query,
        method=method,
    )
