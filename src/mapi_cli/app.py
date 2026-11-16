from __future__ import annotations

from pathlib import Path

import typer

import mapi_cli
from mapi_cli.commands.apis import list_apis
from mapi_cli.commands.call import execute_call
from mapi_cli.commands.describe import describe_operation
from mapi_cli.commands.doctor import run_doctor
from mapi_cli.commands.ops import list_operations
from mapi_cli.commands.providers import list_providers
from mapi_cli.commands.search import search_all
from mapi_cli.context import CliContext
from mapi_cli.errors import run
from mapi_cli.logging import configure_logging
from mapi_cli.tools import tools_app

app = typer.Typer(
    name="mapi",
    help="mapi: Universal CLI and developer toolchain for the MAPI SDK.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# Register top-level commands
app.command("providers", help="List all available providers.")(list_providers)
app.command("apis", help="List all APIs for a given provider.")(list_apis)
app.command("ops", help="List operations for a provider and API.")(list_operations)
app.command("describe", help="Show full parameter details and schema for an operation.")(
    describe_operation
)
app.command("call", help="Execute an operation directly with key=value parameters.")(execute_call)
app.command("search", help="Fuzzy search across providers, APIs, and operations.")(search_all)
app.command("doctor", help="Run diagnostic checks on SDK, transport, and registry.")(run_doctor)

# Register sub-apps
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
