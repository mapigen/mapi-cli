from __future__ import annotations

import json
import os
import sys
from typing import Any

import typer
from mapi import ApiKeyAuth, BearerAuth
from mapi.models.request import RequestConfig
from mapi.models.response import MapiResult

from mapi_cli.completion import (
    complete_api,
    complete_call_parameters,
    complete_operation,
    complete_target_or_provider,
)
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.resolution import resolve_provider_and_api
from mapi_cli.ui.console import console
from mapi_cli.ui.panels import build_dry_run_panel


def _parse_param_value(val: str) -> Any:
    """Parse string value into integer/boolean/float/json if valid, else string."""
    try:
        return json.loads(val)
    except Exception:
        return val


def execute_call(
    ctx: typer.Context,
    target: str = typer.Argument(
        ...,
        help="Provider or composite path 'provider/api/operation'",
        autocompletion=complete_target_or_provider,
    ),
    api: str | None = typer.Argument(
        None,
        help="API name (optional if composite path is used)",
        autocompletion=complete_api,
    ),
    operation: str | None = typer.Argument(
        None,
        help="Operation ID (optional if composite path is used)",
        autocompletion=complete_operation,
    ),
    params: list[str] = typer.Argument(
        None,
        help="Key=value parameters (e.g. id=123 limit=10 status=active)",
        autocompletion=complete_call_parameters,
    ),
    source: str | None = typer.Option(None, "--source", "-s", help="Specific spec source"),
    data: str | None = typer.Option(
        None, "--data", "-d", help="JSON body (raw string, @file.json, or - for stdin)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Prepare and inspect request without sending"
    ),
    emit_curl: bool = typer.Option(False, "--curl", help="Print equivalent curl command"),
    idempotent: bool = typer.Option(
        False, "--idempotent", help="Automatically inject Idempotency-Key UUID"
    ),
    bearer: str | None = typer.Option(None, "--bearer", help="Bearer authorization token"),
    api_key: str | None = typer.Option(None, "--api-key", help="API Key authorization token"),
    auth_env: str | None = typer.Option(
        None, "--auth-env", help="Environment variable name holding auth token"
    ),
) -> None:
    """Execute an API operation directly from the command line.

    Examples:
        mapi call pokeapi/REST/pokemon_retrieve id=ditto
        mapi call pokeapi REST pokemon_retrieve id=ditto
    """
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    # Parse target and parameters
    actual_params = list(params) if params else []
    if "/" in target:
        parts = target.strip("/").split("/")
        if len(parts) >= 3:
            resolved_provider = parts[0]
            resolved_api = parts[1]
            resolved_operation = parts[2]
            leftovers = [x for x in (api, operation) if x is not None]
            actual_params = leftovers + actual_params
        elif len(parts) == 2 and operation:
            resolved_provider = parts[0]
            resolved_api = parts[1]
            resolved_operation = operation
            if api is not None:
                actual_params = [api] + actual_params
        else:
            raise typer.BadParameter(
                "Invalid composite path. Expected format: 'provider/api/operation' (e.g. pokeapi/REST/pokemon_retrieve)"
            )
    else:
        if not api or not operation:
            raise typer.BadParameter(
                "Missing API or Operation ID. Provide 'provider/api/operation' or separate arguments."
            )
        resolved_provider = target
        resolved_api = api
        resolved_operation = operation

    resolved_provider, resolved_api = resolve_provider_and_api(
        client.discovery, resolved_provider, resolved_api
    )

    # Parse key=value arguments
    kwargs: dict[str, Any] = {}
    for p in actual_params:
        if "=" in p:
            k, v = p.split("=", 1)
            kwargs[k.strip()] = _parse_param_value(v.strip())
        else:
            kwargs[p.strip()] = True

    # Parse --data payload
    if data:
        if data == "-":
            raw_body = sys.stdin.read()
            kwargs["json_body"] = json.loads(raw_body)
        elif data.startswith("@"):
            file_path = data[1:]
            with open(file_path, encoding="utf-8") as f:
                kwargs["json_body"] = json.load(f)
        else:
            kwargs["json_body"] = json.loads(data)

    # Set up auth
    auth = None
    if bearer:
        auth = BearerAuth(bearer)
    elif api_key:
        auth = ApiKeyAuth(key=api_key, name="X-Api-Key")
    elif auth_env and auth_env in os.environ:
        auth = BearerAuth(os.environ[auth_env])
    else:
        # Check standard MAPI_<PROVIDER>_TOKEN env var
        prov_env = f"MAPI_{resolved_provider.upper()}_TOKEN"
        if prov_env in os.environ:
            auth = BearerAuth(os.environ[prov_env])

    if auth:
        client._auth = auth

    # Flags
    if dry_run or emit_curl:
        kwargs["_dry_run"] = True
    if idempotent:
        kwargs["_idempotent"] = True

    # Execute with spinner if interactive
    if not (dry_run or emit_curl) and console.is_terminal and c_ctx.output == "auto":
        with console.status(
            f"[bold cyan]Calling {resolved_provider}/{resolved_api}/{resolved_operation}...[/]"
        ):
            res: MapiResult = client.execute(
                resolved_provider, resolved_api, source, resolved_operation, **kwargs
            )
    else:
        res = client.execute(
            resolved_provider, resolved_api, source, resolved_operation, **kwargs
        )

    if emit_curl and isinstance(res.data, RequestConfig):
        console.print(res.data.to_curl())
        return

    if dry_run and isinstance(res.data, RequestConfig):
        panel = build_dry_run_panel(res.data)
        emit_output(res.data, format_type=c_ctx.output, rich_renderable=panel)
        return

    emit_output(res, format_type=c_ctx.output, show_meta=c_ctx.show_meta)
