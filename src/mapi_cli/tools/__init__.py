from __future__ import annotations

from pathlib import Path

import msgspec
import typer
from rich import box
from rich.table import Table

from mapi_cli.paths import resolve_data_dir, resolve_registry_path
from mapi_cli.tools.converter import normalize_spec
from mapi_cli.tools.extractor import extract_service_data
from mapi_cli.tools.fetcher import fetch_spec
from mapi_cli.tools.registry_builder import RegistryBuilder
from mapi_cli.tools.validate import validate_data_directory
from mapi_cli.ui.console import console

tools_app = typer.Typer(
    name="tools",
    help="Maintainer build tools: fetch, extract, compile, validate, and build registries.",
    no_args_is_help=True,
)


def execute_validate(
    data_dir: Path | None = None,
    registry_path: Path | None = None,
) -> None:
    """Core implementation for directory validation, used by both root and tools validate."""
    target_data_dir, _ = resolve_data_dir(data_dir)
    target_reg_path, _ = resolve_registry_path(data_dir=target_data_dir, explicit=registry_path)

    result = validate_data_directory(target_data_dir, target_reg_path)
    table = Table(
        title=f"Validation Report ({target_reg_path.name})",
        box=box.ROUNDED,
        caption=f"[dim]Data: {target_data_dir} | Registry: {target_reg_path}[/]",
    )
    table.add_column("Total Services", justify="right")
    table.add_column("Valid Services", justify="right", style="green")
    table.add_column("Broken Refs", justify="right", style="red")
    table.add_column("Schema Errors", justify="right", style="red")

    table.add_row(
        str(result.total_services),
        str(result.valid_services),
        str(len(result.broken_refs)),
        str(len(result.schema_errors)),
    )
    console.print(table)

    if result.broken_refs or result.schema_errors:
        for s, errs in result.broken_refs.items():
            console.print(f"[bold red]{s}:[/] {', '.join(errs)}")
        for s, errs in result.schema_errors.items():
            console.print(f"[bold red]{s}:[/] {', '.join(errs)}")
        raise typer.Exit(1)


def execute_registry_build(
    data_dir: Path | None = None,
    out: Path | None = None,
) -> None:
    """Core implementation for registry compilation, used by both compile and registry-build."""
    target_data_dir, _ = resolve_data_dir(data_dir)
    target_out, _ = resolve_registry_path(data_dir=target_data_dir, explicit=out)

    builder = RegistryBuilder(data_dir=target_data_dir, registry_path=target_out)
    reg = builder.build_registry()
    builder.save_registry(reg)
    console.print(f"[bold green]Registry compiled:[/] {len(reg.providers)} providers -> {target_out}")


@tools_app.command("fetch")
def cmd_fetch(
    url: str = typer.Argument(..., help="Upstream specification URL"),
    out: Path = typer.Option(..., "--out", "-o", help="Target output file path"),
    timeout: float = typer.Option(30.0, "--timeout", help="Download timeout in seconds"),
) -> None:
    """Download an upstream specification from a remote URL."""
    res = fetch_spec(url, out, timeout=timeout)
    if res.status == "downloaded":
        console.print(f"[bold green]Downloaded:[/] {res.bytes_downloaded} bytes -> {out}")
    else:
        console.print(f"[bold red]Download failed:[/] {res.error_message}")
        raise typer.Exit(1)


@tools_app.command("extract")
def cmd_extract(
    spec_path: Path = typer.Argument(..., help="Path to raw YAML or JSON specification"),
    out: Path = typer.Option(..., "--out", "-o", help="Output ServiceData JSON path"),
    service_name: str = typer.Option(
        "extracted_service", "--name", "-n", help="Service identifier"
    ),
) -> None:
    """Extract an OpenAPI spec into a typed ServiceData structure."""
    raw = normalize_spec(path=spec_path)
    sdata = extract_service_data(service_name, raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(msgspec.json.encode(sdata))
    console.print(
        f"[bold green]Extracted:[/] {len(sdata.operations)} operations, {len(sdata.components.parameters)} reusable params -> {out}"
    )


@tools_app.command("validate")
def cmd_validate(
    data_dir: Path | None = typer.Option(
        None, "--data-dir", "-d", help="Directory containing compiled service data"
    ),
    registry_path: Path | None = typer.Option(
        None, "--registry", "-r", help="Path to mapi-registry.json (or legacy services.json)"
    ),
) -> None:
    """Validate data directory consistency, schemas, and $ref integrity."""
    execute_validate(data_dir=data_dir, registry_path=registry_path)


@tools_app.command("registry-build")
def cmd_registry_build(
    data_dir: Path | None = typer.Option(
        None, "--data-dir", "-d", help="Directory containing service metadata"
    ),
    out: Path | None = typer.Option(
        None, "--out", "-o", help="Target mapi-registry.json path"
    ),
) -> None:
    """Compile mapi-registry.json registry from metadata files on disk."""
    execute_registry_build(data_dir=data_dir, out=out)
