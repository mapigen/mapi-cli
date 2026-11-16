from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from mapi_cli.config import (
    get_config_path,
    reset_config,
    set_config_value,
)
from mapi_cli.paths import (
    auto_discover_candidates,
    find_installed_mapi_sdk,
    find_registry_in_dir,
    resolve_data_dir,
    resolve_registry_path,
)
from mapi_cli.ui.console import console

path_app = typer.Typer(
    name="path",
    help="Manage, find, and configure MAPI SDK and data directory paths.",
    no_args_is_help=False,
)


@path_app.callback(invoke_without_command=True)
def path_default(ctx: typer.Context) -> None:
    """Show active MAPI paths and discovery status when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        show_path()


@path_app.command("show")
def show_path() -> None:
    """Display active MAPI SDK, data directory, registry, and configuration status."""
    sdk_installed, sdk_version, sdk_path = find_installed_mapi_sdk()
    data_dir, data_source = resolve_data_dir()
    reg_path, reg_source = resolve_registry_path(data_dir=data_dir)
    cfg_file = get_config_path()

    table = Table(title="MAPI Path & Environment Status", box=box.ROUNDED)
    table.add_column("Component", style="bold cyan", no_wrap=True)
    table.add_column("Status / Path", style="white", overflow="fold")
    table.add_column("Source", style="dim")

    # 1. SDK Status
    if sdk_installed:
        sdk_desc = f"[bold green]Installed[/] v{sdk_version}\n[dim]{sdk_path}[/]"
        table.add_row("Core MAPI SDK", sdk_desc, "Python Environment")
    else:
        table.add_row(
            "Core MAPI SDK",
            "[bold yellow]Not directly imported in current environment[/]",
            "Check virtualenv",
        )

    # 2. Data Directory
    data_status = (
        f"[bold green]Exists[/] ({data_dir})"
        if data_dir.exists()
        else f"[bold red]Missing[/] ({data_dir})"
    )
    table.add_row("Data Directory", data_status, data_source)

    # 3. Registry File
    if reg_path.exists():
        try:
            reg_data = json.loads(reg_path.read_text(encoding="utf-8"))
            prov_count = len(reg_data.get("providers", {}))
            reg_desc = f"[bold green]Found:[/] {reg_path.name} ({prov_count} providers)\n[dim]{reg_path}[/]"
        except Exception:
            reg_desc = f"[bold green]Found:[/] {reg_path.name}\n[dim]{reg_path}[/]"
    else:
        reg_desc = f"[bold yellow]Not Found[/] (expected: {reg_path.name})\n[dim]{reg_path}[/]"
    table.add_row("Registry File", reg_desc, reg_source)

    # 4. User Configuration
    cfg_status = (
        f"[bold green]Configured[/] ({cfg_file})"
        if cfg_file.exists()
        else f"[dim]Not set ({cfg_file})[/]"
    )
    table.add_row("Config File", cfg_status, "platformdirs")

    console.print(table)


@path_app.command("find")
def find_path() -> None:
    """Scan the environment and filesystem to auto-discover MAPI installations."""
    candidates = auto_discover_candidates()

    table = Table(title="MAPI Path Auto-Discovery Scan", box=box.ROUNDED)
    table.add_column("Source", style="bold cyan")
    table.add_column("Path", style="white")
    table.add_column("Directory?", justify="center")
    table.add_column("Registry File", style="yellow")

    for c in candidates:
        is_dir_badge = "[bold green]YES[/]" if c["is_dir"] else "[dim]NO[/]"
        reg_badge = (
            f"[bold green]{c['registry_file'].name}[/]"
            if c["registry_file"]
            else "[dim]none[/]"
        )
        table.add_row(c["source"], str(c["path"]), is_dir_badge, reg_badge)

    console.print(table)

    active_dir, active_src = resolve_data_dir()
    console.print(
        f"\n[bold]Current Active Path:[/] [cyan]{active_dir}[/] ([dim]via {active_src}[/])"
    )


@path_app.command("set")
def set_path(
    path: Path = typer.Argument(..., help="Path to MAPI data directory or repository"),
) -> None:
    """Set and persist custom MAPI data path in user configuration."""
    resolved = path.resolve()
    if not resolved.exists():
        console.print(f"[bold red]Error:[/] Path does not exist: {resolved}")
        raise typer.Exit(1)

    # If the user pointed to a repo containing a 'data' folder, use that
    target_data_dir = resolved
    if (resolved / "data").is_dir():
        target_data_dir = resolved / "data"

    reg_file = find_registry_in_dir(target_data_dir) or find_registry_in_dir(resolved)
    cfg_path = set_config_value("data_dir", str(target_data_dir))
    if reg_file:
        set_config_value("registry_path", str(reg_file))

    panel = Panel(
        f"[bold green]MAPI path successfully configured![/]\n\n"
        f"[bold]Data Directory:[/] [cyan]{target_data_dir}[/]\n"
        f"[bold]Registry File:[/]  [yellow]{reg_file or 'mapi-registry.json (not found yet)'}[/]\n"
        f"[bold]Saved in:[/]       [dim]{cfg_path}[/]",
        title="Configuration Updated",
        box=box.ROUNDED,
    )
    console.print(panel)


@path_app.command("reset")
def reset_path() -> None:
    """Reset custom configured path and restore auto-discovery."""
    cleared = reset_config()
    if cleared:
        console.print(
            "[bold green]Custom path configuration removed.[/] Default auto-discovery restored."
        )
    else:
        console.print("[dim]No custom configuration was active.[/]")
