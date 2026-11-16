from __future__ import annotations

import sys

import mapi
import typer
from rich import box
from rich.table import Table

import mapi_cli
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.paths import resolve_data_dir, resolve_registry_path


def run_doctor(ctx: typer.Context) -> None:
    """Check system health, SDK versions, registry status, and environment sanity."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    checks = []

    # 1. Environment & SDK
    checks.append(
        {
            "category": "Environment",
            "check": "Python Version",
            "status": "PASS",
            "details": sys.version.split()[0],
        }
    )
    checks.append(
        {
            "category": "Environment",
            "check": "MAPI SDK Version",
            "status": "PASS",
            "details": getattr(mapi, "__version__", "0.1.0"),
        }
    )
    checks.append(
        {
            "category": "Environment",
            "check": "MAPI CLI Version",
            "status": "PASS",
            "details": mapi_cli.__version__,
        }
    )

    # 2. Path & Registry Resolution
    data_dir, data_src = resolve_data_dir(c_ctx.data_dir)
    reg_path, reg_src = resolve_registry_path(data_dir=data_dir)

    checks.append(
        {
            "category": "Paths",
            "check": "Data Directory",
            "status": "PASS" if data_dir.exists() else "WARN",
            "details": f"{data_dir} ({data_src})",
        }
    )
    checks.append(
        {
            "category": "Paths",
            "check": f"Registry File ({reg_path.name})",
            "status": "PASS" if reg_path.exists() else "WARN",
            "details": f"{reg_path} ({reg_src})",
        }
    )

    # 3. Discovery
    try:
        providers = client.discovery.list_providers()
        checks.append(
            {
                "category": "Registry",
                "check": "Providers Discovered",
                "status": "PASS" if providers else "WARN",
                "details": f"{len(providers)} providers available",
            }
        )
    except Exception as e:
        checks.append(
            {
                "category": "Registry",
                "check": "Providers Discovered",
                "status": "FAIL",
                "details": str(e),
            }
        )

    # 4. Transport
    try:
        import niquests  # type: ignore

        checks.append(
            {
                "category": "Transport",
                "check": "HTTP Transport (niquests)",
                "status": "PASS",
                "details": getattr(niquests, "__version__", "installed"),
            }
        )
    except ImportError:
        checks.append(
            {
                "category": "Transport",
                "check": "HTTP Transport (niquests)",
                "status": "FAIL",
                "details": "niquests not found",
            }
        )

    table = Table(title="System & MAPI Doctor", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Check", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for c in checks:
        status_style = "bold green" if c["status"] == "PASS" else "bold yellow" if c["status"] == "WARN" else "bold red"
        table.add_row(
            c["category"], c["check"], f"[{status_style}]{c['status']}[/]", c["details"]
        )

    emit_output(checks, format_type=c_ctx.output, rich_renderable=table)
