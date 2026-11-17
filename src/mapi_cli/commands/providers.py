from __future__ import annotations

import typer

from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.storage import get_api_storage_tier
from mapi_cli.ui.tables import build_providers_table


def execute_list_providers(ctx: typer.Context) -> None:
    """List all available API providers with download status."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client
    data_dir = c_ctx.data_dir

    providers = client.discovery.list_providers()
    table_data = []
    for p in providers:
        apis = client.discovery.list_apis(p)
        total_ops = 0
        tiers = []
        for a in apis:
            try:
                info = client.discovery.get_api_info(p, a)
                total_ops += info.operation_count
                tier = get_api_storage_tier(client, data_dir, p, a)
                tiers.append(tier)
            except Exception:
                pass

        if not apis:
            status = "Not Downloaded"
        elif all(t.is_cached for t in tiers) or (
            any(t.is_cached for t in tiers) and all(t.is_downloaded for t in tiers)
        ):
            status = "Cached"
        elif all(t.is_compressed for t in tiers) or (
            any(t.is_compressed for t in tiers) and all(t.is_downloaded for t in tiers)
        ):
            status = "Compressed"
        elif all(t.is_downloaded for t in tiers):
            status = "Downloaded"
        elif not any(t.is_downloaded for t in tiers):
            status = "Not Downloaded"
        else:
            dl_count = sum(1 for t in tiers if t.is_downloaded)
            status = f"Partial ({dl_count}/{len(apis)})"

        table_data.append(
            {
                "provider": p,
                "apis": apis,
                "operations": total_ops,
                "status": status,
                "downloaded": all(t.is_downloaded for t in tiers) and len(apis) > 0,
            }
        )

    table = build_providers_table(table_data)
    emit_output(table_data, format_type=c_ctx.output, rich_renderable=table)
    if c_ctx.output == "auto":
        from mapi_cli.ui.console import console

        console.print(
            "[dim]Tip: Run 'mapi apis <service>' to inspect operations or 'mapi download <service>' to download.[/]"
        )


def list_providers(ctx: typer.Context) -> None:
    """Alias for 'mapi apis' listing all available providers."""
    execute_list_providers(ctx)
