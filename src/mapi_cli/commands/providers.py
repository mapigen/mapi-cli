from __future__ import annotations

import typer

from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.ui.tables import build_providers_table


def list_providers(ctx: typer.Context) -> None:
    """List all available API providers."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    providers = client.discovery.list_providers()
    table_data = []
    for p in providers:
        apis = client.discovery.list_apis(p)
        total_ops = 0
        for a in apis:
            try:
                info = client.discovery.get_api_info(p, a)
                total_ops += info.operation_count
            except Exception:
                pass
        table_data.append({"provider": p, "apis": apis, "operations": total_ops})

    table = build_providers_table(table_data)
    emit_output(table_data, format_type=c_ctx.output, rich_renderable=table)
