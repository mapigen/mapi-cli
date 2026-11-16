from __future__ import annotations

import typer
from mapi.models.domain import Parameter, ParameterRef

from mapi_cli.completion import (
    complete_api,
    complete_operation,
    complete_target_or_provider,
)
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.resolution import resolve_provider_and_api
from mapi_cli.ui.panels import build_describe_panel


def describe_operation(
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
    source: str | None = typer.Option(None, "--source", "-s", help="Specific spec source"),
) -> None:
    """Describe an operation including path, HTTP method, parameters, and example call.

    Examples:
        mapi describe pokeapi/REST/pokemon_retrieve
        mapi describe pokeapi REST pokemon_retrieve
    """
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    # Handle composite path or split arguments
    if "/" in target:
        parts = target.strip("/").split("/")
        if len(parts) >= 3:
            resolved_provider = parts[0]
            resolved_api = parts[1]
            resolved_operation = parts[2]
        elif len(parts) == 2 and operation:
            resolved_provider = parts[0]
            resolved_api = parts[1]
            resolved_operation = operation
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

    op = client.discovery.get_operation(
        resolved_provider, resolved_api, resolved_operation, source=source
    )

    # Resolve parameter refs from service cache if available
    resolved_params = []
    try:
        actual_source = (
            source
            or client.discovery.get_api_info(resolved_provider, resolved_api).sources[0]
        )
        sdata = client._cache.get(resolved_provider, resolved_api, actual_source)
        for p in op.parameters:
            if isinstance(p, ParameterRef):
                resolved = sdata.components.parameters.get(p.component_name)
                resolved_params.append(resolved if resolved else p)
            else:
                resolved_params.append(p)
    except Exception:
        resolved_params = list(op.parameters)

    panel = build_describe_panel(
        resolved_provider, resolved_api, op, resolved_parameters=resolved_params
    )

    # Serialized structure for JSON output
    data = {
        "provider": resolved_provider,
        "api": resolved_api,
        "operation_id": op.operation_id or resolved_operation,
        "method": op.method,
        "path": op.path,
        "summary": op.summary,
        "description": op.description,
        "parameters": [
            {
                "name": p.name if isinstance(p, Parameter) else p.component_name,
                "in": p.in_ if isinstance(p, Parameter) else "ref",
                "required": p.required if isinstance(p, Parameter) else False,
                "description": p.description if isinstance(p, Parameter) else "",
            }
            for p in resolved_params
        ],
    }

    emit_output(data, format_type=c_ctx.output, rich_renderable=panel)
