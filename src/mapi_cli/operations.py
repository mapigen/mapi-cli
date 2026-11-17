from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from mapi import ApiKeyAuth, BearerAuth
from mapi.models.domain import ParameterRef
from mapi.models.request import RequestConfig
from mapi.models.response import MapiResult

log = logging.getLogger(__name__)


def format_param_type(schema: Any) -> str:
    """Extract a concise, human-readable OpenAPI type string."""
    if not isinstance(schema, dict):
        return "any"
    t = schema.get("type")
    fmt = schema.get("format")
    if t == "array":
        item_schema = schema.get("items", {})
        item_type = format_param_type(item_schema)
        return f"list[{item_type}]"
    if t and fmt:
        return f"{t}:{fmt}"
    if t:
        return str(t)
    if "$ref" in schema:
        return str(schema["$ref"].split("/")[-1])
    return "any"


def _parse_typed_value(raw_val: str, expected_type: str | None = None) -> Any:
    """Parse raw string input respecting OpenAPI parameter type hints."""
    raw_clean = raw_val.strip()
    if expected_type == "string":
        return raw_clean
    if expected_type == "integer":
        try:
            return int(raw_clean)
        except ValueError:
            return raw_clean
    if expected_type == "number":
        try:
            return float(raw_clean)
        except ValueError:
            return raw_clean
    if expected_type == "boolean":
        return raw_clean.lower() in ("true", "1", "yes", "t")

    # Fallback to json.loads or string
    try:
        return json.loads(raw_clean)
    except Exception:
        return raw_clean


@dataclass(frozen=True)
class OperationParamDetail:
    """Inspected details for a single API parameter."""

    name: str
    in_: str  # "path", "query", "header", "cookie", "body"
    is_required: bool
    type_str: str  # "integer", "string", "boolean", "array", etc.
    description: str = ""
    default: Any = None
    enum_values: list[Any] | None = None


@dataclass(frozen=True)
class OperationAuthDetail:
    """Authentication and permission requirements for an API operation."""

    primary_auth: str  # "none", "bearer_token", "api_key", "oauth2"
    auth_types: list[str] = field(default_factory=list)
    scheme: str = ""  # "Bearer", "Bot", etc.
    is_required: bool = False
    is_configured: bool = False
    token_source: str | None = None  # "env:MAPI_GITHUB_TOKEN", "client._auth", "inline"
    env_var_name: str = ""  # "MAPI_GITHUB_TOKEN"
    message: str = ""


@dataclass(frozen=True)
class OperationRequirementCheck:
    """Complete requirement inspection result for an operation."""

    provider: str
    api: str
    source: str
    operation_id: str
    method: str
    path: str
    summary: str
    description: str
    parameters: list[OperationParamDetail] = field(default_factory=list)
    required_parameters: list[OperationParamDetail] = field(default_factory=list)
    optional_parameters: list[OperationParamDetail] = field(default_factory=list)
    missing_parameters: list[OperationParamDetail] = field(default_factory=list)
    auth: OperationAuthDetail = field(
        default_factory=lambda: OperationAuthDetail(primary_auth="none")
    )
    can_execute: bool = False
    status_summary: str = ""
    example_call: str = ""


