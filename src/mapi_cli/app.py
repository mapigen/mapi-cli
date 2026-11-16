from __future__ import annotations

from pathlib import Path

import typer

import mapi_cli
from mapi_cli.commands.apis import list_apis
from mapi_cli.commands.call import execute_call
from mapi_cli.commands.completion import completion_app
from mapi_cli.commands.describe import describe_operation
from mapi_cli.commands.doctor import run_doctor
from mapi_cli.commands.download import execute_download
from mapi_cli.commands.ops import list_operations
from mapi_cli.commands.path import path_app
from mapi_cli.commands.providers import list_providers
from mapi_cli.commands.search import search_all
from mapi_cli.context import CliContext
from mapi_cli.errors import run
from mapi_cli.logging import configure_logging
from mapi_cli.tools import execute_registry_build, execute_validate, tools_app

app = typer.Typer(
    name="mapi",
    help="[bold cyan]mapi[/]: Universal API CLI, toolchain, and discovery engine.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

# 1. Discovery & Inspection Commands
app.command("providers", help="List all available API providers.")(list_providers)
app.command("apis", help="List all APIs for a given provider.")(list_apis)
app.command("ops", help="List operations for a provider and API.")(list_operations)
app.command("operations", help="Alias for 'mapi ops' - list operations.")(list_operations)
app.command("describe", help="Show full parameter details and schema for an operation.")(
    describe_operation
)
app.command("search", help="Fuzzy search across providers, APIs, and operations.")(search_all)

# 2. Execution Commands
app.command("call", help="Execute an operation directly with key=value parameters.")(execute_call)
app.command("download", help="Download and compile remote API specifications.")(execute_download)

# 3. Validation & Build Commands (First-Class Root Commands)
@app.command("validate", help="Validate data directory consistency, schemas, and $ref integrity.")
def cmd_validate_root(
    data_dir: Path | None = typer.Option(
        None, "--data-dir", "-d", help="Directory containing compiled service data"
    ),
    registry_path: Path | None = typer.Option(
        None, "--registry", "-r", help="Path to mapi-registry.json (or legacy services.json)"
    ),
) -> None:
    execute_validate(data_dir=data_dir, registry_path=registry_path)


@app.command("compile", help="Compile mapi-registry.json registry from metadata files on disk.")
def cmd_compile_root(
    data_dir: Path | None = typer.Option(
        None, "--data-dir", "-d", help="Directory containing service metadata"
    ),
    out: Path | None = typer.Option(
        None, "--out", "-o", help="Target mapi-registry.json path"
    ),
) -> None:
    execute_registry_build(data_dir=data_dir, out=out)


app.command("build", help="Alias for 'mapi compile' - compile registry.")(cmd_compile_root)

# 4. Diagnostics & Utilities
app.command("doctor", help="Run diagnostic checks on SDK, transport, and registry.")(run_doctor)

# 5. Sub-apps
app.add_typer(path_app, name="path")
app.add_typer(completion_app, name="completion")
app.add_typer(tools_app, name="tools")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mapi-cli version {mapi_cli.__version__}")
        raise typer.Exit()


@app.callback()
def root(
    ctx: typer.Context,
    data_dir: Path | None = typer.Option(
        None, "--data-dir", envvar="MAPI_DATA_DIR", help="Custom data directory"
    ),
    base_url: str | None = typer.Option(
        None, "--base-url", envvar="MAPI_BASE_URL", help="Override API base URL"
    ),
    timeout: float = typer.Option(
        30.0, "--timeout", envvar="MAPI_TIMEOUT", help="Request timeout in seconds"
    ),
    output: str = typer.Option(
        "auto",
        "--output",
        "-o",
        envvar="MAPI_OUTPUT",
        help="Output format (auto, json, table, raw)",
    ),
    show_meta: bool = typer.Option(
        False, "--show-meta", help="Include response metadata (status, latency, headers)"
    ),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase logging verbosity (stderr)"
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error logs on stderr"),
    version: bool | None = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    configure_logging(verbose=verbose, quiet=quiet)
    ctx.obj = CliContext(
        data_dir=data_dir,
        base_url=base_url,
        timeout=timeout,
        output=output,
        show_meta=show_meta,
    )


def main() -> int:
    return run(app)
