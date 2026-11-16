from __future__ import annotations

import typer
from mapi.models.domain import Parameter, ParameterRef

from mapi_cli.completion import complete_api, complete_operation, complete_provider
from mapi_cli.context import CliContext
from mapi_cli.output import emit_output
from mapi_cli.ui.panels import build_describe_panel


def describe_operation(
    ctx: typer.Context,
    provider: str = typer.Argument(..., help="Provider name", autocompletion=complete_provider),
    api: str = typer.Argument(..., help="API name", autocompletion=complete_api),
    operation: str = typer.Argument(..., help="Operation ID", autocompletion=complete_operation),
    source: str | None = typer.Option(None, "--source", "-s", help="Specific spec source"),
) -> None:
    """Describe an operation including path, HTTP method, parameters, and example call."""
    c_ctx: CliContext = ctx.obj
    client = c_ctx.client

    op = client.discovery.get_operation(provider, api, operation, source=source)

    # Resolve parameter refs from service cache if available
    resolved_params = []
    try:
        actual_source = source or client.discovery.get_api_info(provider, api).sources[0]
        sdata = client._cache.get(provider, api, actual_source)
        for p in op.parameters:
            if isinstance(p, ParameterRef):
                resolved = sdata.components.parameters.get(p.component_name)
                resolved_params.append(resolved if resolved else p)
            else:
                resolved_params.append(p)
    except Exception:
        resolved_params = list(op.parameters)

    panel = build_describe_panel(provider, api, op, resolved_parameters=resolved_params)

    # Serialized structure for JSON output
    data = {
        "operation_id": op.operation_id or operation,
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
