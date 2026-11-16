from __future__ import annotations

from typing import Any

import typer
from rich import box
from rich.table import Table

from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.ui.theme import method_style

HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def search_all(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., help="Search term across providers, APIs, operations, paths, or methods"
    ),
    method: str | None = typer.Option(
        None, "--method", "-m", help="Filter by HTTP method (e.g. GET, POST, PUT, DELETE, PATCH)"
    ),
) -> None:
    """Fuzzy search across all registered providers, APIs, and operations."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client
    q = query.strip().lower()

    allowed_methods = (
        {m.strip().upper() for m in method.split(",") if m.strip()}
        if method
        else None
    )

    matches: list[dict[str, Any]] = []

    # 1. Search providers (only if method constraint is not set)
    if not allowed_methods:
        for prov in client.discovery.list_providers():
            if q in prov.lower():
                matches.append(
                    {
                        "type": "provider",
                        "provider": prov,
                        "api": "-",
                        "method": "-",
                        "operation": prov,
                        "path": "-",
                        "summary": "",
                    }
                )

    # 2. Search APIs (only if method constraint is not set)
    if not allowed_methods:
        for prov in client.discovery.list_providers():
            for api in client.discovery.list_apis(prov):
                if q in api.lower():
                    matches.append(
                        {
                            "type": "api",
                            "provider": prov,
                            "api": api,
                            "method": "-",
                            "operation": api,
                            "path": "-",
                            "summary": "",
                        }
                    )

    # 3. Search Operations across all providers and APIs
    for prov in client.discovery.list_providers():
        for api in client.discovery.list_apis(prov):
            try:
                src = client.discovery._resolve_source(prov, api, None)
                sd = client.discovery._get_service_data(prov, api, src)
                for op_id, op in sd.operations.items():
                    op_method = op.method.upper()
                    if allowed_methods and op_method not in allowed_methods:
                        continue

                    method_match = (q.upper() in HTTP_METHODS) and (op_method == q.upper())
                    text_match = (
                        q in (op.operation_id or "").lower()
                        or q in (op.path or "").lower()
                        or q in (op.summary or "").lower()
                        or q in (op.description or "").lower()
                    )
                    if method_match or text_match:
                        matches.append(
                            {
                                "type": "operation",
                                "provider": prov,
                                "api": api,
                                "method": op_method,
                                "operation": op.operation_id or op_id,
                                "path": op.path,
                                "summary": op.summary or "",
                            }
                        )
            except Exception:
                # Spec not downloaded or unreadable; fallback to listed op names
                try:
                    for op_name in client.discovery.list_operations(prov, api):
                        if allowed_methods:
                            continue
                        if q in op_name.lower():
                            matches.append(
                                {
                                    "type": "operation",
                                    "provider": prov,
                                    "api": api,
                                    "method": "-",
                                    "operation": op_name,
                                    "path": "-",
                                    "summary": "",
                                }
                            )
                except Exception:
                    pass

    title = f"Search Results for '{query}'"
    if method:
        title += f" [method: {method.upper()}]"

    table = Table(
        title=title,
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("Type", style="bold yellow")
    table.add_column("Provider", style="provider")
    table.add_column("API", style="api")
    table.add_column("Method", justify="center")
    table.add_column("Operation", style="op", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Summary", style="dim")

    for m in matches:
        m_meth = m.get("method", "-")
        badge = f"[{method_style(m_meth)}]{m_meth}[/]" if m_meth != "-" else "[dim]-[/]"

        table.add_row(
            m["type"],
            m["provider"],
            m["api"],
            badge,
            m["operation"],
            m.get("path", "-"),
            (m.get("summary") or "")[:40] + ("..." if len(m.get("summary") or "") > 40 else ""),
        )

    emit_output(matches, format_type=c_ctx.output, rich_renderable=table)