def check_operation_requirements(
    client: Any,
    provider: str,
    api: str,
    operation_id: str,
    kwargs: dict[str, Any] | None = None,
    source: str | None = None,
) -> OperationRequirementCheck:
    """Inspect all parameters, required arguments, auth schemes, and missing inputs for an operation.

    All details are provided directly from MAPI specification and registry metadata.
    """
    call_kwargs = kwargs or {}
    src = client.discovery._resolve_source(provider, api, source)
    sd = client.discovery._get_service_data(provider, api, src)

    # Resolve operation
    op = sd.operations.get(operation_id)
    if op is None:
        # Search by operation_id field
        for cand_id, cand_op in sd.operations.items():
            if cand_op.operation_id == operation_id:
                op = cand_op
                operation_id = cand_id
                break

    if op is None:
        raise KeyError(f"Operation '{operation_id}' not found for '{provider}/{api}'")

    # Resolve parameters from components
    param_details: list[OperationParamDetail] = []
    for p in op.parameters:
        if isinstance(p, ParameterRef):
            resolved = sd.components.parameters.get(p.component_name, p)
        else:
            resolved = p

        p_name = getattr(resolved, "name", getattr(p, "component_name", str(p)))
        p_in = getattr(resolved, "in_", "query")
        p_req = getattr(resolved, "is_required", False)
        p_desc = getattr(resolved, "description", "") or ""
        p_schema = getattr(resolved, "schema_", {}) or {}
        type_str = format_param_type(p_schema)
        default_val = p_schema.get("default") if isinstance(p_schema, dict) else None
        enums = p_schema.get("enum") if isinstance(p_schema, dict) else None

        param_details.append(
            OperationParamDetail(
                name=p_name,
                in_=p_in,
                is_required=p_req,
                type_str=type_str,
                description=p_desc,
                default=default_val,
                enum_values=enums,
            )
        )

    required_params = [p for p in param_details if p.is_required]
    optional_params = [p for p in param_details if not p.is_required]

    # Missing parameters: required params not in kwargs (or json_body / data)
    missing_params: list[OperationParamDetail] = []
    for rp in required_params:
        if (
            rp.name not in call_kwargs
            and rp.name != "json_body"
            and rp.name != "data"
            and (rp.in_ != "body" or "json_body" not in call_kwargs)
        ):
            missing_params.append(rp)

    # Auth & Permissions check
    info = client.discovery.get_api_info(provider, api)
    primary_auth = (getattr(info, "primary_auth", None) or "none").lower()
    auth_types = getattr(info, "auth_types", []) or []
    auth_overrides = getattr(info, "auth_overrides", {}) or {}
    scheme = auth_overrides.get("scheme", "Bearer" if primary_auth == "bearer_token" else "")
    env_var_name = f"MAPI_{provider.upper()}_TOKEN"
    is_auth_required = primary_auth not in ("none", "")

    token_source: str | None = None
    if getattr(client, "_auth", None) is not None:
        token_source = "client._auth"
    elif any(k in call_kwargs for k in ("token", "bearer", "api_key")):
        token_source = "inline"
    elif env_var_name in os.environ:
        token_source = f"env:{env_var_name}"
    else:
        # Fallback to standard provider token names
        alt_vars = {
            "github": "GITHUB_TOKEN",
            "discord": "DISCORD_TOKEN",
            "stripe": "STRIPE_API_KEY",
        }
        alt = alt_vars.get(provider.lower())
        if alt and alt in os.environ:
            token_source = f"env:{alt}"

    is_configured = (not is_auth_required) or (token_source is not None)

    if not is_auth_required:
        auth_msg = "Public endpoint • No authentication required"
    elif is_configured:
        auth_msg = f"Configured via {token_source}" + (f" (scheme: {scheme})" if scheme else "")
    else:
        scheme_hint = f" (scheme: '{scheme}')" if scheme else ""
        auth_msg = (
            f"Requires {primary_auth}{scheme_hint}. Set {env_var_name} or pass token=<val>"
        )

    auth_detail = OperationAuthDetail(
        primary_auth=primary_auth,
        auth_types=auth_types,
        scheme=scheme,
        is_required=is_auth_required,
        is_configured=is_configured,
        token_source=token_source,
        env_var_name=env_var_name,
        message=auth_msg,
    )

    can_execute = len(missing_params) == 0 and is_configured

    # Generate diagnostic status summary
    status_parts = []
    if missing_params:
        missing_fmt = [f"{p.name} ({p.in_}: {p.type_str})" for p in missing_params]
        status_parts.append(f"[bold red]Missing argument(s):[/] {', '.join(missing_fmt)}")
    if is_auth_required and not is_configured:
        status_parts.append(f"[bold yellow]Missing Auth:[/] {auth_msg}")

    if can_execute:
        auth_label = token_source or "public"
        status_summary = (
            f"[bold green]✓ Ready to call:[/] {op.method.upper()} {op.path} • Auth: {auth_label}"
        )
    else:
        status_summary = " • ".join(status_parts)

    # Generate example call
    arg_hints = [f"{p.name}=<{p.type_str}>" for p in missing_params]
    example_call = f"/call {' '.join(arg_hints)}" if arg_hints else "/call"

    return OperationRequirementCheck(
        provider=provider,
        api=api,
        source=src,
        operation_id=operation_id,
        method=op.method.upper(),
        path=op.path,
        summary=op.summary or "",
        description=op.description or "",
        parameters=param_details,
        required_parameters=required_params,
        optional_parameters=optional_params,
        missing_parameters=missing_params,
        auth=auth_detail,
        can_execute=can_execute,
        status_summary=status_summary,
        example_call=example_call,
    )


def parse_operation_call_args(
    args_list: list[str],
    params_spec: list[OperationParamDetail] | None = None,
) -> dict[str, Any]:
    """Parse list of 'key=val' or flag strings into typed kwargs."""
    type_map: dict[str, str] = {}
    if params_spec:
        for p in params_spec:
            type_map[p.name] = p.type_str

    kwargs: dict[str, Any] = {}
    for arg in args_list:
        if "=" in arg:
            k, v = arg.split("=", 1)
            k_clean = k.strip()
            expected_type = type_map.get(k_clean)
            kwargs[k_clean] = _parse_typed_value(v.strip(), expected_type=expected_type)
        else:
            kwargs[arg.strip()] = True
    return kwargs


def execute_operation_call(
    client: Any,
    req_check: OperationRequirementCheck,
    kwargs: dict[str, Any],
    dry_run: bool = False,
    emit_curl: bool = False,
) -> MapiResult | RequestConfig:
    """Execute API call with pre-flight authentication setup and validation."""
    clean_kwargs = dict(kwargs)

    # Attach auth if required and not already set
    if req_check.auth.is_required and getattr(client, "_auth", None) is None:
        scheme = req_check.auth.scheme or "Bearer"
        if "token" in clean_kwargs:
            client._auth = BearerAuth(clean_kwargs.pop("token"), scheme=scheme)
        elif "bearer" in clean_kwargs:
            client._auth = BearerAuth(clean_kwargs.pop("bearer"), scheme=scheme)
        elif "api_key" in clean_kwargs:
            client._auth = ApiKeyAuth(key=clean_kwargs.pop("api_key"), name="X-Api-Key")
        elif req_check.auth.token_source and req_check.auth.token_source.startswith("env:"):
            env_var = req_check.auth.token_source.split(":", 1)[1]
            token_val = os.environ.get(env_var)
            if token_val:
                if req_check.auth.primary_auth == "api_key":
                    client._auth = ApiKeyAuth(key=token_val, name="X-Api-Key")
                else:
                    client._auth = BearerAuth(token_val, scheme=scheme)

    if dry_run or emit_curl:
        clean_kwargs["_dry_run"] = True

    res: MapiResult = client.execute(
        req_check.provider,
        req_check.api,
        req_check.source,
        req_check.operation_id,
        **clean_kwargs,
    )

    if (dry_run or emit_curl) and isinstance(res.data, RequestConfig):
        return res.data
    return res
