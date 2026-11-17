from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import niquests
import typer
import yaml
from rich import box
from rich.table import Table

from mapi_cli.completion import complete_api, complete_provider
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.paths import resolve_data_dir
from mapi_cli.resolution import resolve_provider_and_api
from mapi_cli.storage import is_api_local
from mapi_cli.tools.models import CompileConfig, SpecSourceConfig
from mapi_cli.tools.pipeline import process_service
from mapi_cli.ui.console import console


def _is_api_local(data_dir: Path, provider: str, source: str, api: str) -> bool:
    return is_api_local(data_dir, provider, source, api)


def _download_and_compile(
    client: Any,
    data_dir: Path,
    provider: str,
    api: str,
    force: bool = False,
) -> dict[str, Any]:
    try:
        info = client.discovery.get_api_info(provider, api)
    except Exception as e:
        return {
            "provider": provider,
            "api": api,
            "status": "error",
            "message": f"API info not found in registry: {e}",
        }

    sources = getattr(info, "sources", []) or ["github"]
    source = sources[0]

    if not force and _is_api_local(data_dir, provider, source, api):
        return {
            "provider": provider,
            "api": api,
            "source": source,
            "status": "skipped",
            "message": "Already downloaded (use --force to re-download)",
        }

    spec_url = getattr(info, "spec_url", None)
    if not spec_url:
        return {
            "provider": provider,
            "api": api,
            "source": source,
            "status": "error",
            "message": "No remote spec_url registered for this API",
        }

    try:
        resp = niquests.get(spec_url, timeout=30.0)
        resp.raise_for_status()
        raw_bytes = resp.content or b""

        # Write to temporary file for pipeline processing
        suffix = ".yaml" if (spec_url and spec_url.lower().endswith((".yaml", ".yml"))) else ".json"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)

        try:
            source_cfg = SpecSourceConfig(
                provider=provider,
                api=api,
                source=source,
                url=spec_url,
            )
            metrics = process_service(
                source_cfg=source_cfg,
                raw_spec_path=tmp_path,
                data_dir=data_dir,
                config=CompileConfig(),
            )

            if metrics.status == "success":
                # Write metadata.yml
                out_dir = data_dir / provider / source / api
                out_dir.mkdir(parents=True, exist_ok=True)
                metadata_path = out_dir / "metadata.yml"

                # Rule of thumb: if popularity rank already exists in local storage of the project,
                # do NOT override it. Defaults only apply to new/unranked items.
                existing_pop = None
                if metadata_path.exists():
                    try:
                        existing_meta = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
                        if "popularity_rank" in existing_meta and existing_meta["popularity_rank"] is not None:
                            existing_pop = existing_meta["popularity_rank"]
                    except Exception:
                        pass

                local_pop_file = data_dir / "popularity.json"
                if existing_pop is None and local_pop_file.exists():
                    try:
                        pop_data = json.loads(local_pop_file.read_text(encoding="utf-8"))
                        if provider in pop_data:
                            existing_pop = pop_data[provider]
                    except Exception:
                        pass

                final_pop_rank = (
                    existing_pop if existing_pop is not None else getattr(info, "popularity_rank", 999)
                )

                meta_dict = {
                    "format_version": 3,
                    "api_reference": spec_url,
                    "status": "success",
                    "operation_count": metrics.operation_count,
                    "reusable_parameter_count": metrics.reusable_param_count,
                    "auth_types": getattr(info, "auth_types", []),
                    "primary_auth": getattr(info, "primary_auth", "none"),
                    "popularity_rank": final_pop_rank,
                }
                metadata_path.write_text(yaml.dump(meta_dict), encoding="utf-8")

                return {
                    "provider": provider,
                    "api": api,
                    "source": source,
                    "status": "downloaded",
                    "operations": metrics.operation_count,
                    "bytes": len(raw_bytes),
                    "path": metrics.mapi_path,
                }
            else:
                return {
                    "provider": provider,
                    "api": api,
                    "source": source,
                    "status": "failed",
                    "message": metrics.error_message or "Compilation failed",
                }
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    except Exception as e:
        return {
            "provider": provider,
            "api": api,
            "source": source,
            "status": "error",
            "message": str(e),
        }


