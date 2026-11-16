from __future__ import annotations

import typer

from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.ui.tables import build_providers_table


def execute_list_providers(ctx: typer.Context) -> None:
    """List all available API providers with download status."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    providers = client.discovery.list_providers()
    table_data = []
    for p in providers:
        apis = client.discovery.list_apis(p)
        total_ops = 0
        downloaded_count = 0
        for a in apis:
            try:
                info = client.discovery.get_api_info(p, a)
                total_ops += info.operation_count
                is_dl = False
                for src in info.sources:
                    s_dir = client._loader.service_dir(p, a, src)
                    if (
                        (s_dir / f"{a}.mapi.json.zst").exists()
                        or (s_dir / f"{a}.mapi.json").exists()
                        or (s_dir / f"{a}.mapi.msgpack.zst").exists()
                    ):
                        is_dl = True
                        break
                if is_dl:
                    downloaded_count += 1
            except Exception:
                pass

        if not apis:
            status = "Not Downloaded"
        elif downloaded_count == len(apis):
            status = "Downloaded"
        elif downloaded_count == 0:
            status = "Not Downloaded"
        else:
            status = f"Partial ({downloaded_count}/{len(apis)})"

        table_data.append(
            {
                "provider": p,
                "apis": apis,
                "operations": total_ops,
                "status": status,
                "downloaded": downloaded_count == len(apis) and len(apis) > 0,
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
