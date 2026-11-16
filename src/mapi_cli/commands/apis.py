from __future__ import annotations

import typer

from mapi_cli.completion import complete_provider
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.ui.tables import build_apis_table


def list_apis(
    ctx: typer.Context,
    provider: str = typer.Argument(
        ..., help="Provider name (e.g. pokeapi, github)", autocompletion=complete_provider
    ),
) -> None:
    """List all APIs available for a given provider."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    if not client.discovery.provider_exists(provider):
        from mapi.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError(f"Provider '{provider}' not found.")

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