def execute_download(
    ctx: typer.Context,
    target: str | None = typer.Argument(
        None,
        help="Provider or composite 'provider/api' to download",
        autocompletion=complete_provider,
    ),
    api: str | None = typer.Argument(
        None,
        help="API name (optional if provider/api target given)",
        autocompletion=complete_api,
    ),
    all_apis: bool = typer.Option(
        False,
        "--all",
        "-all",
        "-a",
        help="Download and compile all available APIs declared in the registry",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-download even if already downloaded locally",
    ),
    no_tui: bool = typer.Option(
        False,
        "--no-tui",
        envvar="MAPI_NO_TUI",
        help="Disable interactive Textual TUI (Tip: Pass --no-tui or set MAPI_NO_TUI=1 to disable TUI mode)",
    ),
) -> None:
    """Download and compile remote API specifications into local storage."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client
    data_dir, _ = resolve_data_dir()

    discovery = client.discovery
    all_providers = discovery.list_providers()

    # Case 1: --all / -all flag
    if all_apis:
        items_to_download: list[tuple[str, str]] = []
        for p in all_providers:
            for a in discovery.list_apis(p):
                items_to_download.append((p, a))

        if not items_to_download:
            console.print("[dim]No APIs found in registry.[/]")
            return

        results: list[dict[str, Any]] = []
        with console.status("[bold cyan]Downloading and compiling API specs...[/]"):
            for p, a in items_to_download:
                res = _download_and_compile(client, data_dir, p, a, force=force)
                results.append(res)

        table = Table(title="Download Results", box=box.ROUNDED)
        table.add_column("Provider", style="cyan")
        table.add_column("API", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")

        for r in results:
            st = r.get("status", "unknown")
            badge = (
                "[bold green]Downloaded[/]"
                if st == "downloaded"
                else "[yellow]Skipped[/]"
                if st == "skipped"
                else f"[bold red]{st}[/]"
            )
            detail = (
                f"{r.get('operations', 0)} ops ({r.get('bytes', 0)} bytes)"
                if st == "downloaded"
                else r.get("message", "")
            )
            table.add_row(r["provider"], r["api"], badge, detail)

        emit_output(results, format_type=c_ctx.output, rich_renderable=table)
        return

    # Case 2: Specific target given via positional argument
    if target:
        if "/" in target:
            parts = target.split("/", 1)
            provider_name = parts[0]
            api_name = parts[1]
        else:
            provider_name = target
            api_name = api

        prov, resolved_api = resolve_provider_and_api(discovery, provider_name, api_name or "")
        apis_to_sync = [resolved_api] if resolved_api else discovery.list_apis(prov)

        if not apis_to_sync:
            console.print(f"[bold red]Error:[/] No APIs found for provider '{target}'.")
            raise typer.Exit(1)

        results = []
        for a in apis_to_sync:
            with console.status(f"[bold cyan]Downloading {prov}/{a}...[/]"):
                res = _download_and_compile(client, data_dir, prov, a, force=force)
                results.append(res)

        table = Table(title=f"Download Status for '{prov}'", box=box.ROUNDED)
        table.add_column("API", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")

        for r in results:
            st = r.get("status", "unknown")
            badge = (
                "[bold green]Downloaded[/]"
                if st == "downloaded"
                else "[yellow]Skipped[/]"
                if st == "skipped"
                else f"[bold red]{st}[/]"
            )
            detail = (
                f"{r.get('operations', 0)} ops ({r.get('bytes', 0)} bytes)"
                if st == "downloaded"
                else r.get("message", "")
            )
            table.add_row(r["api"], badge, detail)

        emit_output(results, format_type=c_ctx.output, rich_renderable=table)
        return

    # Case 3: No arguments given -> interactive TUI if in TTY, else fallback prompt
    import sys
    if sys.stdin.isatty() and not no_tui:
        from mapi_cli.ui.download_tui import DownloadTUIApp

        tui_app = DownloadTUIApp(client=client, data_dir=data_dir)
        tui_app.force = force
        tui_app.run()
        return

    console.print("[bold cyan]MAPI Spec Download Selection[/]\n")
    candidates: list[tuple[str, str, str]] = []
    for p in all_providers:
        for a in discovery.list_apis(p):
            info = discovery.get_api_info(p, a)
            src = (getattr(info, "sources", []) or ["github"])[0]
            is_dl = _is_api_local(data_dir, p, src, a)
            dl_str = "[bold green]Downloaded[/]" if is_dl else "[yellow]Not Downloaded[/]"
            candidates.append((p, a, dl_str))

    console.print("Available providers and APIs in registry:")
    for idx, (p, a, status_str) in enumerate(candidates, start=1):
        console.print(f"  [bold cyan]{idx}[/]) {p}/{a} ({status_str})")

    choice_str = typer.prompt(
        f"\nEnter selection number (1-{len(candidates)}) or provider name",
        default="1",
    )

    selected_p = ""
    selected_a = ""
    if choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        if 0 <= choice_idx < len(candidates):
            selected_p, selected_a, _ = candidates[choice_idx]
    else:
        prov = choice_str.strip()
        apis = discovery.list_apis(prov)
        if apis:
            selected_p = prov
            selected_a = apis[0]

    if not selected_p or not selected_a:
        console.print("[bold red]Invalid selection.[/]")
        raise typer.Exit(1)

    with console.status(f"[bold cyan]Downloading {selected_p}/{selected_a}...[/]"):
        res = _download_and_compile(client, data_dir, selected_p, selected_a, force=force)

    st = res.get("status", "unknown")
    if st == "downloaded":
        console.print(
            f"[bold green]Successfully downloaded {selected_p}/{selected_a}![/] "
            f"({res.get('operations', 0)} operations compiled to {res.get('path', '')})"
        )
    elif st == "skipped":
        console.print(f"[yellow]{res.get('message', 'Already downloaded.')}[/]")
    else:
        console.print(f"[bold red]Download failed:[/] {res.get('message', 'Error')}")
